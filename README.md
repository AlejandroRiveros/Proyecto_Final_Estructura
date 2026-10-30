# Planeador de viajes TransMilenio

Proyecto final de Estructuras de Datos y Algoritmos, Universidad de La Sabana, 2026-2.

## Cómo arrancar

_Pendiente: comando único para arrancar la app._

## Estructura

- `motor/`: paquete Python con toda la lógica (`from motor import Red, simular_fila`).
- `conversion/`: script del GTFS a los tres CSV.
- `datos/`: `estaciones.csv`, `rutas.csv`, `horarios.csv`.
- `app/`: front y panel de rendimiento (R11).
- `pruebas/`: pruebas propias del motor.

## Decisiones (R12)

Para cada requisito: estructura, algoritmo, alternativa descartada y por qué, y la O grande de cada operación diciendo qué es n.

| Req | Estructura | Algoritmo | Alternativa descartada | O grande (n = ...) |
|---|---|---|---|---|
| R1 | Tabla hash propia con encadenamiento (`motor/estructuras/tabla_hash.py`), nombre → estación | Hash polinomial base 31; se duplica la tabla al pasar factor de carga 0.75 | Arreglo ordenado + búsqueda binaria: O(log n), y R1 es la consulta más frecuente | `estado`: O(1) promedio, O(n) peor caso; n = número de estaciones |
| R2 | Arreglo ordenado con los nombres de las estaciones abiertas (`_abiertas`) | Búsqueda binaria del primer nombre ≥ prefijo; desde ahí se avanza mientras empiece por el prefijo y falten resultados | BST: los nombres llegan ordenados en el CSV y el árbol se degenera en lista (h = n). Tabla hash: no guarda orden | `autocompletar`: O(log n + k); n = estaciones abiertas, k = máximo pedido |
| R3 | El mismo arreglo ordenado de R2 | Búsqueda binaria de `desde` y recorrido hasta pasar `hasta` (ambos incluidos) | Recorrer todas las estaciones filtrando: O(n) por consulta | `rango`: O(log n + m); n = estaciones abiertas, m = estaciones devueltas |
| R4 | Tabla hash ruta → (tabla hash estación → arreglo ordenado y sin repetidos de horas "HH:MM") | Al cargar: verificar orden en O(h), merge sort solo si hace falta, y quitar repetidas en un recorrido. Al consultar: búsqueda binaria de la primera hora ≥ la pedida | Recorrer la lista sin ordenar en cada consulta: O(h), y la pista dice que las troncales pasan cientos de veces al día. Arreglo de 1.440 minutos por par: O(1), pero mucha memoria | `proximo_bus`: O(log h); h = horas de esa ruta en esa estación. Carga: O(H log h), H = total de horas |
| R5 | | | | |
| R6 | | | | |
| R7 | Por ruta: lista doblemente enlazada con las paradas + tabla hash estación → nodo (`motor/estructuras/lista_doble.py`) | La tabla hash da el nodo en O(1); agregar y quitar solo reconectan punteros anterior/siguiente. El recorrido de ida sale de la cabeza y el de vuelta de la cola. Devuelven `True`/`False` como R8 (`False` también si `nueva` no es una estación de la red); `recorrido` da `[]` si la ruta no existe | Arreglo por ruta: buscar y correr elementos, O(L). Lista simple: quitar necesita el nodo anterior, O(L), y la vuelta hay que voltearla | `agregar_parada`/`quitar_parada`: O(1) promedio; `recorrido`: O(L); L = paradas de la ruta |
| R8 | Bandera `abierta` en la estación (tabla hash) + sacar o reinsertar el nombre en el arreglo ordenado de abiertas | Búsqueda binaria de la posición y corrimiento a mano del arreglo (un ciclo mueve cada elemento una casilla; no se usan `list.insert` ni `list.pop(i)`). Devuelve `True` si cambió algo y `False` si la estación no existe o ya estaba en ese estado | Solo marcar y saltar las cerradas al consultar: cerrar en O(1), pero autocompletar puede caer a O(n) con muchas cerradas. AVL: O(log n) en todo, pero no se vio en clase | `cerrar`/`reabrir`: O(n); n = estaciones abiertas. Pendiente: efecto en ranking (R6) y viajes (R5) |
| R9 | Dos pilas propias (`motor/estructuras/pila.py`): deshacer y rehacer. Cada cambio guarda una tupla que lo describe; al quitar una parada se guarda también la parada anterior (o `None` si era la primera) | `deshacer` saca el tope, aplica el cambio contrario (cerrar ↔ reabrir, agregar ↔ quitar) y lo pasa a rehacer; `rehacer` hace lo inverso. Un cambio nuevo vacía rehacer. Los cambios sin efecto (`False`) no se registran | Copiar la red completa en cada cambio: O(n) en tiempo y memoria por cambio. Una sola lista con índice: recortarla al hacer un cambio nuevo es más propenso a errores | `deshacer`/`rehacer`: O(1) por la pila + el costo del cambio contrario: O(1) en rutas, O(n) en cerrar/reabrir; n = estaciones abiertas |
| R10 | | | | |

### Construcción del arreglo ordenado

Al cargar no se supone que el CSV venga ordenado, porque la red de prueba es distinta. Primero se verifica el orden con un recorrido, O(n) (`esta_ordenado`), y solo si hay algo fuera de orden se ordena con un merge sort propio, O(n log n) (`motor/estructuras/ordenamiento.py`). Con datos ordenados la carga cuesta O(n). Con datos desordenados sigue siendo correcta. Cerrar y reabrir (R8) sacan y meten nombres en el arreglo, O(n) por el corrimiento. Se acepta ese costo porque cerrar y reabrir son mucho menos frecuentes que buscar.

### Horas

Los CSV del profesor traen horas entre 00:01 y 23:59 en formato HH:MM con dos dígitos, así que se comparan bien como texto ("07:05" < "13:40") sin convertirlas. El profesor entregó los CSV ya convertidos, por eso no hubo que decidir qué hacer con horas del GTFS como 25:10.
