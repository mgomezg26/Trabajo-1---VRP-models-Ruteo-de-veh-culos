"""
Lee los JSON de resultados/ y produce las tablas y figuras del informe.

    python analizar.py

Genera:
    resultados/tabla_principal.csv   .md    -> item 1 del enunciado
    resultados/tabla_tiempos.csv     .md    -> item 2
    resultados/tabla_comparaciones.csv .md  -> items 3 y 4
    figuras/tiempos.png, figuras/gap.png
    figuras/rutas_n<..>_K<..>.png           -> comparacion visual de rutas
"""

import glob
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import datos as D
import validar as VA


def cargar():
    """Carga solo los JSON de corridas. En resultados/ tambien hay archivos
    generados (por ejemplo comparaciones_reevaluadas.json, que es una lista),
    asi que hay que filtrar en vez de asumir que todo .json es una corrida."""
    out = {}
    for f in glob.glob(os.path.join("resultados", "*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                r = json.load(fh)
        except Exception as e:
            print(f"  (no se pudo leer {os.path.basename(f)}: {e})")
            continue
        if isinstance(r, dict) and "etiqueta" in r:
            out[r["etiqueta"]] = r
    return out


def estado_legible(r):
    """El limite se toma del JSON, NO se asume 1h: la corrida puede haberse
    hecho con otro limite y la tabla debe decir el que se uso de verdad."""
    if r.get("error"):
        return "error"
    if r.get("infactible"):
        return "infactible"
    if r.get("optimo"):
        return "optimo"
    if r.get("limite_tiempo"):
        lim = r.get("limite_tiempo_s")
        txt = (f"{lim/3600:.0f}h" if lim and lim >= 3600
               else f"{lim:.0f}s" if lim else "?")
        return (f"limite {txt} (con sol.)" if r.get("tiene_solucion")
                else f"limite {txt} (sin sol.)")
    return str(r.get("status_solver"))


def fmt(v, d=2):
    return "-" if v is None else f"{v:.{d}f}"


# ===========================================================================
# tabla principal: las 15 instancias
# ===========================================================================

def tabla_principal(res):
    filas = []
    for n, K in D.instancias():
        et = f"n{n}_K{K}_espera"
        r = res.get(et)
        if r is None:
            filas.append({"n": n, "clientes": n - 1, "K": K,
                          "estado": "NO CORRIDA"})
            continue
        m = r.get("metricas") or {}
        filas.append({
            "n": n, "clientes": n - 1, "K": K, "K0": r["parametros"]["K0"],
            "Q": r["parametros"]["Q"], "Tmax": r["parametros"]["Tmax"],
            "solver": r["solver"], "estado": estado_legible(r),
            "factible": "si" if r.get("tiene_solucion") else "no",
            "espera_total": r.get("objetivo"),
            "cota": r.get("cota"), "gap": r.get("gap"),
            "tiempo_s": r.get("tiempo_solver") or r.get("tiempo_pared_s"),
            "nodos": r.get("nodos"),
            "rutas_usadas": m.get("num_rutas"),
            "dist_total": m.get("distancia_total"),
            "duracion_max": m.get("duracion_maxima"),
            "vars": r.get("num_vars"), "restr": r.get("num_restr"),
            "limite_s": r.get("limite_tiempo_s"),
            "violaciones": len(r.get("violaciones") or []),
        })
    return pd.DataFrame(filas)


def md_principal(df):
    L = ["| n | clientes | K | estado | factible | espera total | gap | "
         "tiempo (s) | rutas | solver |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for _, f in df.iterrows():
        gap = f.get("gap")
        gap_s = "-" if gap is None or pd.isna(gap) else (
            "0" if abs(gap) < 1e-9 else f"{gap*100:.3f}%")
        L.append(f"| {f['n']} | {f.get('clientes','')} | {f['K']} | "
                 f"{f['estado']} | {f.get('factible','-')} | "
                 f"{fmt(f.get('espera_total'))} | {gap_s} | "
                 f"{fmt(f.get('tiempo_s'),1)} | "
                 f"{f.get('rutas_usadas') if f.get('rutas_usadas') is not None else '-'} | "
                 f"{f.get('solver','-')} |")
    return "\n".join(L)


# ===========================================================================
# comparaciones (items 3 y 4)
# ===========================================================================

def tabla_comparaciones(res):
    filas = []
    for et, r in sorted(res.items()):
        if not r.get("tiene_solucion"):
            continue
        m = r.get("metricas") or {}
        if r["objetivo_tipo"] == "espera" and r["release"]:
            modelo = "extendido (min espera)"
        elif r["objetivo_tipo"] == "distancia":
            modelo = "min distancia"
        elif r["objetivo_tipo"] == "makespan" and not r["release"]:
            modelo = "base (min makespan)"
        else:
            modelo = f"{r['objetivo_tipo']} release={r['release']}"
        # Las corridas del experimento de Big-M son el MISMO modelo; si no se
        # distinguen aparecen como filas duplicadas en la comparacion.
        if r.get("big_m") not in (None, "profesor"):
            modelo += f" [Big-M {r['big_m']}]"
        filas.append({
            "n": r["n"], "K": r["K"], "modelo": modelo,
            "estado": estado_legible(r),
            "espera_total": m.get("espera_total"),
            "dist_total": m.get("distancia_total"),
            "duracion_max": m.get("duracion_maxima"),
            "makespan_abs": m.get("makespan_absoluto"),
            "rutas": m.get("num_rutas"),
            "tiempo_s": r.get("tiempo_solver") or r.get("tiempo_pared_s"),
            "gap": r.get("gap"),
            "secuencias": " | ".join("-".join(str(i) for i in ru)
                                     for ru in (r.get("rutas") or [])),
        })
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    orden = {"extendido (min espera)": 0, "min distancia": 1,
             "base (min makespan)": 2}
    df["_o"] = df["modelo"].map(lambda s: orden.get(s, 9))
    return df.sort_values(["n", "K", "_o"]).drop(columns="_o")


def md_comparaciones(df):
    if df.empty:
        return "_(sin comparaciones todavia)_"
    L = ["| n | K | modelo | espera total | distancia total | duracion max | "
         "rutas | rutas (secuencias) |",
         "|---|---|---|---|---|---|---|---|"]
    for _, f in df.iterrows():
        L.append(f"| {f['n']} | {f['K']} | {f['modelo']} | "
                 f"{fmt(f['espera_total'])} | {fmt(f['dist_total'])} | "
                 f"{fmt(f['duracion_max'])} | {f['rutas']} | "
                 f"`{f['secuencias']}` |")
    return "\n".join(L)


# ===========================================================================
# figuras
# ===========================================================================

def fig_tiempos(df):
    """
    Tres paneles. Dos cuidados que la version simple no tenia:

    1. Los tiempos estan CENSURADOS en el limite: casi todas las instancias lo
       agotan, asi que una curva tiempo-vs-n se ve plana y sugiere, falsamente,
       que el tiempo deja de crecer. Se marca el limite y se distinguen los
       puntos censurados (hueco) de los resueltos a optimalidad (relleno).
    2. n >= 25 se resolvio con HiGHS, no con Gurobi. Mezclar sus gaps en una
       sola curva sin avisar atribuye al tamano algo que es del solver.
    """
    d = df[df["tiempo_s"].notna()].copy()
    if d.empty:
        return
    lim = d["limite_s"].dropna().max() if "limite_s" in d else None

    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.4))
    colores = {0: "tab:blue", 1: "tab:orange", 2: "tab:green"}

    for off, sub in d.groupby(d["K"] - d["K0"]):
        s = sub.sort_values("n")
        c = colores.get(off, "gray")
        et = f"K = K0+{off}"

        # --- panel 1: tiempo, distinguiendo censurado de resuelto ---------
        ax[0].plot(s["n"], s["tiempo_s"], "-", color=c, label=et, lw=1.5)
        opt = s[s["estado"] == "optimo"]
        cen = s[s["estado"] != "optimo"]
        ax[0].plot(opt["n"], opt["tiempo_s"], "o", color=c, ms=8)
        ax[0].plot(cen["n"], cen["tiempo_s"], "o", color=c, ms=8,
                   markerfacecolor="white", markeredgewidth=1.8)

        # --- panel 2: gap -------------------------------------------------
        g = s[s["gap"].notna()]
        ax[1].plot(g["n"], g["gap"] * 100, "o-", color=c, label=et, lw=1.5)

        # --- panel 3: cota dual contra la cota valida trivial -------------
        b = s[s["cota"].notna()]
        ax[2].plot(b["n"], b["cota"], "o-", color=c, label=et, lw=1.5)

    if lim:
        ax[0].axhline(lim, ls="--", c="crimson", lw=1.2)
        ax[0].annotate(f"límite = {lim:.0f}s", (0.02, 0.93), color="crimson",
                       xycoords="axes fraction", fontsize=9)
    ax[0].set_yscale("log")
    ax[0].set_xlabel("n (nodos)"); ax[0].set_ylabel("tiempo (s, escala log)")
    ax[0].set_title("Tiempo de cómputo\n(relleno = óptimo probado; "
                    "hueco = censurado en el límite)", fontsize=10)
    ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)

    ax[1].set_xlabel("n (nodos)"); ax[1].set_ylabel("gap final (%)")
    ax[1].set_title("Gap al terminar", fontsize=10)
    ax[1].grid(alpha=.3); ax[1].legend(fontsize=8)

    # cota valida trivial sum d_0j, que la relajacion no conoce
    ns = sorted(d["n"].unique())
    triv = []
    for n in ns:
        dd = D.generar(n)
        triv.append(sum(dd["dist"][0][j] for j in range(1, n)))
    ax[2].plot(ns, triv, "k--", lw=1.8, label="cota válida $\\sum_j d_{0j}$")
    ax[2].axhline(0, c="crimson", lw=1, ls=":")
    ax[2].annotate("cotas negativas:\nimposibles, la espera es ≥ 0",
                   (0.03, 0.06), xycoords="axes fraction", fontsize=8,
                   color="crimson")
    ax[2].set_xlabel("n (nodos)"); ax[2].set_ylabel("cota inferior (dual)")
    ax[2].set_title("Cota dual alcanzada vs cota válida trivial", fontsize=10)
    ax[2].grid(alpha=.3); ax[2].legend(fontsize=8)

    # marcar donde cambia el solver
    for a in ax:
        a.axvspan(22.5, 31, color="gray", alpha=.10)
        a.annotate("HiGHS", (0.88, 0.02), xycoords="axes fraction",
                   fontsize=8, color="gray")
        a.annotate("Gurobi", (0.30, 0.02), xycoords="axes fraction",
                   fontsize=8, color="gray")

    fig.tight_layout()
    fig.savefig(os.path.join("figuras", "tiempos.png"), dpi=150)
    plt.close(fig)


