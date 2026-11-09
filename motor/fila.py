# R10
from motor.estructuras.cola import Cola
from motor.estructuras.ordenamiento import esta_ordenado, merge_sort


def simular_fila(llegadas, frecuencia, capacidad):
    """Simula la fila de abordaje en hora pico.

    llegadas: lista con el minuto en que llega cada pasajero (una persona por
    elemento; [0, 1, 1, 4] son dos pasajeros en el minuto 1).
    frecuencia: minutos entre buses. El primer bus sale en el minuto 0 y luego
    uno cada `frecuencia` minutos (provisional hasta tener el enunciado).
    capacidad: cupos de cada bus.

    Devuelve la espera en minutos de cada pasajero, en orden cronológico de
    llegada (los que llegan en el mismo minuto, en el orden de la lista).
    [] si no hay llegadas; None si frecuencia o capacidad no son positivas.

    Quien llega justo cuando sale un bus alcanza a subir a ese bus. Los que no
    caben esperan el siguiente, en orden de llegada (cola FIFO).

    O(P) si las llegadas ya vienen ordenadas; O(P log P) si hay que ordenar una
    copia con merge sort. P = pasajeros. Cada vuelta del ciclo principal sube al
    menos a un pasajero, así que hay a lo sumo P salidas con abordaje; las
    salidas vacías se saltan con una cuenta, sin recorrerlas.
    """
    if frecuencia <= 0 or capacidad <= 0:
        return None
    p = len(llegadas)
    if p == 0:
        return []
    # Se verifica el orden en O(P); solo si hace falta se ordena una copia
    # (merge sort es estable: los empates quedan en el orden de la lista).
    if esta_ordenado(llegadas):
        orden = llegadas
    else:
        orden = merge_sort(llegadas)

    esperas = [0] * p
    cola = Cola()  # guarda la posición de cada pasajero en `orden`
    siguiente = 0  # primer pasajero que todavía no ha llegado a la fila
    salida = 0
    while siguiente < p or not cola.esta_vacia():
        if cola.esta_vacia():
            salida = _primera_salida_desde(orden[siguiente], frecuencia)
        # Entran a la fila todos los que llegaron hasta la salida (incluida).
        while siguiente < p and orden[siguiente] <= salida:
            cola.encolar(siguiente)
            siguiente += 1
        suben = 0
        while suben < capacidad and not cola.esta_vacia():
            j = cola.desencolar()
            esperas[j] = salida - orden[j]
            suben += 1
        salida += frecuencia
    return esperas


def _primera_salida_desde(minuto, frecuencia):
    """Primera salida (0, f, 2f, ...) en el minuto dado o después. O(1)."""
    if minuto <= 0:
        return 0
    # División hacia arriba: -(-a // f) * f.
    return -(-minuto // frecuencia) * frecuencia
