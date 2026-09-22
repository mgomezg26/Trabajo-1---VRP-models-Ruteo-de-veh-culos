# Notas para el informe

Material para que escribas el Word. Las tablas con números salen de
`python analizar.py` (quedan en `resultados/*.md` para pegar y `*.csv` para Excel).

El enunciado no impone plantilla: solo pide cuatro resultados. La estructura de
abajo está ordenada para que cada sección responda uno de ellos.

---

## Sección 1 — El modelo extendido

### Lo que cambia respecto al modelo base

El modelo base del Anexo 1 supone que **todos los vehículos salen en `t = 0`**
(restricción 7: `t_0 = 0`). Con tiempos de liberación eso se rompe: si un
vehículo visita al cliente `i`, no puede partir del depósito antes de `r_i`.

Como todos los clientes de una ruta comparten el mismo vehículo, comparten la
hora de salida. Luego la hora de salida de una ruta debe ser **al menos el mayor
`r_i` de todos los clientes que atiende**. Y como el objetivo es minimizar
espera, en el óptimo será exactamente ese máximo.

### Conjuntos y parámetros

Iguales a los del Anexo 1, más:

- `r_i ∈ R+`: tiempo de liberación del cliente `i ∈ V⁺`.

### Variables de decisión

| Variable | Significado |
|---|---|
| `X_ij ∈ {0,1}` | 1 si se recorre el arco `(i,j)` |
| `T_i ≥ 0` | tiempo de llegada **absoluto** al nodo `i` |
| `u_i ≥ 0` | **(nueva)** hora de salida del depósito de la ruta que atiende al cliente `i` |
| `w_ij ≥ 0` | variable de orden MTZ |
| `L_ij ≥ 0` | carga acumulada en el arco `(i,j)` |

Nota sobre `t_i` vs `T_i`: en el modelo base `t_i` se mide desde 0, que es la
hora de salida común. Aquí cada ruta sale en un instante distinto, así que `T_i`
es tiempo absoluto y la duración de la ruta se obtiene restando `u_i`.

### Función objetivo

```
min  Z = Σ_{i ∈ V⁺} ( T_i − r_i )
```

La espera en el cliente `i` es la diferencia entre la llegada y su liberación.

### Restricciones

Se conservan del Anexo 1, sin cambios: (2) visita única, (3) conservación de
flujo, (4) sin auto-loops, (5) límite de vehículos, (9) y (10) MTZ,
(11) y (12) carga.

Se **reemplazan** o **agregan**:

**Continuidad temporal entre clientes** (era la (6), restringida a clientes):

```
T_j ≥ T_i + d_ij − M (1 − X_ij)        ∀ i, j ∈ V⁺, i ≠ j
```

**Continuidad temporal desde el depósito** (nueva; sustituye `t_0 = 0`):

```
T_j ≥ u_j + d_0j − M (1 − X_0j)        ∀ j ∈ V⁺
```

La llegada al primer cliente se cuenta **desde la hora de salida**, no desde cero.

**Respeto del tiempo de liberación** (nueva):

```
u_j ≥ r_j                              ∀ j ∈ V⁺
```

**Consistencia de la hora de salida dentro de la ruta** (nueva, la clave):

```
u_j − u_i ≤ M_u (1 − X_ij − X_ji)      ∀ i, j ∈ V⁺, i < j
u_i − u_j ≤ M_u (1 − X_ij − X_ji)      ∀ i, j ∈ V⁺, i < j
```

con `M_u = max_i r_i`.

**Longitud de la ruta limitada por `Tmax`** (era la (8), ahora es duración):

```
T_j + d_j0 − u_j ≤ Tmax                ∀ j ∈ V⁺
```

Es decir, *regreso menos salida*, como pide el enunciado.

### Dos puntos que conviene justificar explícitamente en el informe

**1. Por qué la consistencia de `u` necesita las dos desigualdades.**

Propagar en un solo sentido (solo `u_j ≥ u_i` cuando se usa el arco `(i,j)`)
**no alcanza**. El vehículo debe salir después del mayor `r` de *toda* la ruta,
y ese máximo puede estar en cualquier posición, incluso en el último cliente.
Con una sola desigualdad la hora de salida del primer cliente quedaría
subestimada y el modelo reportaría una espera menor que la real. Las dos
desigualdades juntas fuerzan `u_i = u_j` cuando `i` y `j` son consecutivos, y
por transitividad a lo largo de la ruta todos los clientes comparten la salida.

