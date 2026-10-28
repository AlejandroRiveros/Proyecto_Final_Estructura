"""Motor del planeador TransMilenio.

Todo lo que resuelve un requisito vive en este paquete.
Prohibido aquí: dict, set, sorted, .sort(), min/max sobre colecciones,
`x in lista`, .index(), .count(), bisect, heapq, collections, functools
y cualquier librería externa. Permitido: list como arreglo, str, for,
y los módulos csv, time y random.
"""

from motor.red import Red
from motor.fila import simular_fila
