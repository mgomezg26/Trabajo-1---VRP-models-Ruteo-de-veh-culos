# Trabajo de Modelación 1: Ruteo de Vehículos con tiempos de liberación

Guía para entender el código y correrlo.

---

## 1. Qué hace cada archivo

| Archivo | Qué es |
|---|---|
| `datos.py` | Genera los datos de cada instancia. Las líneas marcadas `# [PROFESOR]` son **copia textual** del script del curso: semillas y generación de datos intactas, como exige el enunciado. |
| `modelo.py` | El modelo MILP. Escrito **una sola vez** en PuLP y despachado a Gurobi o a HiGHS. Tiene un interruptor de objetivo (`espera` / `distancia` / `makespan`) y otro de tiempos de liberación (`release`). |
| `validar.py` | Verificador **independiente**. Recalcula todo desde las rutas sin usar el solver y compara contra lo que reportó el solver. |
| `correr.py` | Resuelve **una** instancia y guarda un JSON con todo (estado, objetivo, gap, cota, nodos, tiempo, rutas, horas de salida y llegada). |
| `lote.py` | Corre varias instancias en paralelo, una por proceso. |
| `regresion.py` | Prueba de equivalencia: construye el modelo del profesor en gurobipy y lo compara contra el mío. |
| `analizar.py` | Lee los JSON y produce las tablas y figuras del informe. |
| `comparar.py` | Comparaciones de los ítems 3 y 4, midiendo **las tres soluciones con la misma métrica** (ver el Paso 7). |
| `referencia_profesor_*.py` | Los scripts originales, sin tocar, como referencia. |

---

## 2. Requisitos

Tienen que quedar instalados en tu máquina:

```bash
python -m pip install gurobipy numpy pandas matplotlib pulp highspy
```

---

## 3. Paso a paso para correrlo

### Paso 1 — Ver los parámetros de las instancias

```bash
python datos.py
```

Confirma que las semillas producen los datos esperados y muestra las 15 combinaciones `(n, K)`.

### Paso 2 — Comprobar que mi modelo reproduce el del profesor

```bash
python regresion.py 120
```

Con `release=off` y objetivo `makespan`, mi modelo debe dar el mismo valor que el del profesor. Si los dos prueban optimalidad y coinciden, la base es correcta.

### Paso 3 — Resolver una instancia sola (para probar)

```bash
python correr.py --n 10 --K 2 --objetivo espera --tiempo 300
```

Imprime el log del solver, las rutas con sus horas, y **el resultado del validador**. Guarda `resultados/n10_K2_espera.json`.

### Paso 4 — Las 15 instancias del enunciado

```bash
python lote.py --que principal --procesos 3 --tiempo 300 --hilos 2
```

Para la versión final con el límite de 1 hora que pide el enunciado:

```bash
python lote.py --que principal --procesos 3 --tiempo 3600 --hilos 2
```


### Paso 5 — Las comparaciones (ítems 3 y 4 del enunciado)

```bash
python lote.py --que comparaciones --procesos 3 --tiempo 300
```

Resuelve, sobre las instancias con gap = 0, la variante que minimiza distancia y el modelo base. Las instancias están en la lista `COMPARAR` al inicio de `lote.py`; ajústala si quieres otras.

### Paso 6 — Tablas y figuras

```bash
python analizar.py
```

Genera en `resultados/` las tablas (`.csv` para Excel y `.md` para pegar) y en `figuras/` las gráficas de tiempo, gap y comparación visual de rutas.

### Paso 7 — La tabla de comparación justa

```bash
python comparar.py
```

**Este paso es necesario, no opcional.** Las corridas del modelo base usan `release=off`, así que la "espera" que reportan está calculada con `r = 0` y **no es comparable** con la del modelo extendido. `comparar.py` toma las rutas de cada modelo y las evalúa todas con los tiempos de liberación reales, fijando la salida de cada ruta en el mayor `r` de sus clientes. Eso es lo que responde de verdad los ítems 3 y 4.

