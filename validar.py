"""
Verificacion independiente de una solucion.

Recalcula TODO a partir de la lista de rutas, sin usar el solver, y compara
contra el valor objetivo reportado. Si el modelo tiene un error de formulacion
(un Big-M mal puesto, una restriccion que no ataja lo que se cree), aqui se ve.
"""

TOL = 1e-4


def evaluar(datos, rutas, release=True):
    """Metricas de una solucion, calculadas desde cero."""
    n = datos["n"]
    dist = datos["dist"]
    q = datos["q"]
    r = datos["r"] if release else [0.0] * n

    detalle = []
    for ruta in rutas:
        clientes = [i for i in ruta if i != 0]

        # La ruta no puede partir antes del mayor tiempo de liberacion de los
        # clientes que atiende. Como el objetivo minimiza espera, la salida
        # optima es exactamente ese maximo.
        salida = max([r[i] for i in clientes], default=0.0)

        carga = sum(q[i] for i in clientes)
        acumulado = 0.0
        llegadas = {}
        for a, b in zip(ruta, ruta[1:]):
            acumulado += dist[a][b]
            if b != 0:
                llegadas[b] = salida + acumulado

        distancia = acumulado
        espera = sum(llegadas[i] - r[i] for i in clientes)

        # Restriccion R9, evaluada cliente por cliente (no solo en el ultimo):
        #   llegada_j + d_j0 - salida <= Tmax
        holgura = min(
            [datos["Tmax"] - ((llegadas[i] - salida) + dist[i][0]) for i in clientes],
            default=float("inf"))

        detalle.append({
            "ruta": ruta,
            "clientes": clientes,
            "carga": carga,
            "distancia": distancia,
            "salida": salida,
            "regreso": salida + distancia,
            "duracion": distancia,
            "llegadas": llegadas,
            "espera": espera,
            "holgura_Tmax": holgura,
        })

    return {
        "rutas": detalle,
        "num_rutas": len(detalle),
        "espera_total": sum(d["espera"] for d in detalle),
        "distancia_total": sum(d["distancia"] for d in detalle),
        "makespan_absoluto": max([d["regreso"] for d in detalle], default=0.0),
        "duracion_maxima": max([d["duracion"] for d in detalle], default=0.0),
    }


def validar(datos, K, rutas, objetivo="espera", release=True,
            obj_reportado=None, u_solver=None):
    """Devuelve (metricas, lista_de_violaciones)."""
    n = datos["n"]
    q = datos["q"]
    Q = datos["Q"]
    Tmax = datos["Tmax"]
    r = datos["r"] if release else [0.0] * n

    m = evaluar(datos, rutas, release=release)
    fallas = []

    # --- 1. cada cliente exactamente una vez -----------------------------
    visitas = {}
    for d in m["rutas"]:
        for i in d["clientes"]:
            visitas[i] = visitas.get(i, 0) + 1
    for i in range(1, n):
        c = visitas.get(i, 0)
        if c != 1:
            fallas.append(f"cliente {i} visitado {c} veces (debe ser 1)")

    # --- 2. rutas cerradas en el deposito --------------------------------
    for d in m["rutas"]:
        if d["ruta"][0] != 0 or d["ruta"][-1] != 0:
            fallas.append(f"ruta no cerrada en el deposito: {d['ruta']}")
        if len(d["ruta"]) < 3:
            fallas.append(f"ruta vacia o degenerada: {d['ruta']}")

    # --- 3. numero de vehiculos ------------------------------------------
    if m["num_rutas"] > K:
        fallas.append(f"usa {m['num_rutas']} rutas y el limite es K={K}")

    # --- 4. capacidad -----------------------------------------------------
    for d in m["rutas"]:
        if d["carga"] > Q + TOL:
            fallas.append(f"ruta {d['ruta']} lleva {d['carga']} > Q={Q}")

    # --- 5. duracion / Tmax ----------------------------------------------
    for d in m["rutas"]:
        if d["holgura_Tmax"] < -TOL:
            fallas.append(
                f"ruta {d['ruta']} viola Tmax={Tmax} "
                f"(holgura {d['holgura_Tmax']:.3f})")

    # --- 6. tiempos de liberacion ----------------------------------------
    if release:
        for d in m["rutas"]:
            for i in d["clientes"]:
                if d["salida"] < r[i] - TOL:
                    fallas.append(
                        f"ruta {d['ruta']} sale en {d['salida']:.2f} "
                        f"pero el cliente {i} libera en {r[i]:.2f}")

    # --- 7. demanda total atendida ---------------------------------------
    atendida = sum(d["carga"] for d in m["rutas"])
    if abs(atendida - sum(q)) > TOL:
        fallas.append(f"demanda atendida {atendida} != demanda total {sum(q)}")

    # --- 8. el objetivo reportado coincide con el recalculado -------------
    if obj_reportado is not None:
        esperado = {"espera": m["espera_total"],
                    "distancia": m["distancia_total"],
                    "makespan": m["makespan_absoluto"]}[objetivo]
        if abs(esperado - obj_reportado) > 1e-2:
            fallas.append(
                f"objetivo del solver {obj_reportado:.4f} != recalculado "
                f"{esperado:.4f} (objetivo='{objetivo}')")

    # --- 9. la hora de salida del solver es la optima ---------------------
    if u_solver is not None and release:
        for d in m["rutas"]:
            for i in d["clientes"]:
                if abs(u_solver.get(i, 0.0) - d["salida"]) > 1e-2:
                    fallas.append(
                        f"u[{i}]={u_solver.get(i):.2f} del solver != "
                        f"salida optima {d['salida']:.2f} de su ruta")
                    break

    return m, fallas


def imprimir(datos, K, m, fallas, titulo=""):
    print("=" * 74)
    if titulo:
        print(titulo)
    print(f"n={datos['n']}  K={K}  Q={datos['Q']}  Tmax={datos['Tmax']}")
    print("=" * 74)
    for d in m["rutas"]:
        print(f"  ruta {'-'.join(str(i) for i in d['ruta'])}")
        print(f"       carga={d['carga']:>3}/{datos['Q']}  "
              f"dist={d['distancia']:>8.2f}  salida={d['salida']:>7.2f}  "
              f"regreso={d['regreso']:>8.2f}  espera={d['espera']:>9.2f}  "
              f"holgura Tmax={d['holgura_Tmax']:>8.2f}")
    print(f"  rutas={m['num_rutas']}  espera total={m['espera_total']:.2f}  "
          f"distancia total={m['distancia_total']:.2f}  "
          f"duracion max={m['duracion_maxima']:.2f}")
    if fallas:
        print("  !! VIOLACIONES:")
        for f in fallas:
            print("     -", f)
    else:
        print("  OK: la solucion cumple todas las restricciones")
    print()
