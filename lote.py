"""
Corre varias instancias en paralelo, una por proceso.

    python lote.py --que principal          # las 15 instancias del enunciado
    python lote.py --que comparaciones      # distancia y modelo base
    python lote.py --que bigm               # experimento de Big-M ajustado
    python lote.py --que principal --procesos 3 --tiempo 3600

Con --procesos 3 y --hilos 2 se usan los 6 nucleos fisicos de la maquina.
Como hay paralelismo, los tiempos medidos NO son de una corrida aislada; eso
debe quedar dicho en la seccion de configuracion experimental del informe.
"""

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import datos as D

# Instancias elegidas para las comparaciones de los items 3 y 4 del enunciado.
# El enunciado pide "al menos dos instancias con gap igual a cero".
#
# Resultado de la corrida principal: las UNICAS que alcanzaron gap = 0 son las
# tres de n = 10. En n = 15 los gaps quedaron entre 36% y 70% tras 300 s, asi
# que no califican. Se usan las tres de n = 10:
#   (10,2) y (10,3) tienen 2 y 3 rutas -> sirven para comparar estructura
#                                         entre vehiculos;
#   (10,1) tiene una sola ruta -> se incluye como contraste (ahi el problema
#                                 degenera en un TSP con liberaciones).
COMPARAR = [(10, 1), (10, 2), (10, 3)]


def tareas(que, tiempo, hilos):
    t = []
    if que == "principal":
        for n, K in D.instancias():
            t.append(["--n", str(n), "--K", str(K), "--objetivo", "espera"])
    elif que == "comparaciones":
        for n, K in COMPARAR:
            t.append(["--n", str(n), "--K", str(K), "--objetivo", "distancia"])
            t.append(["--n", str(n), "--K", str(K), "--objetivo", "makespan",
                      "--release", "off"])
    elif que == "cortes":
        # Las 15 con las desigualdades validas T_j >= r_j + d_0j, para medir
        # cuanto mejora la cota respecto de la formulacion tal cual.
        for n, K in D.instancias():
            t.append(["--n", str(n), "--K", str(K), "--objetivo", "espera",
                      "--cortes", "on"])
    elif que == "bigm":
        for n, K in [(15, 2), (20, 2), (20, 3)]:
            t.append(["--n", str(n), "--K", str(K), "--objetivo", "espera",
                      "--bigm", "ajustado"])
    else:
        raise ValueError(que)
    return [x + ["--tiempo", str(tiempo), "--hilos", str(hilos)] for x in t]


def ordenar(t):
    """Primero las chicas, para tener retroalimentacion rapida."""
    return sorted(t, key=lambda a: int(a[a.index("--n") + 1]))


def correr_una(argv):
    etiqueta = f"n{argv[argv.index('--n')+1]}_K{argv[argv.index('--K')+1]}"
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, "correr.py"] + argv,
                       capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return {"argv": argv, "etiqueta": etiqueta, "rc": p.returncode,
            "segundos": dt, "stdout": p.stdout, "stderr": p.stderr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--que", default="principal",
                    choices=["principal", "comparaciones", "cortes", "bigm"])
    ap.add_argument("--procesos", type=int, default=3)
    ap.add_argument("--tiempo", type=float, default=3600.0)
    ap.add_argument("--hilos", type=int, default=2)
    args = ap.parse_args()

    t = ordenar(tareas(args.que, args.tiempo, args.hilos))
    print(f"{len(t)} instancias, {args.procesos} procesos en paralelo, "
          f"{args.hilos} hilos cada uno, limite {args.tiempo:.0f}s")
    print(f"peor caso: {len(t)/args.procesos*args.tiempo/3600:.1f} horas\n")

    t0 = time.perf_counter()
    hechas = 0
    with cf.ThreadPoolExecutor(max_workers=args.procesos) as ex:
        futuros = {ex.submit(correr_una, a): a for a in t}
        for f in cf.as_completed(futuros):
            rr = f.result()
            hechas += 1
            estado = "ok" if rr["rc"] == 0 else f"FALLO(rc={rr['rc']})"
            print(f"[{hechas}/{len(t)}] {rr['etiqueta']:>12} "
                  f"{estado:>12} {rr['segundos']:>8.1f}s", flush=True)
            if rr["rc"] != 0:
                print("   stderr:", (rr["stderr"] or "")[-600:], flush=True)

    print(f"\ntotal: {(time.perf_counter()-t0)/60:.1f} minutos")


if __name__ == "__main__":
    main()