**2. Por qué se escriben por pareja no ordenada.**

Usar `(1 − X_ij − X_ji)` en vez de `(1 − X_ij)` permite cubrir los dos sentidos
del arco con la mitad de las filas: `(n−1)(n−2)` en lugar de `2(n−1)(n−2)`.
No se pierde nada porque MTZ ya prohíbe los ciclos de dos nodos, así que
`X_ij` y `X_ji` no pueden valer 1 a la vez en una solución válida.

**3. Consistencia con el modelo base.** Con `r ≡ 0` se obtiene `u ≡ 0` y el
modelo se reduce exactamente al del Anexo 1. Eso se verificó numéricamente
(ver Sección 2).

**4. Cómo se interpretó el límite `Tmax` (decisión de modelado, vale declararla).**

Hay una ambigüedad real entre el Anexo 1 y el enunciado de los atributos
adicionales, y conviene resolverla explícitamente en el informe.

La restricción (8) del Anexo 1 es **por cliente**:

```
t_j + d_j0 ≤ Tmax        ∀ j ∈ V⁺
```

es decir, "llegar a `j` y volver directo al depósito" no puede pasar de `Tmax`,
*para todo* cliente `j`. En cambio el enunciado de los atributos adicionales
dice: "la diferencia entre el tiempo de regreso al depósito y el tiempo de
partida debe ser menor o igual a dicha cantidad", lo que se lee como una cota
sobre la **duración total de la ruta**, que solo involucra al último cliente.

Las dos lecturas **no son equivalentes**: la forma por cliente es más
restrictiva. Si un cliente lejano se visita temprano, `t_j + d_j0` puede ser
mayor que la duración real de la ruta, y la forma por cliente rechazaría una
ruta que la lectura de "duración total" aceptaría.

Aquí se conservó la **forma por cliente** del Anexo 1, cambiando solo el punto
de referencia de tiempo absoluto a duración:

```
T_j + d_j0 − u_j ≤ Tmax   ∀ j ∈ V⁺
```

Razón: el enunciado pide el problema base "con las siguientes modificaciones",
y la modificación declarada es el punto de referencia (ahora relativo a la
partida), no la estructura de la restricción. Mantenerla por cliente conserva
además la comparabilidad con el modelo base del ítem 4.

Dato que hace que la decisión sea poco riesgosa en estas instancias: el mayor
ida-y-vuelta directo (`d_0j + d_j0`) va de 1313 a 1555 según la instancia,
siempre por debajo del `Tmax` correspondiente (2366 a 3885). Así que ningún
cliente queda excluido por sí solo; las dos lecturas solo podrían diferir por
el tiempo acumulado a lo largo de la ruta.

---

## Sección 2 — Configuración experimental

Esto hay que declararlo, porque condiciona la lectura de todos los resultados.

### Implementación

El modelo se escribió **una sola vez en PuLP** y se despacha a dos solvers.
Escribirlo una vez evita el riesgo de que dos implementaciones del mismo modelo
se desincronicen.

### Verificación de correctitud

Dos pruebas, ambas reproducibles:

1. **Verificador independiente** (`validar.py`): recalcula visitas, cargas,
   duraciones, horas de salida y espera total a partir de las rutas, **sin usar
   el solver**, y compara contra el valor reportado. Ninguna de las soluciones
   obtenidas viola restricciones.

2. **Prueba de regresión** (`regresion.py`): se construyó el modelo base tal
   cual está en el script del curso (en gurobipy) y se comparó contra el mío con
   `release=off`. En los tres casos que alcanzaron optimalidad probada
   (n = 10 con K = 1, 2, 3) los valores coinciden a precisión de máquina
   (diferencias de 1e-11, 1e-7 y 1e-12). En n = 15 ninguno de los dos cerró el
   gap dentro del límite, así que la comparación de incumbentes no es
   concluyente ahí; no indica discrepancia de formulación.

### Un error de implementación que vale la pena reportar

Conviene mencionarlo: muestra por qué hace falta el verificador independiente.

Escribir el objetivo como `Σ (T_i − r_i)` deja una **constante** `−Σ r_i` en la
función objetivo, y **PuLP no le transmite esa constante al solver**. El efecto
fue doble:

1. el valor objetivo reportado quedaba inflado en `Σ r_i` (en n = 10:
   6730.17 reportado contra 4653.17 real, exactamente 2077 = `Σ r_i` de más);
