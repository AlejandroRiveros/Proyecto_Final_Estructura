# Planeador de viajes TransMilenio

Proyecto final de Estructuras de Datos y Algoritmos, Universidad de La Sabana, 2026-2.

## Cómo arrancar

Desde la raíz del repositorio, una sola vez: `pip install -r requirements.txt`. Después:

```
python -m streamlit run app/app.py
```

Se usa `python -m` porque así la raíz del repositorio queda en el path y la app encuentra `motor/`
(con `streamlit run app/app.py` a secas, Python solo ve la carpeta `app/`).

El panel de rendimiento (R11) también se puede abrir solo: `python -m streamlit run app/panel_r11.py`.

## Estructura

- `motor/`: paquete Python con toda la lógica (`from motor import Red, simular_fila`).
- `conversion/`: script del GTFS a los tres CSV (`convertir.py`) y los CSV que genera (`conversion/generados/`). También genera `coordenadas.csv` (latitud y longitud de cada estación, promedio de sus vagones en el GTFS), que solo lee la app para dibujar el mapa del viaje; el motor no lo usa.
- `datos/`: CSV entregados por el profesor. Son los que usan la app y las pruebas.
- `datos/`: `estaciones.csv`, `rutas.csv`, `horarios.csv`.
- `app/`: front y panel de rendimiento (R11).
- `pruebas/`: pruebas propias del motor.

## Revisión de prohibidos

`pruebas/test_prohibidos.py` recorre el AST de cada archivo de `motor/` y falla si encuentra diccionarios o conjuntos (literales, por comprensión o con `dict()`/`set()`), `sorted`, `min`, `max`, `.sort()`, `.index()`, `.count()`, `.insert()`, `.pop(i)`, el operador `in` fuera de un `for`, `csv.DictReader` o imports distintos de `csv`, `time` y `random`. Al mirar la estructura del programa no confunde llaves dentro de comentarios o cadenas.

## Decisiones (R12)

Para cada requisito: estructura, algoritmo, alternativa descartada y por qué, y la O grande de cada operación diciendo qué es n.