### Paso 8 — Las desigualdades válidas

```bash
python lote.py --que cortes --procesos 3 --tiempo 300
```

Repite las 15 instancias agregando `T_j ≥ r_j + d_0j`, que es una desigualdad válida (ver punto 6). Mejora mucho las cotas y da material para el análisis del ítem 2.

### Paso 9 (opcional) — El experimento de Big-M

```bash
python lote.py --que bigm --tiempo 300
```

Repite unas instancias con un Big-M más ajustado.

---

## 4. El modelo, en palabras

El modelo base del Anexo 1 supone que todos los vehículos salen en `t = 0`. Con tiempos de liberación eso ya no sirve: un vehículo que visita al cliente `i` **no puede salir antes de `r_i`**.

La pieza nueva es una variable por cliente:

> `u_i` = hora de salida del depósito de la ruta que atiende al cliente `i`

y tres cosas que hay que imponer sobre ella:

1. **`u_i ≥ r_i`** — respeta la liberación del cliente que visita (va como cota inferior de la variable).
2. **`u_i = u_j` si `i` y `j` van en la misma ruta** — todos los clientes de una ruta comparten la hora de salida.
3. **`T_j ≥ u_j + d_0j`** para el primer cliente — la llegada se cuenta desde la salida, no desde cero.

El punto 2 es donde es fácil equivocarse. Propagar en un solo sentido (`u_j ≥ u_i` cuando se usa el arco `(i,j)`) **no alcanza**: subestimaría la espera, porque el vehículo debe salir después del mayor `r` de **toda** la ruta, y ese máximo puede estar en cualquier posición. Por eso se imponen las dos desigualdades, que juntas dan la igualdad:

```
u_j - u_i <= Mu * (1 - X_ij - X_ji)
u_i - u_j <= Mu * (1 - X_ij - X_ji)
```

Escritas por pareja **no ordenada**, lo que cuesta la mitad de las filas.

El objetivo pasa a ser `min Σ (T_i - r_i)`, y la restricción de longitud de ruta pasa a ser `regreso - salida ≤ Tmax`, es decir la **duración**, no la hora absoluta.

Con `release=False` el modelo colapsa exactamente al del profesor (`u_i` queda en 0). Eso es lo que verifica `regresion.py`.

---

## 5. Dos cosas que hay que saber al leer los resultados

### La licencia de Gurobi solo llega hasta n = 20

Medido, no supuesto:

| n | variables | restricciones | licencia gratuita |
|---|---|---|---|
| 10 | 320 | 402 | cabe |
| 15 | 705 | 902 | cabe |
| 20 | 1240 | 1602 | cabe |
| 25 | 1925 | 2502 | **no cabe** |
| 30 | 2760 | 3602 | **no cabe** |

(tamaños medidos en las corridas, campos `num_vars` y `num_restr` de cada JSON)

La licencia que viene con `pip install gurobipy` admite 2000 variables y 2000 restricciones. Por eso `correr.py` usa **Gurobi para n ≤ 20 y HiGHS para n = 25 y 30**.

En n = 25 y 30 **el gap y el tiempo son de HiGHS, no de Gurobi**, y no son directamente comparables con los de las otras instancias. Si consigues la licencia académica (gratis con el correo institucional), fuerza Gurobi en todas con `--solver gurobi` y quedan homogéneas.

### El límite de tiempo usado

El enunciado pide limitar a **una hora por instancia**. Los resultados de esta corrida se generaron con **300 s** por falta de tiempo antes de la entrega. Para la versión definitiva hay que repetir el Paso 4 con `--tiempo 3600`. **El límite usado queda guardado en cada JSON** (`limite_tiempo_s`), así que no hay riesgo de reportar una cosa por otra.

---

## 6. La desigualdad válida (por qué existe `--cortes`)

Las cotas duales de las instancias grandes salieron **negativas** (−3944 en
n = 25, −5654 en n = 30) para una cantidad que es una suma de términos
`T_i − r_i ≥ 0` y por lo tanto **nunca puede ser negativa**.

