"""
Modelo MILP de ruteo de vehiculos con tiempos de liberacion.

Se escribe UNA sola vez, en PuLP, y se despacha a Gurobi o a HiGHS. Asi no hay
riesgo de que dos implementaciones del mismo modelo se desincronicen.

Correspondencia con el modelo base del Anexo 1 del enunciado:

  base (Anexo 1)                    aqui
  ------------------------------    ------------------------------------------
  t_i  tiempo de llegada            T_i  tiempo de llegada ABSOLUTO
  (no existe)                       u_i  hora de salida del deposito de la
                                         ruta que atiende al cliente i
  (2) visita unica                  R1
  (3) conservacion de flujo         R2
  (4) sin auto-loops                R3
  (5) limite de vehiculos           R4
  (6) continuidad temporal Big-M    R5 (entre clientes) + R6 (desde deposito)
  (7) t_0 = 0                       sustituida por u_i (salida por ruta)
  (8) limite de tiempo por ruta     R9  (ahora es regreso - salida <= Tmax)
  (9) MTZ cota                      R10
  (10) MTZ flujo                    R11
  (11) carga por arco               R12
  (12) conservacion de carga        R13
  (13) definicion del makespan      solo si objetivo='makespan'
  (nuevo)                           R7  u_i >= r_i
  (nuevo)                           R8  u_i = u_j si i y j van en la misma ruta

Con  release=False  y  objetivo='makespan'  el modelo se reduce EXACTAMENTE al
modelo base del profesor (u_i queda fijo en 0, y R5+R6 colapsan en la
restriccion 6 original). Eso se usa como prueba de regresion.
"""

import pulp


# ===========================================================================
# CONSTRUCCION DEL MODELO
# ===========================================================================

