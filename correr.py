"""
Resuelve UNA instancia y guarda el resultado en JSON.

Un proceso por instancia: si una se cae o se queda sin licencia, las demas no
se ven afectadas (el script del profesor corre las 15 en un solo proceso y
ademas lee md.ObjVal sin revisar el estado, por lo que aborta en la primera
instancia infactible).

Uso:
    python correr.py --n 10 --K 1
    python correr.py --n 10 --K 1 --objetivo distancia
    python correr.py --n 10 --K 1 --objetivo makespan --release off   # base
"""

import argparse
import json
import os
import platform
import sys
import time

# Ejecutar siempre desde la carpeta del script, para que ch150.tsp resuelva
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pulp

import datos as D
import modelo as MO
import validar as VA

LIMITE_LICENCIA_GUROBI = 20   # medido empiricamente: n<=20 cabe, n>=25 no


def elegir_solver(n, forzado=None):
    if forzado:
        return forzado
    return "gurobi" if n <= LIMITE_LICENCIA_GUROBI else "highs"


def stats_gurobi(prob):
    g = prob.solverModel
    out = {}
    for attr, clave in [("Status", "status_solver"), ("MIPGap", "gap"),
                        ("ObjBound", "cota"), ("ObjVal", "objetivo"),
                        ("Runtime", "tiempo_solver"), ("NodeCount", "nodos"),
                        ("SolCount", "num_soluciones"),
                        ("NumVars", "num_vars"), ("NumConstrs", "num_restr"),
                        ("IterCount", "iteraciones")]:
        try:
            out[clave] = getattr(g, attr)
        except Exception:
            out[clave] = None
    # 2=OPTIMAL 3=INFEASIBLE 9=TIME_LIMIT
    out["optimo"] = out["status_solver"] == 2
    out["infactible"] = out["status_solver"] == 3
    out["limite_tiempo"] = out["status_solver"] == 9
    out["tiene_solucion"] = bool(out["num_soluciones"])
    return out