| Req | Estructura | Algoritmo | Alternativa descartada | O grande (n = ...) |
|---|---|---|---|---|
| R1 | Tabla hash propia con encadenamiento (`motor/estructuras/tabla_hash.py`), nombre → estación | Hash polinomial base 31; se duplica la tabla al pasar factor de carga 0.75 | Arreglo ordenado + búsqueda binaria: O(log n), y R1 es la consulta más frecuente | `estado`: O(1) promedio, O(n) peor caso; n = número de estaciones |
| R2 | Arreglo ordenado con los nombres de las estaciones abiertas (`_abiertas`) | Búsqueda binaria del primer nombre ≥ prefijo; desde ahí se avanza mientras empiece por el prefijo y falten resultados | BST: los nombres llegan ordenados en el CSV y el árbol se degenera en lista (h = n). Tabla hash: no guarda orden | `autocompletar`: O(log n + k); n = estaciones abiertas, k = máximo pedido |
| R3 | El mismo arreglo ordenado de R2 | Búsqueda binaria de `desde` y recorrido hasta pasar `hasta` (ambos incluidos) | Recorrer todas las estaciones filtrando: O(n) por consulta | `rango`: O(log n + m); n = estaciones abiertas, m = estaciones devueltas |
| R4 | Tabla hash ruta → (tabla hash estación → arreglo ordenado y sin repetidos de horas "HH:MM") | Al cargar: verificar orden en O(h), merge sort solo si hace falta, y quitar repetidas en un recorrido. Al consultar: si la estación está cerrada o la parada ya no está en la ruta, `None` (dos revisiones O(1) en tablas hash; los horarios no se borran, así que reabrir y deshacer funcionan solos); si no, búsqueda binaria de la primera hora ≥ la pedida. `None` también si no hay más buses ese día | Recorrer la lista sin ordenar en cada consulta: O(h), y la pista dice que las troncales pasan cientos de veces al día. Arreglo de 1.440 minutos por par: O(1), pero mucha memoria | `proximo_bus`: O(log h); h = horas de esa ruta en esa estación. Carga: O(H log h), H = total de horas |
| R5 | Índice inverso estación → rutas (tabla hash, mantenido por las mismas funciones internas que usa R9) + tabla hash de mejores llegadas desde el origen + lista doble de cada ruta | Encuentro en el medio: (1) desde el origen, hacia adelante por cada ruta, se guarda la mejor llegada a cada estación abierta (menos paradas; empate por nombre de ruta). (2) Desde el destino, hacia atrás con los punteros `anterior`, cada estación abierta ya alcanzada es un transbordo posible. El directo es solo un candidato. En empate gana el directo y luego el orden de nombres. Las cerradas no sirven para subir, bajar ni cambiar, pero no cortan la ruta. Si las dos rutas coinciden, es un directo. Devuelve una lista de tramos `(ruta, sube_en, baja_en)`: uno si es directo, dos si hay transbordo (la bajada del primero es la subida del segundo); `None` si no hay viaje. El total de paradas lo calcula el motor (`_buscar_viaje`) y no se deja a la app | Probar todas las combinaciones (ruta, estación, ruta, estación): O(R × L × R × L). BFS sobre la red (sesión 10): la red ya es un grafo implícito (estación → sus rutas → parada `siguiente`) y este algoritmo es, en el fondo, un recorrido de dos niveles sobre él; un BFS general recorre toda la red, O(V × r × L), y no limita los transbordos. Dijkstra (sesión 11): para resolver este mismo problema tendría que llevar en el estado la ruta y cuántos transbordos van (estación, ruta, transbordos ≤ 1), con peso 1 por parada y 0 por cambio; explora toda la red, O((V + E) log V), y necesita un heap propio (`heapq` está prohibido). Sin ese límite resuelve otro problema, que la app muestra aparte como alternativa con menos paradas (ver «Búsqueda con más transbordos»). Como R5 limita el viaje a un transbordo, basta con mirar las rutas del origen y del destino | `viaje`: O(R × L) con R = rutas por estación y L = paradas por ruta (máximos); accesos hash O(1) promedio. No se mide en rendimiento |
| R6 | Arreglo de estaciones abiertas ordenado por buses al día (más primero; empate alfabético). Cada estación guarda su posición en el arreglo y su total de buses. Conteo por ruta y estación en tabla hash | Al cargar: sumar buses de cada parada y merge sort, O(n log n). `ranking(k)`: los primeros k. Al cambiar los buses de una estación: intercambios con la vecina hasta su lugar. Cerrar/reabrir: sacar/meter con corrimiento y binaria | Reordenar todo con merge sort en cada cambio: O(n log n) por cambio. Calcular el ranking en cada consulta: O(n log n) por consulta, y la pista dice que se consulta muy seguido. Reconstruir en la primera consulta tras un cambio: esa consulta dejaría de ser O(k) | `ranking`: O(k). Mantenimiento: O(d + 1) al editar rutas (d = posiciones que salta la estación), O(n) al cerrar/reabrir; n = estaciones abiertas |
| R7 | Por ruta: lista doblemente enlazada con las paradas + tabla hash estación → nodo (`motor/estructuras/lista_doble.py`) | La tabla hash da el nodo en O(1); agregar y quitar solo reconectan punteros anterior/siguiente. El recorrido de ida sale de la cabeza y el de vuelta de la cola. Devuelven `True`/`False` como R8 (`False` también si `nueva` no es una estación de la red); `recorrido` da `[]` si la ruta no existe | Arreglo por ruta: buscar y correr elementos, O(L). Lista simple: quitar necesita el nodo anterior, O(L), y la vuelta hay que voltearla | `agregar_parada`/`quitar_parada`: O(1) promedio en la ruta + O(d + 1) por mantener el ranking de R6 (ver compromiso R6/R7); `recorrido`: O(L); L = paradas de la ruta |
| R8 | Bandera `abierta` en la estación (tabla hash) + sacar o reinsertar el nombre en el arreglo ordenado de abiertas | Búsqueda binaria de la posición y corrimiento a mano del arreglo (un ciclo mueve cada elemento una casilla; no se usan `list.insert` ni `list.pop(i)`). Devuelve `True` si cambió algo y `False` si la estación no existe o ya estaba en ese estado | Solo marcar y saltar las cerradas al consultar: cerrar en O(1), pero autocompletar puede caer a O(n) con muchas cerradas. AVL: O(log n) en todo, pero no se vio en clase | `cerrar`/`reabrir`: O(n); n = estaciones abiertas (corrimiento en `_abiertas` y en el ranking de R6). En R5 la bandera se revisa en O(1): una cerrada no sirve para subir, bajar ni transbordar, pero no corta la ruta |
| R9 | Dos pilas propias (`motor/estructuras/pila.py`): deshacer y rehacer. Cada cambio guarda una tupla que lo describe; al quitar una parada se guarda también la parada anterior (o `None` si era la primera) | `deshacer` saca el tope, aplica el cambio contrario (cerrar ↔ reabrir, agregar ↔ quitar) y lo pasa a rehacer; `rehacer` hace lo inverso. Un cambio nuevo vacía rehacer. Los cambios sin efecto (`False`) no se registran | Copiar la red completa en cada cambio: O(n) en tiempo y memoria por cambio. Una sola lista con índice: recortarla al hacer un cambio nuevo es más propenso a errores | `deshacer`/`rehacer`: O(1) por la pila + el costo del cambio contrario: O(1) en la ruta + O(d + 1) en el ranking al restaurar una edición de ruta, O(n) al restaurar cerrar/reabrir; n = estaciones abiertas |
| R10 | Cola FIFO propia (`motor/estructuras/cola.py`, lista enlazada con primero y último). `llegadas` es la lista de minutos en que llega cada pasajero (uno por elemento); se devuelve la espera de cada uno en orden cronológico de llegada (`[]` sin llegadas, `None` si frecuencia o capacidad no son positivas). Como pidió el profesor (2026-11-11), en la app las llegadas se dan a ritmo fijo, como pasajeros por minuto (en hora pico llegan muchos por minuto), y una cantidad de pasajeros. El tipo de bus fija la capacidad según el sitio oficial de TransMilenio: articulado 160 y biarticulado 260; en "Personalizado" se escriben los cupos libres por bus (mínimo 1), porque el bus puede llegar con gente. El botón "Caso real: Calle 100" llena 64 pasajeros por minuto (3.862 validaciones entre las 17:00 y las 18:00 del 14 de julio de 2021), 3.862 pasajeros y un bus cada 3 minutos (la mediana de la F14-1 en Calle 100 a esa hora, en `horarios.csv`); las validaciones cuentan entradas a la estación, no pasajeros de una ruta. Con 100 por minuto la app arma 100 veces 0, 100 veces 1, … y se lo pasa al motor, que así recibe la lista ya ordenada (O(P)). Provisional hasta tener el enunciado: primer bus en el minuto 0 y formato del retorno | Se revisa el orden en O(P) y solo si hace falta se ordena una copia con merge sort (estable: los empates quedan en el orden de la lista). Los buses salen en 0, f, 2f…; en cada salida entran a la cola los que llegaron hasta ese minuto (incluido) y suben hasta `capacidad` en orden de llegada. Si la cola queda vacía, se salta con una cuenta a la primera salida que alcanza al siguiente pasajero, sin recorrer salidas vacías | Recorrer minuto a minuto o salida por salida: depende de la duración de la simulación y no solo de P. Un índice que avanza por la lista también sirve (suben en orden de llegada), pero la cola modela la fila tal cual. Lista de Python con `pop(0)`: O(P) por cada salida de la fila | O(P) con llegadas ordenadas; O(P log P) si hay que ordenarlas; memoria O(P). P = pasajeros. Cada salida con abordaje sube al menos a uno, así que hay a lo sumo P salidas |

