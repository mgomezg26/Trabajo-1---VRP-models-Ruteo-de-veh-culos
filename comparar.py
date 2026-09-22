"""
Comparaciones de los items 3 y 4 del enunciado.

Punto delicado que resuelve este script: el modelo base se resuelve con
release=off, asi que la "espera" que reporta su corrida esta calculada con
r = 0 y NO es comparable con la del modelo extendido.

Para comparar de verdad hay que tomar las RUTAS del modelo base y evaluarlas
con los tiempos de liberacion reales, fijando la salida de cada ruta en el
mayor r de sus clientes (que es la salida optima para un conjunto de rutas
dado). Eso es exactamente "cuanto se pierde por no modelar las liberaciones".

Lo mismo aplica al modelo de distancia: al minimizar distancia nada empuja las
horas de salida hacia abajo, asi que su espera tambien se recalcula asi.

    python comparar.py
"""

import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import datos as D
import validar as VA

MODELOS = [("espera", "extendido (min espera)"),
           ("distancia", "min distancia"),
           ("makespan_norelease", "base (min makespan)")]


def cargar(n, K, suf):
    p = f"resultados/n{n}_K{K}_{suf}.json"
    if not os.path.exists(p):
        return None
    r = json.load(open(p, encoding="utf-8"))
    return r if r.get("tiene_solucion") else None


def main():
    combos = sorted({(r["n"], r["K"]) for r in
                     [cargar(n, K, "makespan_norelease")
                      for n in D.NS for K in range(1, 6)] if r})
    if not combos:
        print("no hay corridas del modelo base; corre primero:")
        print("  python lote.py --que comparaciones")
        return

    filas = []
    for n, K in combos:
        datos = D.generar(n)
        print("=" * 86)
        print(f"  n = {n},  K = {K}   "
              f"(Tmax={datos['Tmax']}, Q={datos['Q']}, "
              f"max r={max(datos['r'][1:]):.0f})")
        print("=" * 86)

        base_ref = None
        for suf, nombre in MODELOS:
            r = cargar(n, K, suf)
            if r is None:
                print(f"  {nombre:<24} -- sin datos")
                continue

            # TODAS las soluciones se evaluan con la MISMA metrica: tiempos de
            # liberacion reales y salida = max r de cada ruta.
            m = VA.evaluar(datos, r["rutas"], release=True)
            _, fallas = VA.validar(datos, K, r["rutas"], objetivo="espera",
                                   release=True)
            # las del modelo base pueden violar Tmax al medirse como duracion?
            # no: Tmax se evalua sobre la duracion, que no depende de la salida.

            if suf == "espera":
                base_ref = m["espera_total"]

            extra = ""
            if base_ref and suf != "espera":
                extra = (f"  (+{100*(m['espera_total']/base_ref - 1):.1f}% "
                         f"de espera vs el optimo)")

            print(f"  {nombre:<24} espera={m['espera_total']:>9.1f}"
                  f"  dist={m['distancia_total']:>7.1f}"
                  f"  dur.max={m['duracion_maxima']:>7.1f}"
                  f"  rutas={m['num_rutas']}{extra}")
            for d in m["rutas"]:
                rs = [f"{int(datos['r'][i])}" for i in d["clientes"]]
                print(f"      {'-'.join(map(str, d['ruta'])):<24} "
                      f"salida={d['salida']:>6.0f}  carga={d['carga']:>3}"
                      f"  dist={d['distancia']:>7.1f}  r de sus clientes: "
                      f"[{', '.join(rs)}]")
            if fallas:
                print("      !! ", fallas)

            filas.append({
                "n": n, "K": K, "modelo": nombre,
                "espera_total": round(m["espera_total"], 2),
                "distancia_total": round(m["distancia_total"], 2),
                "duracion_maxima": round(m["duracion_maxima"], 2),
                "num_rutas": m["num_rutas"],
                "gap_de_su_corrida": r.get("gap"),
                "sobrecosto_espera_pct": (
                    None if suf == "espera" or not base_ref
                    else round(100 * (m["espera_total"] / base_ref - 1), 2)),
                "rutas": [list(map(int, ru)) for ru in r["rutas"]],
                "salidas": [d["salida"] for d in m["rutas"]],
            })
        print()

    with open("resultados/comparaciones_reevaluadas.json", "w",
              encoding="utf-8") as f:
        json.dump(filas, f, indent=2, ensure_ascii=False)

    # tabla en markdown para pegar en el informe
    L = ["| n | K | modelo | espera total | sobrecosto espera | distancia | "
         "duración máx | rutas |", "|---|---|---|---|---|---|---|---|"]
    for f_ in filas:
        sc = ("—" if f_["sobrecosto_espera_pct"] is None
              else f"+{f_['sobrecosto_espera_pct']:.1f}%")
        L.append(f"| {f_['n']} | {f_['K']} | {f_['modelo']} | "
                 f"{f_['espera_total']:.1f} | {sc} | "
                 f"{f_['distancia_total']:.1f} | "
                 f"{f_['duracion_maxima']:.1f} | {f_['num_rutas']} |")
    md = "\n".join(L)
    with open("resultados/tabla_comparaciones_reevaluadas.md", "w",
              encoding="utf-8") as f:
        f.write(md)
    print("TABLA PARA EL INFORME "
          "(todas las soluciones medidas con la misma métrica)\n")
    print(md)
    print("\nguardado en resultados/tabla_comparaciones_reevaluadas.md")


if __name__ == "__main__":
    main()