2. y lo más grave, el **gap relativo** se calculaba sobre `Σ T_i` en lugar de
   sobre `Σ (T_i − r_i)`. Como `Σ r_i > 0`, **el gap reportado subestimaba el
   gap verdadero** del objetivo que pide el enunciado.

La corrección fue cargar la constante en una variable fija en 1, de modo que el
solver la vea como un término lineal. Lo detectó el verificador independiente en
la primera corrida.

### Solvers: por qué no todo es Gurobi

La licencia que viene con `pip install gurobipy` admite **2000 variables y 2000
restricciones**. El modelo extendido las excede a partir de n = 25:

| n | variables | restricciones | ¿cabe? |
|---|---|---|---|
| 10 | 320 | 402 | sí |
| 15 | 705 | 902 | sí |
| 20 | 1240 | 1602 | sí |
| 25 | 1925 | 2502 | **no** |
| 30 | 2760 | 3602 | **no** |

(tamaños medidos, no estimados: campos `num_vars` y `num_restr` de cada JSON)

Por eso **n ≤ 20 se resolvió con Gurobi y n = 25, 30 con HiGHS**.

Consecuencia que hay que advertir en el informe: en n = 25 y 30 **el gap y el
tiempo son de HiGHS, no de Gurobi**, y no son directamente comparables con el
resto de la tabla. Con licencia académica (gratuita con el correo institucional)
se puede homogeneizar corriendo todo con Gurobi.

### Límite de tiempo

El enunciado pide una hora por instancia. **Esta corrida usó 300 s** por falta
de tiempo antes de la entrega. El límite quedó registrado en cada archivo de
resultados, y repetir con el límite completo es un solo flag
(`--tiempo 3600`). Si repites, actualiza la tabla y este párrafo.

### Paralelismo (afecta los tiempos medidos)

Las instancias se corrieron **3 en paralelo, 2 hilos cada una**, sobre un
AMD Ryzen 7 7445HS (6 núcleos físicos, 12 hilos) con 16 GB de RAM. Por lo tanto
**los tiempos no son de una corrida aislada en una máquina desocupada** y
podrían mejorar con `--procesos 1`. Hay que decirlo al presentar el ítem 2.

### Parámetros del solver

`MIPGap = 0` (para que "gap igual a cero" signifique cero y no el 1e-4 que
Gurobi trae por defecto), `Seed = 0`, `Threads = 2`.

---

## Sección 3 — Resultados de las 15 instancias (ítem 1)

Pega aquí `resultados/tabla_principal.md`.

Parámetros generados por instancia (semilla 1234567, intacta):

| n | clientes | avgdist | Σq | Q | K0 | Tmax | M | clientes con r>0 | max r |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 9 | 338 | 62 | 93 | 1 | 2366 | 7202 | 5 | 600 |
| 15 | 14 | 370 | 99 | 99 | 1 | 3885 | 11282 | 6 | 600 |
| 20 | 19 | 376 | 119 | 90 | 2 | 2632 | 15546 | 8 | 600 |
| 25 | 24 | 364 | 141 | 85 | 2 | 3185 | 19433 | 9 | 600 |
| 30 | 29 | 363 | 144 | 72 | 2 | 3812 | 23320 | 12 | 670 |

Combinaciones: `K ∈ {1,2,3}` para n = 10 y 15; `K ∈ {2,3,4}` para n = 20, 25 y 30.

Observaciones que conviene hacer al presentar la tabla:

- **`n` incluye el depósito.** Los nodos van de 0 a n−1, así que hay n−1
  clientes. El enunciado dice "número de clientes"; vale aclarar la convención
  para que no haya ambigüedad al leer la tabla.
- **La capacidad casi no restringe**, porque `Q = ⌈Σq/n · 15⌉` es holgada. Con
  `K0 = ⌈Σq/Q⌉` resulta `K0 = 1` para n = 10 y 15, y `K0 = 2` para el resto. Dos
  excepciones donde sí aprieta: en n = 15 la capacidad total con `K0` es
  exactamente 99 = Σq, y en n = 30 es exactamente 144 = Σq. En esos dos casos,
  con `K = K0` los vehículos deben ir **exactamente llenos**.
- **Ningún cliente es inalcanzable**: el mayor ida-y-vuelta directo
  (`d_0j + d_j0`) es 1313 a 1555 según la instancia, bien por debajo de `Tmax`.
  Así que la infactibilidad, si aparece, no viene de un cliente aislado.