### Búsqueda con más transbordos (apoyo de la app, no es parte del contrato)

Cuando R5 no encuentra viaje, la app ofrece «Buscar con más transbordos» (`Red.viaje_con_transbordos`). Las búsquedas de apoyo devuelven (tramos, paradas), y `Red.viaje_y_paradas` da lo mismo para R5 sin cambiar la firma de `viaje`: el total de paradas lo cuenta el motor durante la búsqueda y la app no recorre las rutas. Con los CSV del profesor y todas las estaciones abiertas, de los 21.462 pares de estaciones distintas R5 resuelve 20.944; los 518 restantes se resuelven todos con 3 tramos.

- Criterio: primero el viaje con menos tramos y, entre los que tienen los mismos tramos, el de menos paradas. Mismas reglas de R5 para las estaciones cerradas.
- Algoritmo: BFS por niveles (sesión 10) con la Cola FIFO del proyecto. Cada salto es un tramo completo, desde donde se sube hasta una parada abierta posterior de la misma ruta, así que el nivel de una estación es el número de tramos. Cada estación guarda (tramos, paradas, ruta, dónde se subió) en una tabla hash para reconstruir el viaje. Una estación entra a la cola una sola vez; mientras se procesa el nivel anterior se le puede mejorar el número de paradas, y al encontrar el destino se termina ese nivel antes de parar.
- Descartado: un BFS con aristas "seguir en el bus" (1 parada) y "cambiar de ruta" (0) no minimiza nada bien, porque las aristas no valen lo mismo. Minimizar solo paradas puede dar viajes con muchos transbordos para ahorrar pocas paradas, por eso esa opción se muestra aparte, como alternativa. Minimizar tiempo no se puede: `horarios.csv` no dice qué horas son del mismo bus.
- O(V × r × L): V = estaciones, r = rutas por estación, L = paradas por ruta. No se mide en rendimiento.
- Alternativa con menos paradas (`Red.viaje_menos_paradas`): Dijkstra (sesión 11) sobre el mismo grafo, con costo (paradas, tramos) comparado como tupla: menos paradas y, en empate, menos tramos. Usa un montículo binario de mínimos propio (`motor/estructuras/monticulo.py`, meter y sacar O(log n)) porque `heapq` está prohibido; las entradas viejas se dejan y se ignoran al salir. O(E log E), E = V × r × L. La app la muestra junto al viaje de R5 o de BFS solo cuando ahorra paradas, con cuántas paradas ahorra y cuántos transbordos agrega. En la red del profesor pasa en 11.397 de los 21.462 pares: ahorra 3,3 paradas en promedio (máximo 27) a cambio de 1 a 4 transbordos más. Se habla de paradas y no de tiempo porque `horarios.csv` no permite saber cuánto tarda un bus entre dos estaciones.