def construir(datos, K, objetivo="espera", release=True, big_m="profesor",
              cortes=False):
    """
    objetivo : 'espera'    -> min suma de tiempos de espera   (modelo del trabajo)
               'distancia' -> min distancia total recorrida   (comparacion 1)
               'makespan'  -> min Rmax                        (modelo base)
    release  : True  -> se respetan los tiempos de liberacion r_i
               False -> se ignoran (u_i = 0), para replicar el modelo base
    big_m    : 'profesor' -> M = max(d_ij) * n   (formula original)
               'ajustado' -> M = max_r + Tmax + max_d   (cota valida mas fina)
    """
    n = datos["n"]
    dist = datos["dist"]
    q = datos["q"]
    Q = datos["Q"]
    Tmax = datos["Tmax"]
    r = datos["r"] if release else [0.0] * n

    V = range(n)
    Vp = range(1, n)

    max_d = max(dist[i][j] for i in V for j in V if i != j)
    max_r = max(r) if release else 0.0

    if big_m == "profesor":
        M = datos["M_profesor"]
    elif big_m == "ajustado":
        # Cota superior valida de  T_i + d_ij - T_j :
        #   T_i <= max_r + Tmax   (sale a lo sumo en max_r y la ruta dura <= Tmax)
        #   T_j >= 0
        M = max_r + Tmax + max_d
    else:
        raise ValueError(f"big_m desconocido: {big_m}")

    # Big-M para la consistencia de la hora de salida: u_i vive en [0, max_r]
    Mu = max_r if max_r > 0 else 1.0

    prob = pulp.LpProblem("VRP_release_times", pulp.LpMinimize)

    # ---------------------------------------------------------------- variables
    X = pulp.LpVariable.dicts("X", (V, V), cat=pulp.LpBinary)
    w = pulp.LpVariable.dicts("w", (V, V), lowBound=0)
    L = pulp.LpVariable.dicts("L", (V, V), lowBound=0)

    # T_i: tiempo de llegada absoluto al nodo i
    T = pulp.LpVariable.dicts("T", V, lowBound=0)

    # u_i: hora de salida del deposito de la ruta que atiende al cliente i.
    # Si release=False se fija en 0 y el modelo colapsa al base.
    if release:
        u = {i: pulp.LpVariable(f"u_{i}", lowBound=r[i], upBound=max_r)
             for i in Vp}
    else:
        u = {i: 0.0 for i in Vp}

    prob += T[0] == 0, "T0"

    # -------------------------------------------------------------- R1 visita
    # Cada cliente es visitado exactamente una vez.
    for j in Vp:
        prob += pulp.lpSum(X[i][j] for i in V if i != j) == 1, f"R1_visita_{j}"

    # ------------------------------------------------------- R2 flujo de arcos
    # En cada nodo, los arcos que entran igualan los que salen.
    for j in V:
        prob += pulp.lpSum(X[i][j] - X[j][i] for i in V) == 0, f"R2_flujo_{j}"

    # ------------------------------------------------------------ R3 auto-loops
    prob += pulp.lpSum(X[i][i] for i in V) == 0, "R3_sin_autoloops"

    # ------------------------------------------------------- R4 vehiculos
    # El numero de salidas del deposito no excede K.
    prob += pulp.lpSum(X[0][i] for i in Vp) <= K, "R4_vehiculos"

    # ------------------------------------- R5 continuidad temporal entre clientes
    # Si se recorre (i,j), la llegada a j es al menos la llegada a i mas d_ij.
    for i in Vp:
        for j in Vp:
            if i != j:
                prob += (T[j] >= T[i] + dist[i][j] - M * (1 - X[i][j]),
                         f"R5_tiempo_{i}_{j}")

    # ------------------------------------- R6 continuidad temporal desde deposito
    # La llegada al primer cliente de una ruta cuenta desde la hora de SALIDA.
    for j in Vp:
        prob += (T[j] >= u[j] + dist[0][j] - M * (1 - X[0][j]),
                 f"R6_salida_{j}")

    # ------------------------------------------------- R7 tiempo de liberacion
    # Si un vehiculo visita al cliente j, parte del deposito en t >= r_j.
    #
    # No aparece como fila del modelo porque va impuesta como COTA INFERIOR de
    # la variable: u_j se declara con lowBound=r[j] (ver arriba). Es equivalente
    # y le ahorra n-1 restricciones al modelo. Con release=False no hace falta
    # ninguna, porque entonces u_j es la constante 0 y todos los r_j son 0.

    # --------------------------------- R8 consistencia de la hora de salida
    # Todos los clientes de una misma ruta comparten la hora de salida.
    # Si el arco (i,j) o el (j,i) se recorre, entonces u_i = u_j.
    # Se escribe por pareja NO ordenada, lo que cuesta la mitad de filas.
    if release:
        for i in Vp:
            for j in Vp:
                if i < j:
                    juntos = 1 - X[i][j] - X[j][i]
                    prob += (u[j] - u[i] <= Mu * juntos, f"R8a_{i}_{j}")
                    prob += (u[i] - u[j] <= Mu * juntos, f"R8b_{i}_{j}")

    # ------------------------------------------------ R9 duracion de la ruta
    # regreso al deposito menos hora de salida <= Tmax
    for j in Vp:
        prob += (T[j] + dist[j][0] - u[j] <= Tmax, f"R9_Tmax_{j}")

    # ------------------------------------------- C1 desigualdades validas
    # La relajacion lineal produce cotas NEGATIVAS para la espera total, que
    # por definicion es >= 0. El motivo: con X fraccionario los Big-M de R5 y
    # R6 quedan desactivados y nada impide que T_j caiga por debajo de r_j.
    #
    # Desigualdad valida: el vehiculo que atiende a j parte en u_j >= r_j y
    # recorre del deposito hasta j una distancia de al menos d_0j (desigualdad
    # triangular, que la metrica euclidea cumple). Por lo tanto
    #
    #       T_j  >=  u_j + d_0j  >=  r_j + d_0j
    #
    # es decir  espera_j = T_j - r_j >= d_0j, y la espera total es al menos
    # sum_j d_0j. No corta ninguna solucion entera factible: solo le informa
    # al solver algo que ya es cierto.
    if cortes:
        for j in Vp:
            prob += T[j] >= r[j] + dist[0][j], f"C1_llegada_minima_{j}"

    # ----------------------------------------------------------- R10/R11 MTZ
    for i in V:
        for j in V:
            prob += w[i][j] <= n * X[i][j], f"R10_mtz_cota_{i}_{j}"
    for j in Vp:
        prob += pulp.lpSum(w[i][j] - w[j][i] for i in V) == 1, f"R11_mtz_flujo_{j}"

    # ---------------------------------------------------------- R12/R13 carga
    for i in V:
        for j in V:
            prob += L[i][j] <= Q * X[i][j], f"R12_carga_cota_{i}_{j}"
    for j in Vp:
        prob += (pulp.lpSum(L[i][j] - L[j][i] for i in V) == q[j],
                 f"R13_carga_flujo_{j}")

    # ------------------------------------------------------- funcion objetivo
    Rmax = None
    if objetivo == "espera":
        # min  suma de (llegada - liberacion)
        #
        # CUIDADO: escribir  lpSum(T[j] - r[j])  deja una CONSTANTE (-sum r)
        # en el objetivo, y PuLP no se la pasa al solver. Eso tiene dos
        # consecuencias, las dos malas:
        #   1. el ObjVal reportado queda inflado en sum(r);
        #   2. peor, el gap relativo se calcula sobre sum(T) en vez de sobre
        #      sum(T - r). Como sum(r) > 0, el gap reportado SUBESTIMA el
        #      gap verdadero del objetivo que pide el enunciado.
        # Solucion: cargar la constante en una variable fija en 1, para que
        # el solver la vea como un termino lineal mas. Asi ObjVal y MIPGap
        # quedan referidos al objetivo correcto.
        suma_r = sum(r[j] for j in Vp)
        if suma_r > 0:
            cte = pulp.LpVariable("cte_uno", lowBound=1, upBound=1)
            prob += pulp.lpSum(T[j] for j in Vp) - suma_r * cte
        else:
            prob += pulp.lpSum(T[j] for j in Vp)
    elif objetivo == "distancia":
        prob += pulp.lpSum(dist[i][j] * X[i][j] for i in V for j in V)
    elif objetivo == "makespan":
        Rmax = pulp.LpVariable("Rmax", lowBound=0)
        for j in Vp:
            prob += Rmax >= T[j] + dist[j][0], f"R14_makespan_{j}"
        prob += Rmax
    else:
        raise ValueError(f"objetivo desconocido: {objetivo}")

    meta = {"M": M, "Mu": Mu, "max_d": max_d, "max_r": max_r,
            "objetivo": objetivo, "release": release, "big_m": big_m,
            "cortes": cortes,
            "cota_trivial_espera": sum(dist[0][j] for j in Vp)}
    return prob, {"X": X, "T": T, "u": u, "w": w, "L": L, "Rmax": Rmax}, meta


# ===========================================================================
# EXTRACCION DE LA SOLUCION
# ===========================================================================

def extraer_rutas(n, Xval):
    """Reconstruye las rutas caminando desde el deposito."""
    suc = {}
    for i in range(n):
        for j in range(n):
            if i != j and Xval[i][j] > 0.5:
                suc.setdefault(i, []).append(j)

    rutas = []
    for primero in suc.get(0, []):
        ruta = [0, primero]
        actual = primero
        for _ in range(n + 2):          # tope de seguridad
            if actual == 0:
                break
            siguientes = suc.get(actual, [])
            if not siguientes:
                break
            actual = siguientes[0]
            ruta.append(actual)
        rutas.append(ruta)
    return rutas