- **`rutas_usadas ≤ K`**: la restricción (5) es un techo, no una igualdad, y
  varias instancias usan menos vehículos de los permitidos.
- **Distinguir "infactible" de "sin solución"**: solo lo primero prueba que no
  existe solución. Lo segundo significa que el solver agotó el tiempo sin
  encontrar ninguna. La tabla los reporta por separado.
- **Efecto de K sobre la espera**: en n = 10 la espera baja de 9862 (K=1) a
  4653 (K=2) a 3704 (K=3). Más vehículos permiten rutas más cortas y que cada
  una salga más cerca de la liberación de sus propios clientes.

---

## Sección 4 — Análisis del tiempo de cómputo (ítem 2)

Figuras: `figuras/tiempos.png` (tiempo vs n en escala log, y gap vs n).

### El factor dominante: la relajación lineal es extremadamente débil

Esto es lo más importante del análisis, y la evidencia es contundente.

**Síntoma 1: la relajación da cotas NEGATIVAS para una cantidad que es
forzosamente positiva.** La espera total es una suma de diferencias
`T_i − r_i ≥ 0`, así que el óptimo nunca puede ser negativo. Pero las cotas
duales reportadas fueron:

| n | cota dual reportada |
|---|---|
| 25 (K = 2, 4) | **−3944** |
| 25 (K = 3) | **−3842** |
| 30 (K = 2, 3, 4) | **−5654** |

Y en n = 10, K = 2 el primer LP de la raíz da **−14.4**; después de los cortes
propios de Gurobi sube apenas a **~50**, contra un óptimo de **4653**.

**Por qué pasa.** Con `X` fraccionario, los Big-M de las restricciones de
continuidad temporal (R5 y R6) quedan desactivados, y entonces nada impide que
`T_j` caiga **por debajo** de `r_j`. La relajación "compra" espera negativa. El
solver arranca sin ninguna información útil y tiene que cerrar todo el intervalo
explorando el árbol: en n = 10, K = 2 exploró **96 372 nodos** para probar
optimalidad de un problema de **9 clientes**.

**Síntoma 2: el mismo modelo con otro objetivo es fácil.** La misma instancia
(n = 10, K = 2), cambiando solo la función objetivo a distancia total, tiene
cota en la raíz de **1389.8** contra un óptimo de **1962.9** (gap en la raíz
del 29%) y **cierra en 0 segundos, en la raíz, sin ramificar**. La dificultad
no está en la estructura de ruteo ni en MTZ: está en el **objetivo de espera**.

### La mejora que se derivó de ese diagnóstico

El diagnóstico sugiere de inmediato una **desigualdad válida**. El vehículo que
atiende a `j` parte en `u_j ≥ r_j` y recorre del depósito hasta `j` una
distancia de al menos `d_0j` (desigualdad triangular, que la métrica euclídea
cumple). Por lo tanto:

```
T_j  ≥  u_j + d_0j  ≥  r_j + d_0j          ∀ j ∈ V⁺
```

y en consecuencia la espera total es al menos `Σ_j d_0j`. No corta ninguna
solución entera factible: solo le informa al solver algo que ya era cierto.

Esa cota trivial vale:

| n | `Σ d_0j` (cota válida) | mejor cota que lograron los solvers en 300 s |
|---|---|---|
| 10 | 2956 | ~50 (Gurobi, raíz) |
| 15 | 5538 | 5113 – 6001 (Gurobi) |
| 20 | **8016** | **6409 – 6882** (Gurobi) |
| 25 | **10155** | **−3944** (HiGHS) |
| 30 | **12297** | **−5654** (HiGHS) |

Es decir: en n = 20 la desigualdad da gratis una cota **mejor que la que Gurobi
alcanzó tras 300 segundos de búsqueda**, y en n = 25 y 30 convierte una cota
negativa sin sentido en una cota fuerte.

**Validez comprobada:** con las desigualdades activadas, las tres instancias de
n = 10 dan **exactamente el mismo óptimo y las mismas rutas** (9862.04,
4653.17, 3704.18). Si la desigualdad fuera inválida, cortaría el óptimo y se
vería aquí.

**Efecto medido en las 15 instancias** (tabla completa en
`resultados/tabla_cortes.md`; límite de 300 s en las dos corridas):

