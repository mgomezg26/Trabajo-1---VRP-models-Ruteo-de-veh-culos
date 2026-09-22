"""
Generacion de datos de las instancias.

IMPORTANTE: las lineas marcadas con  # [PROFESOR] son copia textual de
VRP_MILP_Trabajo_1.py. No se modifican las semillas ni la generacion de datos,
tal como exige el enunciado.

La unica diferencia estructural es que aqui se calculan los datos de UN solo n
(en lugar de recorrer los cinco). Esto es equivalente porque el script del
profesor reinicia las semillas al comienzo de cada iteracion de n:

    for n in [10,15,20,25,30]:
        random.seed(1234567)
        np.random.seed(1234567)

por lo que los datos de un n dado no dependen de los n anteriores.
"""

import math
import random

import numpy as np

ARCHIVO_COORD = "ch150.tsp"
NS = [10, 15, 20, 25, 30]


def generar(n, archivo=ARCHIVO_COORD):
    """Devuelve el diccionario de datos de la instancia de tamano n."""

    coord = np.loadtxt(archivo)                                  # [PROFESOR]

    random.seed(1234567)                                         # [PROFESOR]
    np.random.seed(1234567)                                      # [PROFESOR]

    # --- matriz de distancias y distancia promedio -----------------------
    dist = []                                                    # [PROFESOR]
    avgdist = 0                                                  # [PROFESOR]
    x = []                                                       # [PROFESOR]
    y = []                                                       # [PROFESOR]
    for i in range(n):                                           # [PROFESOR]
        dist.append([])                                          # [PROFESOR]
        x.append(coord[i][0])                                    # [PROFESOR]
        y.append(coord[i][1])                                    # [PROFESOR]
        for j in range(n):                                       # [PROFESOR]
            dist[i].append(math.sqrt((coord[i][0] - coord[j][0]) ** 2
                                     + (coord[i][1] - coord[j][1]) ** 2))
            avgdist += dist[i][j]                                # [PROFESOR]
    avgdist = math.ceil(avgdist / (n * n))                       # [PROFESOR]

    # --- tiempos de liberacion -------------------------------------------
    # 50% en cero, 50% entero aleatorio entre 5 y 2*avgdist
    r = np.zeros(n)                                              # [PROFESOR]
    for i in range(n):                                           # [PROFESOR]
        if random.random() < 0.5:                                # [PROFESOR]
            r[i] = random.randint(5, 2 * avgdist)                # [PROFESOR]

    # --- demandas ---------------------------------------------------------
    q = [random.randint(1, 10) for _ in range(n)]                # [PROFESOR]
    q[0] = 0                                                     # [PROFESOR]

    # --- capacidad y numero minimo de vehiculos --------------------------
    Q = math.ceil(sum(q) / n * 15)                               # [PROFESOR]
    K0 = math.ceil(sum(q) / Q)                                   # [PROFESOR]

    # Tmax solo depende de K0, por lo que es el mismo para los tres K
    Tmax = math.ceil(avgdist * n / K0 * 0.7)                     # [PROFESOR]

    # ---------------------------------------------------------------------
    # El bucle del profesor genera tambien r[0] (deposito). El deposito no es
    # cliente y no tiene tiempo de liberacion, asi que el modelo lo ignora.
    # Se guarda el valor original para poder reportarlo en el informe.
    # ---------------------------------------------------------------------
    r_deposito_generado = float(r[0])
    r = [0.0] + [float(v) for v in r[1:]]

    return {
        "n": n,
        "dist": dist,
        "x": x,
        "y": y,
        "avgdist": avgdist,
        "r": r,
        "r_deposito_generado": r_deposito_generado,
        "q": q,
        "Q": Q,
        "K0": K0,
        "Tmax": Tmax,
        "M_profesor": max(dist[i][j] for i in range(n)
                          for j in range(n) if i != j) * n,      # [PROFESOR]
    }


def instancias():
    """Las 15 combinaciones (n, K) que pide el enunciado."""
    for n in NS:
        K0 = generar(n)["K0"]
        for K in range(K0, K0 + 3):                              # [PROFESOR]
            yield n, K


if __name__ == "__main__":
    print(f"{'n':>3} {'clientes':>8} {'avgdist':>7} {'sum q':>6} {'Q':>4} "
          f"{'K0':>3} {'Tmax':>6} {'M':>8} {'r>0':>4} {'max r':>6}")
    print("-" * 66)
    for n in NS:
        d = generar(n)
        nr = sum(1 for v in d["r"][1:] if v > 0)
        print(f"{n:>3} {n-1:>8} {d['avgdist']:>7} {sum(d['q']):>6} {d['Q']:>4} "
              f"{d['K0']:>3} {d['Tmax']:>6} {d['M_profesor']:>8.0f} "
              f"{nr:>4} {max(d['r'][1:]):>6.0f}")
    print()
    print("Instancias a resolver:", list(instancias()))