def stats_highs(prob):
    """
    CUIDADO: no se puede usar  pulp.value(prob.objective)  para saber si hay
    solucion. Si HiGHS agota el tiempo SIN encontrar ninguna factible, las
    variables quedan en 0 y ese valor devuelve 0.0, no None, lo que haria
    pasar por "solucion de espera 0" algo que en realidad no es una solucion.
    La fuente confiable es  info.primal_solution_status.
    """
    import highspy

    h = prob.solverModel
    out = {"num_vars": len(prob.variables()),
           "num_restr": len(prob.constraints)}

    factible = False
    obj = None
    try:
        info = h.getInfo()
        factible = (info.primal_solution_status
                    == highspy.SolutionStatus.kSolutionStatusFeasible)
        gap = getattr(info, "mip_gap", None)
        # sin solucion el gap viene en infinito; eso no es un numero reportable
        out["gap"] = None if (gap is None or gap != gap or gap == float("inf")) else gap
        cota = getattr(info, "mip_dual_bound", None)
        out["cota"] = None if cota == float("-inf") else cota
        out["nodos"] = getattr(info, "mip_node_count", None)
        if factible:
            obj = info.objective_function_value
    except Exception:
        out.update(gap=None, cota=None, nodos=None)

    try:
        out["tiempo_solver"] = h.getRunTime()
    except Exception:
        out["tiempo_solver"] = None

    try:
        est = str(h.getModelStatus())
        out["status_solver"] = est
        out["optimo"] = "kOptimal" in est
        out["infactible"] = "kInfeasible" in est
        out["limite_tiempo"] = "kTimeLimit" in est
    except Exception:
        out.update(status_solver=None, optimo=False,
                   infactible=False, limite_tiempo=False)

    out["objetivo"] = obj
    out["tiene_solucion"] = factible
    out["num_soluciones"] = 1 if factible else 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--K", type=int, required=True)
    ap.add_argument("--objetivo", default="espera",
                    choices=["espera", "distancia", "makespan"])
    ap.add_argument("--release", default="on", choices=["on", "off"])
    ap.add_argument("--bigm", default="profesor",
                    choices=["profesor", "ajustado"])
    ap.add_argument("--cortes", default="off", choices=["on", "off"],
                    help="agrega las desigualdades validas T_j >= r_j + d_0j")
    ap.add_argument("--solver", default=None, choices=["gurobi", "highs"])
    ap.add_argument("--tiempo", type=float, default=3600.0)
    ap.add_argument("--hilos", type=int, default=2)
    ap.add_argument("--etiqueta", default=None)
    args = ap.parse_args()

    release = args.release == "on"
    cortes = args.cortes == "on"
    etiqueta = args.etiqueta or (
        f"n{args.n}_K{args.K}_{args.objetivo}"
        f"{'' if release else '_norelease'}"
        f"{'' if args.bigm == 'profesor' else '_bigm-ajustado'}"
        f"{'_cortes' if cortes else ''}")

    datos = D.generar(args.n)
    solver_nombre = elegir_solver(args.n, args.solver)

    print(f"[{etiqueta}] construyendo modelo...", flush=True)
    t0 = time.perf_counter()
    prob, var, meta = MO.construir(datos, args.K, objetivo=args.objetivo,
                                   release=release, big_m=args.bigm,
                                   cortes=cortes)
    t_build = time.perf_counter() - t0
    print(f"[{etiqueta}] modelo: {len(prob.variables())} vars, "
          f"{len(prob.constraints)} restricciones "
          f"(construido en {t_build:.1f}s)", flush=True)

    # El objetivo NO puede tener termino constante: PuLP no lo transmite al
    # solver, lo que falsearia el ObjVal y, sobre todo, el gap relativo.
    cte_obj = prob.objective.constant
    if abs(cte_obj) > 1e-9:
        print(f"[{etiqueta}] ABORTA: el objetivo tiene constante {cte_obj}, "
              f"que el solver no veria (gap y ObjVal quedarian mal)",
              file=sys.stderr)
        return 1

    log = os.path.join("logs", f"{etiqueta}_{solver_nombre}.log")
    if solver_nombre == "gurobi":
        solver = pulp.GUROBI(msg=1, timeLimit=args.tiempo, gapRel=0.0,
                             logPath=log, Threads=args.hilos, Seed=0)
    else:
        solver = pulp.HiGHS(msg=1, timeLimit=args.tiempo, gapRel=0.0,
                            logFile=log, threads=args.hilos)

    print(f"[{etiqueta}] resolviendo con {solver_nombre} "
          f"(limite {args.tiempo:.0f}s, {args.hilos} hilos)...", flush=True)
    t0 = time.perf_counter()
    try:
        prob.solve(solver)
        error = None
    except Exception as e:                         # licencia, memoria, etc.
        error = f"{type(e).__name__}: {e}"
        print(f"[{etiqueta}] ERROR: {error}", flush=True)
    t_wall = time.perf_counter() - t0

    res = {
        "etiqueta": etiqueta, "n": args.n, "K": args.K,
        "objetivo_tipo": args.objetivo, "release": release,
        "big_m": args.bigm, "cortes": cortes, "solver": solver_nombre,
        "limite_tiempo_s": args.tiempo, "hilos": args.hilos,
        "tiempo_construccion_s": t_build, "tiempo_pared_s": t_wall,
        "error": error,
        "parametros": {k: datos[k] for k in
                       ("n", "avgdist", "Q", "K0", "Tmax", "M_profesor",
                        "r_deposito_generado")},
        "sum_q": sum(datos["q"]), "q": datos["q"], "r": datos["r"],
        "meta_modelo": meta,
        "estado_pulp": pulp.LpStatus[prob.status] if error is None else None,
        "maquina": {"plataforma": platform.platform(),
                    "procesador": platform.processor()},
    }

    if error is None:
        res.update(stats_gurobi(prob) if solver_nombre == "gurobi"
                   else stats_highs(prob))

        if res.get("tiene_solucion"):
            n = args.n
            Xv = [[(var["X"][i][j].value() or 0.0) for j in range(n)]
                  for i in range(n)]
            rutas = MO.extraer_rutas(n, Xv)
            uv = ({i: (var["u"][i].value() or 0.0) for i in range(1, n)}
                  if release else None)

            m, fallas = VA.validar(datos, args.K, rutas,
                                   objetivo=args.objetivo, release=release,
                                   obj_reportado=res.get("objetivo"),
                                   u_solver=uv)
            res["rutas"] = [d["ruta"] for d in m["rutas"]]
            res["detalle_rutas"] = [
                {k: v for k, v in d.items() if k != "llegadas"} |
                {"llegadas": {str(a): b for a, b in d["llegadas"].items()}}
                for d in m["rutas"]]
            res["metricas"] = {k: v for k, v in m.items() if k != "rutas"}
            res["violaciones"] = fallas
            res["u_solver"] = uv
            VA.imprimir(datos, args.K, m, fallas, titulo=f"[{etiqueta}]")
        else:
            res["rutas"] = None
            print(f"[{etiqueta}] sin solucion factible "
                  f"(estado {res.get('status_solver')})", flush=True)

    destino = os.path.join("resultados", f"{etiqueta}.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False, default=str)
    print(f"[{etiqueta}] guardado en {destino}", flush=True)

    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