| n | K | solver | cota sin | cota con | gap sin | gap con | tiempo sin | tiempo con |
|---|---|---|---|---|---|---|---|---|
| 10 | 1 | Gurobi | 9862.0 | 9862.0 | 0 | 0 | 54.2 s | **18.8 s** |
| 10 | 2 | Gurobi | 4653.2 | 4653.2 | 0 | 0 | 37.2 s | **0.9 s** |
| 10 | 3 | Gurobi | 3704.2 | 3704.2 | 0 | 0 | 15.1 s | **0.4 s** |
| 15 | 1 | Gurobi | 6000.5 | 8309.8 | 70.2% | **58.7%** | 300 s | 300 s |
| 15 | 2 | Gurobi | 5248.6 | 7349.0 | 52.3% | **35.9%** | 300 s | 300 s |
| 15 | 3 | Gurobi | 5113.3 | 7074.5 | 36.2% | **11.7%** | 300 s | 300 s |
| 20 | 2 | Gurobi | 6881.9 | 10403.3 | 61.4% | **45.8%** | 300 s | 300 s |
| 20 | 3 | Gurobi | 6778.1 | 9816.0 | 50.1% | **27.7%** | 300 s | 300 s |
| 20 | 4 | Gurobi | 6409.2 | 9414.8 | 44.3% | **18.4%** | 300 s | 300 s |
| 25 | 2 | HiGHS | −3943.7 | 10532.0 | sin sol. | **72.0%** | 300 s | 300 s |
| 25 | 3 | HiGHS | −3842.3 | 10181.6 | 112.9% | **62.0%** | 300 s | 300 s |
| 25 | 4 | HiGHS | −3943.7 | 10155.2 | 115.8% | **53.5%** | 300 s | 300 s |
| 30 | 2 | HiGHS | −5653.7 | 12297.1 | sin sol. | sin sol. | 300 s | 300 s |
| 30 | 3 | HiGHS | −5653.7 | 12297.1 | 112.9% | **71.6%** | 300 s | 300 s |
| 30 | 4 | HiGHS | −5653.7 | 12297.1 | 114.1% | **66.7%** | 300 s | 300 s |

Tres cosas que vale la pena destacar de esta tabla:

1. **En n = 10 el óptimo y las rutas no cambian** (9862.04, 4653.17, 3704.18),
   que es la comprobación de que la desigualdad es válida, y el tiempo baja
   hasta **41×** (37.2 s → 0.9 s).
2. **El gap mejora en las 13 instancias donde había gap**, en algunos casos de
   forma drástica: n = 15 K = 3 pasa de 36.2% a 11.7%, y n = 20 K = 4 de 44.3%
   a 18.4%.
3. **n = 25, K = 2 pasa de no encontrar ninguna solución factible a encontrar
   una** (gap 72.0%). El corte no solo mejora la cota: también ayuda a la
   búsqueda de factibilidad.

Un detalle revelador: en n = 30 la cota con desigualdades es **exactamente**
12297.1 = `Σ d_0j` en los tres valores de K, y en n = 25 K = 4 es exactamente
10155.2. Es decir, en las instancias grandes **HiGHS no logra mejorar en 300 s
ni un punto por encima de la cota que la desigualdad le regala**. Eso dice algo
fuerte sobre lo poco que aporta la búsqueda con esta formulación a ese tamaño.

Para el informe esto da un cierre fuerte al ítem 2: no solo se identifica el
factor que domina el tiempo de cómputo, sino que se propone una corrección
concreta, se demuestra que es válida (mismo óptimo) y se mide cuánto mejora.

### Factores concretos, en orden de impacto

1. **Big-M débil en la continuidad temporal.** `M = max(d_ij) · n` va de 7202
   (n=10) a 23320 (n=30), cuando los tiempos reales nunca pasan de
   `max r + Tmax ≈ 4500`. Un `M` del orden de 4 a 5 veces lo necesario relaja
   las restricciones mucho más de lo que hace falta.

   **Experimento hecho, con resultado negativo que vale reportar:** se repitió
   con `M = max r + Tmax + max d` (una cota válida y mucho más fina; ver
   `--bigm ajustado`). En n = 10, K = 2 el óptimo y las rutas son idénticos, lo
   que confirma que la cota ajustada es válida. Pero la cota en la raíz sube
   apenas de ~50 a ~54: **ajustar el Big-M por sí solo no arregla la
   relajación.** Conviene reportarlo, porque descarta una explicación fácil y
   deja claro que el problema de fondo es el que ataca la desigualdad válida de
   arriba: no que `M` sea grande, sino que nada impide `T_j < r_j`.