def fig_rutas(res, n, K):
    """Compara visualmente las rutas de los tres modelos en una instancia."""
    quiere = [(f"n{n}_K{K}_espera", "Extendido: min espera"),
              (f"n{n}_K{K}_distancia", "Min distancia total"),
              (f"n{n}_K{K}_makespan_norelease", "Base: min makespan")]
    hay = [(res[e], t) for e, t in quiere
           if e in res and res[e].get("rutas")]
    if not hay:
        return

    d = D.generar(n)
    x, y, r = d["x"], d["y"], d["r"]
    fig, axes = plt.subplots(1, len(hay), figsize=(5.2 * len(hay), 5.2),
                             squeeze=False)
    colores = plt.cm.tab10.colors

    for ax, (rr, titulo) in zip(axes[0], hay):
        for k, ruta in enumerate(rr["rutas"]):
            xs = [x[i] for i in ruta]
            ys = [y[i] for i in ruta]
            ax.plot(xs, ys, "-", color=colores[k % 10], lw=1.6,
                    label=f"ruta {k+1}", zorder=2)
        for i in range(1, n):
            ax.scatter([x[i]], [y[i]], s=90,
                       c=("tab:red" if r[i] > 0 else "white"),
                       edgecolors="black", zorder=3)
            ax.annotate(f"{i}", (x[i], y[i]), fontsize=7,
                        ha="center", va="center", zorder=4)
        ax.scatter([x[0]], [y[0]], marker="s", s=160, c="black", zorder=5)
        ax.annotate("dep", (x[0], y[0]), fontsize=8, xytext=(6, 6),
                    textcoords="offset points")
        # La espera se RECALCULA con los tiempos de liberacion reales para las
        # tres soluciones. La corrida del modelo base usa release=off, asi que
        # su 'metricas.espera_total' esta medida con r=0 y no es comparable;
        # si se usara ese valor, la figura contradiria la tabla de comparar.py.
        m = VA.evaluar(d, rr["rutas"], release=True)
        ax.set_title(f"{titulo}\nespera={m['espera_total']:.0f}  "
                     f"dist={m['distancia_total']:.0f}  "
                     f"rutas={m['num_rutas']}", fontsize=10)
        ax.legend(fontsize=7); ax.grid(alpha=.25)
        ax.set_aspect("equal", adjustable="datalim")

    fig.suptitle(f"n={n}, K={K}   (rojo = cliente con r_i > 0; espera medida "
                 f"con liberaciones reales en los tres casos)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join("figuras", f"rutas_n{n}_K{K}.png"), dpi=150)
    plt.close(fig)


# ===========================================================================

def main():
    res = cargar()
    print(f"{len(res)} resultados leidos\n")

    df = tabla_principal(res)
    df.to_csv(os.path.join("resultados", "tabla_principal.csv"), index=False)
    md = md_principal(df)
    with open(os.path.join("resultados", "tabla_principal.md"), "w",
              encoding="utf-8") as f:
        f.write(md)
    print("TABLA PRINCIPAL (item 1)\n")
    print(md)

    cols = ["n", "K", "estado", "tiempo_s", "gap", "nodos", "vars", "restr",
            "solver"]
    dt = df[[c for c in cols if c in df.columns]]
    dt.to_csv(os.path.join("resultados", "tabla_tiempos.csv"), index=False)

    dc = tabla_comparaciones(res)
    if not dc.empty:
        dc.to_csv(os.path.join("resultados", "tabla_comparaciones.csv"),
                  index=False)
        mdc = md_comparaciones(dc)
        with open(os.path.join("resultados", "tabla_comparaciones.md"), "w",
                  encoding="utf-8") as f:
            f.write(mdc)
        print("\n\nTABLA DE COMPARACIONES (items 3 y 4)\n")
        print(mdc)

    fig_tiempos(df)
    for n, K in {(r["n"], r["K"]) for r in res.values()}:
        fig_rutas(res, n, K)
    print("\nfiguras en figuras/")

    malas = [(e, r["violaciones"]) for e, r in res.items()
             if r.get("violaciones")]
    if malas:
        print("\n!! SOLUCIONES CON VIOLACIONES:")
        for e, v in malas:
            print(" ", e, v)
    else:
        print("\nninguna solucion viola restricciones")


if __name__ == "__main__":
    main()
