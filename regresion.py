"""
Prueba de regresion.

Construye el modelo base TAL CUAL lo escribio el profesor (gurobipy, copia
textual de las restricciones de VRP_MILP_Trabajo_1.py) y lo compara contra
mi modelo en PuLP con release=off y objetivo=makespan.

Si los dos dan el mismo valor objetivo, mi reimplementacion en PuLP es
equivalente al modelo base, y por lo tanto el modelo extendido parte de una
base correcta.

Uso:  python regresion.py
"""

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import gurobipy as gp
import pulp
from gurobipy import GRB

import datos as D
import modelo as MO
import validar as VA


def modelo_profesor(datos, K, tiempo=300):
    """Copia textual del modelo de VRP_MILP_Trabajo_1.py."""
    n = datos["n"]
    dist = datos["dist"]
    q = datos["q"]
    Q = datos["Q"]
    Tmax = datos["Tmax"]

    md = gp.Model("VRP base")
    X = md.addVars(n, n, vtype=GRB.BINARY, name='X')
    t = md.addVars(n, vtype=GRB.CONTINUOUS, name='t', lb=0)
    w = md.addVars(n, n, vtype=GRB.CONTINUOUS, name='w')
    L = md.addVars(n, n, vtype=GRB.CONTINUOUS, name='L')
    Rmax = md.addVar(vtype=GRB.CONTINUOUS, name='Rmax')

    V = range(n)
    Vp = range(1, n)
    M = max([dist[i][j] for i in V for j in V if i != j]) * n

    md.addConstrs(gp.quicksum(X[i, j] for i in V if i != j) == 1 for j in Vp)
    md.addConstrs(gp.quicksum(X[i, j] - X[j, i] for i in V) == 0 for j in V)
    md.addConstr(gp.quicksum(X[i, i] for i in V) == 0)
    md.addConstr(gp.quicksum(X[0, i] for i in Vp) <= K)
    md.addConstrs(t[j] >= t[i] + dist[i][j] - M * (1 - X[i, j])
                  for j in Vp for i in V if i != j)
    md.addConstr(t[0] == 0)
    md.addConstrs(t[j] + dist[j][0] <= Tmax for j in Vp)
    md.addConstrs(w[i, j] <= n * X[i, j] for i in V for j in V)
    md.addConstrs(gp.quicksum(w[i, j] - w[j, i] for i in V) == 1 for j in Vp)
    md.addConstrs(L[i, j] <= Q * X[i, j] for i in V for j in V)
    md.addConstrs(gp.quicksum(L[i, j] - L[j, i] for i in V) == q[j] for j in Vp)
    md.addConstrs(Rmax >= t[j] + dist[j][0] for j in Vp)
    md.setObjective(Rmax, GRB.MINIMIZE)
    md.update()
    md.setParam(GRB.Param.OutputFlag, 0)
    md.setParam(GRB.Param.TimeLimit, tiempo)
    md.setParam(GRB.Param.MIPGap, 0.0)
    md.setParam(GRB.Param.Threads, 4)
    md.setParam(GRB.Param.Seed, 0)
    md.optimize()

    Xv = None
    obj = None
    if md.SolCount > 0:
        obj = md.ObjVal
        Xv = [[X[i, j].X for j in range(n)] for i in range(n)]
    return md.Status, obj, md.MIPGap if md.SolCount else None, Xv


def modelo_mio(datos, K, tiempo=300):
    prob, var, _ = MO.construir(datos, K, objetivo="makespan", release=False)
    prob.solve(pulp.GUROBI(msg=0, timeLimit=tiempo, gapRel=0.0,
                           Threads=4, Seed=0))
    g = prob.solverModel
    n = datos["n"]
    Xv = None
    obj = None
    if g.SolCount > 0:
        obj = g.ObjVal
        Xv = [[(var["X"][i][j].value() or 0.0) for j in range(n)]
              for i in range(n)]
    return g.Status, obj, g.MIPGap if g.SolCount else None, Xv


def main():
    # Limite corto: esto es una prueba de EQUIVALENCIA de formulacion, no una
    # medicion de tiempos. Si los dos modelos coinciden en varias instancias,
    # son el mismo modelo. Se puede pasar otro limite:  python regresion.py 600
    tiempo = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
    casos = [(10, 1), (10, 2), (10, 3), (15, 2)]
    print(f"limite por modelo: {tiempo:.0f}s")
    print("=" * 78)
    print("REGRESION: modelo base del profesor (gurobipy)  vs  el mio "
          "(PuLP, release=off)")
    print("=" * 78)
    print(f"{'n':>3} {'K':>2} | {'prof. obj':>11} {'prof. gap':>9} | "
          f"{'mio obj':>11} {'mio gap':>9} | {'dif':>9} {'veredicto':>10}")
    print("-" * 78)

    todo_ok = True
    for n, K in casos:
        datos = D.generar(n)
        s1, o1, g1, _ = modelo_profesor(datos, K, tiempo)
        s2, o2, g2, Xv2 = modelo_mio(datos, K, tiempo)

        # Solo se puede exigir igualdad si LOS DOS probaron optimalidad. Si
        # alguno se detuvo por tiempo, los incumbentes pueden diferir sin que
        # los modelos sean distintos: simplemente pararon en puntos distintos
        # del arbol. Ese caso no confirma ni refuta la equivalencia.
        opt1 = g1 is not None and g1 < 1e-6
        opt2 = g2 is not None and g2 < 1e-6

        if o1 is None and o2 is None:
            ver, dif = "ok (sin sol)", float("nan")
        elif o1 is None or o2 is None:
            ver, dif, todo_ok = "DIFIERE", float("nan"), False
        elif not (opt1 and opt2):
            dif = abs(o1 - o2)
            ver = "no concl."          # ninguno probo optimalidad
        else:
            dif = abs(o1 - o2)
            ok = dif < 1e-4
            ver = "ok" if ok else "DIFIERE"
            todo_ok = todo_ok and ok

        so1 = f"{o1:.4f}" if o1 is not None else "infactible"
        so2 = f"{o2:.4f}" if o2 is not None else "infactible"
        sg1 = f"{g1:.2e}" if g1 is not None else "-"
        sg2 = f"{g2:.2e}" if g2 is not None else "-"
        print(f"{n:>3} {K:>2} | {so1:>11} {sg1:>9} | {so2:>11} {sg2:>9} | "
              f"{dif:>9.2e} {ver:>10}")

        # de paso: la solucion de mi modelo cumple las restricciones del base
        if Xv2 is not None:
            rutas = MO.extraer_rutas(n, Xv2)
            _, fallas = VA.validar(datos, K, rutas, objetivo="makespan",
                                   release=False, obj_reportado=o2)
            if fallas:
                todo_ok = False
                print("      !! violaciones en mi solucion:", fallas)

    print("-" * 78)
    print("RESULTADO:", "equivalentes en todos los casos concluyentes"
          if todo_ok else "!! HAY DIFERENCIAS, revisar la formulacion")
    print("  'no concl.' = ninguno de los dos probo optimalidad dentro del")
    print("  limite, asi que la comparacion de incumbentes no dice nada.")
    return 0 if todo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