2. **MTZ también da una relajación floja.** La formulación de eliminación de
   subtours por flujo de orden es compacta (evita restricciones exponenciales)
   pero notoriamente débil comparada con cortes de subtour agregados
   dinámicamente.

3. **Crecimiento cuadrático del modelo.** Hay tres familias de variables
   indexadas por arco (`X`, `w`, `L`), así que el número de variables crece como
   `3n²`: de 320 en n = 10 a 2760 en n = 30. Las restricciones van de 402 a
   3602. Es la causa de que la curva de tiempo contra n en escala log se vea
   casi recta.

4. **Efecto de K.** Dos efectos que van en sentidos opuestos, y conviene
   mirarlos por separado en la tabla: con `K = K0` el problema está más
   apretado (en n = 15 y 30 los vehículos deben ir exactamente llenos), lo que
   puede *ayudar* podando el árbol o *estorbar* si encontrar una solución
   factible se vuelve difícil; con `K` mayor hay más libertad, mejor objetivo,
   pero también más **simetría** entre vehículos idénticos, y la simetría es
   veneno para branch-and-bound porque el solver reexplora soluciones que son
   la misma salvo permutación.

5. **Dispersión de los `r_i`.** La mitad de los clientes tiene `r_i = 0` y la
   otra mitad valores hasta 600-670. Esa mezcla es la que crea la tensión
   interesante: agrupar por cercanía geográfica compite con agrupar por
   liberación parecida.

6. **Cambio de solver en n = 25 y 30.** Parte del salto de tiempo y gap entre
   n = 20 y n = 25 se debe a que cambia el solver, no solo el tamaño. Hay que
   decirlo para no atribuirle a la dificultad del problema algo que es del
   solver. Dato concreto: en n = 25 HiGHS no encontró **ninguna** solución
   factible en 25 s de prueba.

### Qué se podría hacer (para las conclusiones)

- Cortes de subtour dinámicos en vez de MTZ.
- Restricciones de ruptura de simetría entre vehículos idénticos.
- Dar al solver una solución inicial factible construida con una heurística
  golosa: en las instancias grandes el problema no fue solo cerrar el gap, sino
  **encontrar la primera solución factible**.

---

## Secciones 5 y 6 — Las dos comparaciones (ítems 3 y 4)

Instancias usadas: las tres de **n = 10** (K = 1, 2, 3), las únicas que
alcanzaron **gap = 0**. El enunciado pide al menos dos.

Tabla lista para pegar: `resultados/tabla_comparaciones_reevaluadas.md`
(la genera `python comparar.py`).
Figuras: `figuras/rutas_n10_K<K>.png`, con los clientes de `r_i > 0` en rojo.

### Nota metodológica importante (vale declararla)

Las tres soluciones se miden con **la misma métrica**: tiempos de liberación
reales y salida de cada ruta fijada en el mayor `r` de sus clientes, que es la
salida óptima para un conjunto de rutas dado.

Esto hace falta porque ni el modelo de distancia ni el base determinan las horas
de salida: el de distancia no las empuja hacia abajo, y el base directamente
ignora los `r_i` y sale en 0. Comparar el valor que reporta cada corrida sería
comparar cosas distintas. Lo que se compara es **la mejor espera alcanzable con
las rutas que produce cada criterio**.

### Los números

| n | K | modelo | espera total | sobrecosto | distancia | duración máx | rutas |
|---|---|---|---|---|---|---|---|
| 10 | 1 | extendido (min espera) | 9862.0 | — | 2129.9 | 2129.9 | 1 |
| 10 | 1 | min distancia | 14086.7 | +42.8% | 1962.9 | 1962.9 | 1 |
| 10 | 1 | base (min makespan) | 14086.7 | +42.8% | 1962.9 | 1962.9 | 1 |
| 10 | 2 | extendido (min espera) | 4653.2 | — | 2434.9 | 1343.0 | 2 |
| 10 | 2 | min distancia | 10225.1 | +119.8% | 1962.9 | 1962.9 | 1 |
| 10 | 2 | base (min makespan) | 7000.5 | +50.4% | 2531.0 | 1326.1 | 2 |
| 10 | 3 | extendido (min espera) | 3704.2 | — | 2533.8 | 1343.0 | 3 |
| 10 | 3 | min distancia | 10225.1 | +176.0% | 1962.9 | 1962.9 | 1 |
| 10 | 3 | base (min makespan) | 5857.3 | +58.1% | 3765.0 | 1313.1 | 3 |