### Compromiso entre R6 y R7

R6 se consulta muy seguido y R7 se edita todo el tiempo. Para que `ranking(k)` sea O(k), el ranking se mantiene ordenado, y cada edición de ruta que cambia los buses de una estación la mueve a su lugar. Editar los enlaces de la ruta sigue siendo O(1), y como cada estación guarda su posición, no hay que buscarla. Moverla cuesta O(d + 1), donde d es cuántas posiciones salta, y en el peor caso eso es O(n).

Reglas fijadas:
- **Qué cuenta como bus:** cada fila de `horarios.csv` para ese par ruta-estación, con repetidas. Las horas sin repetir solo se usan en R4.
- **Qué mide el ranking:** oferta, es decir, cuántos buses programados pasan por la estación en un día hábil según el GTFS de julio de 2021. No mide demanda (cuántos pasajeros entran), que saldría de las validaciones y no está en los CSV.
- **Parada agregada sin horarios para esa ruta:** suma 0 buses. Si vuelve una parada que sí tenía horarios, por ejemplo al deshacer, recupera su conteo.
- **Empates:** más buses primero y, a igual número, orden alfabético.
- **Deshacer y rehacer:** usan las mismas funciones internas de mantenimiento, así que el ranking se actualiza solo.

Medición (redes sintéticas, duplicando n):

| n | `ranking(10)` | editar, d pequeño | editar, extremo a extremo |
|---|---|---|---|
| 10.000 | 0,92 µs | 2,8 µs | 1.881 µs |
| 20.000 | 0,69 µs | 2,7 µs | 3.938 µs |
| 40.000 | 0,68 µs | 2,7 µs | 7.829 µs |
| 80.000 | 0,69 µs | 2,9 µs | 15.394 µs |

La consulta no crece. Una edición que mueve poco no crece. Una edición que lleva una estación de un extremo al otro crece lineal, como se esperaba. Documentarlo no elimina una posible penalización: el criterio del profesor decide si ese costo es aceptable.

Respuesta del profesor (2026-11-11): lo que se nos pide es que el ranking quede actualizado después de cada edición de R7, y así lo hace el motor.

Alternativa considerada (sesión 11): un heap propio de máximos con la posición de cada estación guardada. Cambiar los buses de una estación costaría O(log n) en vez de O(d + 1), pero `ranking(k)` tendría que sacar y volver a meter k elementos, O(k log n) en vez de O(k). Como el ranking se consulta muy seguido y cambia poco, se queda el arreglo ordenado.

### Construcción del arreglo ordenado

Al cargar no se supone que el CSV venga ordenado, porque la red de prueba es distinta. Primero se verifica el orden con un recorrido, O(n) (`esta_ordenado`), y solo si hay algo fuera de orden se ordena con un merge sort propio, O(n log n) (`motor/estructuras/ordenamiento.py`). Con datos ordenados la carga cuesta O(n). Con datos desordenados sigue siendo correcta. Cerrar y reabrir (R8) sacan y meten nombres en el arreglo, O(n) por el corrimiento. Se acepta ese costo porque cerrar y reabrir son mucho menos frecuentes que buscar.

### Horas

Las horas van en formato HH:MM con dos dígitos, así que se comparan bien como texto ("07:05" < "13:40") sin convertirlas.

**Horas del GTFS como 25:10 (diapositiva 8).** El conversor conserva las horas extendidas del GTFS: 25:10:00 se guarda como 25:10 y representa la 01:10 del día calendario siguiente, dentro del mismo día de servicio (así lo define la especificación GTFS). Se eligió esto frente a otras dos opciones:

- Restar 24 (25:10 → 01:10): el bus quedaría antes de las 23:59 del mismo día de servicio, y `proximo_bus` a las 23:50 ya no lo encontraría.
- Descartar esas filas: se perderían buses y cambiaría el ranking de R6.

Conservarlas mantiene el orden correcto como texto ("23:59" < "25:10"), así que R4 consultado a las 23:50 devuelve ese bus, y el bus sigue contando en R6. Lo que no cubre: una consulta a las 00:30 (por ejemplo, desde la app) no encuentra el bus de las 25:10, porque esa hora pertenece al día de servicio anterior. La app muestra una hora extendida como "25:10 (01:10 del día siguiente)". El GTFS del 14 de julio de 2021 no trae ninguna hora después de 23:59, así que hoy la regla no cambia los CSV; queda para cualquier otro GTFS. Si el enunciado detallado fija un máximo de 23:59, hay que ajustar esta decisión.