El motivo: con `X` fraccionario los Big-M de la continuidad temporal quedan
desactivados, y entonces nada impide que `T_j` caiga por debajo de `r_j`. La
relajación se "compra" espera negativa.

De ahí sale una desigualdad válida. El vehículo que atiende a `j` parte en
`u_j ≥ r_j` y recorre del depósito hasta `j` al menos `d_0j` (desigualdad
triangular):

```
T_j ≥ u_j + d_0j ≥ r_j + d_0j
```

No corta ninguna solución entera factible. Comprobado: con `--cortes on` las
tres instancias de n = 10 dan el mismo óptimo y las mismas rutas, y el tiempo
baja de 37.6 s a 1.2 s (K = 2) y de 15.5 s a 0.7 s (K = 3).

La corrida **principal** se hizo **sin** estas desigualdades, para reportar la
formulación tal como sale del enunciado. Las corridas con `--cortes on` quedan
aparte (etiquetas `*_cortes`) como experimento de mejora.

---

## 7. Un error que valió la pena atrapar

El validador (`validar.py`) sirvió de inmediato. En la primera corrida el solver reportó un objetivo de **6730.17** y el recálculo independiente dio **4653.17**. La diferencia, 2077.00, era exactamente `Σ r_i`.

La causa: escribir el objetivo como `lpSum(T[j] - r[j])` deja una **constante** `-Σr` en la función objetivo, y **PuLP no le pasa esa constante al solver**. Eso tenía dos consecuencias:

1. el valor objetivo reportado quedaba inflado en `Σ r`;
2. y lo más grave, el **gap relativo** se calculaba sobre `Σ T` en vez de sobre `Σ(T - r)`. Como `Σ r > 0`, **el gap reportado subestimaba el gap verdadero**.

La corrección fue cargar la constante en una variable fija en 1, para que el solver la vea como un término lineal más. `correr.py` ahora aborta si detecta cualquier constante en el objetivo, para que no vuelva a pasar inadvertido.

Vale la pena mencionarlo: es justo el tipo de detalle que separa "el modelo corrió" de "el modelo está bien".

---

## 8. Qué significa cada columna de la tabla

| Columna | Qué es |
|---|---|
| `estado` | `optimo` (gap probado = 0), `infactible` (**probado**, no hay solución), `limite (con sol.)` (se acabó el tiempo pero hay solución factible), `limite (sin sol.)` (se acabó el tiempo sin encontrar ninguna) |
| `espera_total` | El objetivo: `Σ (llegada_i − r_i)` |
| `gap` | Gap relativo final del solver. Con `MIPGap = 0` un cero es cero de verdad, no el 1e-4 que trae Gurobi por defecto |
| `cota` | Mejor cota inferior (dual bound) |
| `tiempo_s` | Tiempo del solver |
| `rutas_usadas` | Rutas realmente usadas, que puede ser menor que `K` |
| `violaciones` | Cuántas restricciones viola la solución según el validador. **Debe ser 0 en todas.** |

Ojo con dos distinciones que el informe debe respetar:

- **`infactible` no es lo mismo que `limite (sin sol.)`.** Solo la primera prueba que no existe solución.
- **`rutas_usadas ≤ K`**: la restricción es un techo, no una igualdad.

---

## 9. Nota sobre los tiempos medidos

Las corridas se hacen **3 en paralelo**, así que los tiempos no son los de una corrida aislada en una máquina desocupada. Esto hay que decirlo en la sección de configuración experimental. Si quieres tiempos limpios para el análisis del ítem 2, corre con `--procesos 1`, a cambio de que tarde el triple.

Dato adicional para ese análisis: `r[0]`, el tiempo de liberación del depósito, lo genera el bucle del profesor pero el depósito no es cliente y no tiene liberación, así que el modelo lo ignora. En estas instancias resultó ser 0 en los cinco tamaños, así que no cambia nada; queda registrado en el JSON como `r_deposito_generado` por transparencia.