### Ítem 3 — Contra minimizar distancia

**1. El hallazgo estructural más fuerte: minimizar distancia usa UNA sola ruta,
sin importar cuánto valga K.** Con K = 1, 2 o 3 la solución de distancia es
siempre el mismo tour de 1962.9. La razón es inmediata: cada ruta adicional
obliga a una salida y un regreso extra al depósito, y eso solo suma distancia.
La restricción (5) es un techo (`≤ K`), no una igualdad, así que nada fuerza a
usar los vehículos disponibles.

Consecuencia: **el criterio de distancia desaprovecha por completo la flota**.
Y como una sola ruta debe atender a todos los clientes, su salida queda atada
al mayor `r` de todos (600), de modo que los clientes con `r_i = 0` esperan
600 más el viaje. De ahí que el sobrecosto crezca con K: +119.8% con K = 2 y
+176.0% con K = 3, porque el modelo extendido sí aprovecha los vehículos extra
mientras el de distancia se queda en uno.

**2. El intercambio.** Optimizar espera cuesta entre 19% y 23% más distancia
(1962.9 → 2434.9 con K = 2; → 2533.8 con K = 3). A cambio, la espera se reduye
a menos de la mitad.

**3. Con K = 1 cambia el orden de visita, no la partición.** Las dos soluciones
tienen una sola ruta, pero distinta secuencia:

- distancia: `0-4-1-5-8-3-2-9-7-6-0` (el tour más corto)
- espera: `0-4-6-7-9-2-3-1-8-5-0` (deja a los de `r` alto — 1, 8, 5 — al final)

El motivo conviene explicarlo porque es elegante: con una sola ruta la salida
está fija en 600 sin importar el orden, así que minimizar `Σ (T_i − r_i)`
equivale a minimizar `Σ T_i`, es decir **la suma de los tiempos de llegada**.
Eso no es el TSP: es un problema de **latencia mínima** (o "repairman
problem"), que prefiere visitar temprano lo que pueda y no minimizar el
recorrido total. De ahí que acepte 2129.9 de distancia en vez de 1962.9.

### Ítem 4 — Contra el modelo base

**1. El costo de ignorar las liberaciones: entre +42.8% y +58.1% de espera.**
Ese es el argumento central a favor del modelo extendido, y sale de evaluar las
rutas del modelo base con la métrica de espera.

**2. El mecanismo, que es lo que hay que explicar: el modelo extendido agrupa
por tiempo de liberación; el base los mezcla.** Se ve limpísimo en K = 3, con
los `r` de cada ruta al lado:

*Extendido* (espera 3704.2):

| ruta | `r` de sus clientes | salida | duración |
|---|---|---|---|
| `0-6-4-0` | [0, 0] | 0 | 322.0 |
| `0-7-1-8-5-0` | [260, 600, 588, 552] | 600 | 1343.0 |
| `0-9-2-3-0` | [0, 77, 0] | 77 | 868.8 |

*Base* (espera 5857.3):

| ruta | `r` de sus clientes | salida | duración |
|---|---|---|---|
| `0-5-0` | [552] | 552 | 1313.1 |
| `0-6-8-1-0` | [0, 588, 600] | 600 | 1276.3 |
| `0-7-9-2-3-4-0` | [260, 0, 77, 0, 0] | 260 | 1175.6 |

El extendido **aísla** los cuatro clientes de liberación alta (1, 5, 7, 8) en
una sola ruta que sale en 600, y deja que las otras dos salgan en 0 y en 77.
El base mete al cliente 6 (`r = 0`) junto a 8 y 1 (`r = 588` y `600`), lo que
obliga a esa ruta entera a salir en 600: el cliente 6 espera 600 más el viaje
sin ninguna razón. Ese es exactamente el desperdicio que el modelo extendido
elimina.

**3. El base equilibra duraciones; el extendido no.** Es la consecuencia directa
de sus objetivos. En K = 3 el base reparte 1313.1 / 1276.3 / 1175.6 (muy
parejo, porque el makespan lo castiga por la ruta más larga), mientras el
extendido reparte 322.0 / 1343.0 / 868.8 (muy desparejo). El extendido
**quiere** una ruta corta que salga de inmediato con los clientes de `r = 0`.

**4. Lo que cuesta al revés es poco.** El makespan del extendido es apenas 2.3%
peor que el del base (1343.0 contra 1313.1 en K = 3). Es decir: se gana entre
43% y 58% de espera a cambio de casi nada de makespan. Buen material para las
conclusiones.

**5. Comprobación de consistencia:** con K = 1, el modelo base y el de distancia
dan **exactamente la misma solución** (14086.7 de espera, 1962.9 de distancia,
misma secuencia). Es lo esperado: con una sola ruta el makespan es la duración
de esa ruta, que es su distancia, así que minimizar makespan y minimizar
distancia son el mismo problema (el TSP). Que coincidan es una señal de que la
implementación de los tres objetivos es consistente. Vale mencionarlo, y
también que por eso K = 1 es el caso menos informativo de los tres para
comparar estructura entre vehículos.

---

## Sección 7 — Conclusiones y limitaciones

Limitaciones que hay que declarar, por honestidad del reporte:

1. **Límite de tiempo de 300 s** en lugar de los 3600 s del enunciado (repetible
   con un flag).
2. **Dos solvers distintos**: Gurobi para n ≤ 20, HiGHS para n = 25 y 30, por el
   límite de la licencia gratuita. Los gaps y tiempos de esas seis instancias no
   son comparables con el resto.
3. **Tiempos medidos con tres procesos en paralelo**, no en una máquina
   desocupada.
4. Si quedaron instancias sin solución factible dentro del límite, decirlo como
   tal y **no** confundirlo con infactibilidad probada.

---

## Checklist antes de entregar

Los cuatro resultados que pide el enunciado, y dónde está cada uno:

- [ ] **Ítem 1** — tabla de las 15 combinaciones `(n, K)` con factibilidad,
      objetivo, gap, tiempo y rutas → `resultados/tabla_principal.md`, más el
      detalle de rutas en `resultados/*.json` (campo `detalle_rutas`).
- [ ] **Ítem 2** — análisis del tiempo de cómputo → Sección 4 de este
      documento, figura `figuras/tiempos.png`.
- [ ] **Ítem 3** — comparación con minimizar distancia, en ≥ 2 instancias con
      gap = 0 → Sección 5/6, tabla
      `resultados/tabla_comparaciones_reevaluadas.md`, figuras
      `figuras/rutas_n10_K*.png`.
- [ ] **Ítem 4** — comparación con el modelo base, en las mismas instancias →
      Sección 5/6, misma tabla y figuras.

Cosas que **hay que declarar** para que el informe sea honesto:

- [ ] El límite de tiempo realmente usado (300 s en esta corrida, no 3600 s).
- [ ] Que n = 25 y 30 usan HiGHS y no Gurobi, por el límite de la licencia, y
      que sus gaps no son comparables con el resto.
- [ ] Que los tiempos se midieron con 3 procesos en paralelo.
- [ ] Que dos instancias (n = 25 K = 2 y n = 30 K = 2) terminaron **sin
      solución factible**, lo cual **no** es lo mismo que infactibilidad
      probada.
- [ ] Que la corrida principal es **sin** las desigualdades válidas; las que
      las llevan están aparte (etiquetas `*_cortes`) como experimento.
- [ ] La interpretación que se le dio a `Tmax` (ver Sección 1, punto 4).

Si consigues repetir con más tiempo:

```bash
python lote.py --que principal --procesos 3 --tiempo 3600 --hilos 2
python analizar.py
python comparar.py
```

y actualiza la tabla, la figura y los párrafos donde diga 300 s. Si además
consigues la licencia académica de Gurobi, agrega `--solver gurobi` para que
las 15 queden con el mismo solver.

---

## Apéndice sugerido

- Tabla de parámetros por instancia (está en la Sección 3).
- Rutas completas con horas de salida, llegada por cliente y carga: están en
  `resultados/*.json`, campo `detalle_rutas`.
- El código (`datos.py`, `modelo.py`, `validar.py`, `correr.py`).
- Dato de transparencia: el bucle del profesor genera también `r[0]`, el
  tiempo de liberación del depósito. El depósito no es cliente y no tiene
  liberación, así que el modelo lo ignora. En estas instancias resultó ser 0 en
  los cinco tamaños, de modo que no afecta ningún resultado; queda registrado en
  los JSON como `r_deposito_generado`.
