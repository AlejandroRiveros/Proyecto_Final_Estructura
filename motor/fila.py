# R10
from motor.estructuras.cola import Cola
from motor.estructuras.ordenamiento import esta_ordenado, merge_sort


def simular_fila(llegadas, frecuencia, capacidad):
    """Simula la fila de abordaje en hora pico.

    llegadas: lista con el segundo en que llega cada persona (una por elemento;
    pueden venir en cualquier orden).
    frecuencia: segundos entre buses. Los buses salen en frecuencia,
    2*frecuencia, 3*frecuencia, ...
    capacidad: cupo de cada bus.

    Devuelve, en el mismo orden de `llegadas`, el segundo en que salió el bus
    de cada persona. La gente sube en orden de llegada (cola FIFO); quien llega
    en el mismo segundo que otro, en el orden de la lista. Quien llega justo
    cuando sale un bus alcanza a subir a ese bus.
    [] si no hay llegadas; None si frecuencia o capacidad no son positivas.

    Ejemplo del enunciado: simular_fila([30, 5, 5, 70], 60, 2) == [120, 60, 60, 120].

    O(P) si las llegadas ya vienen ordenadas; O(P log P) si hay que ordenarlas
    con merge sort. P = personas. Cada vuelta del ciclo principal sube al menos
    a una persona, así que hay a lo sumo P salidas con abordaje; las salidas
    vacías se saltan con una cuenta, sin recorrerlas.
    """
    if frecuencia <= 0 or capacidad <= 0:
        return None
    p = len(llegadas)
    if p == 0:
        return []
    # orden[j] = posición en `llegadas` de la j-ésima persona en llegar.
    # Se revisa el orden en O(P); solo si hace falta se ordenan los pares
    # (segundo, posición) con merge sort. La posición desempata, así que los
    # que llegan en el mismo segundo quedan en el orden de la lista.
    if esta_ordenado(llegadas):
        orden = list(range(p))
    else:
        pares = []
        for i in range(p):
            pares.append((llegadas[i], i))
        pares = merge_sort(pares)
        orden = []
        for par in pares:
            orden.append(par[1])

    salidas = [0] * p
    cola = Cola()  # guarda la posición en `llegadas` de cada persona en la fila
    siguiente = 0  # índice en `orden` de la primera persona que aún no llega
    bus = 0
    while siguiente < p or not cola.esta_vacia():
        if cola.esta_vacia():
            # Fila vacía: se salta directo al primer bus que alcanza a la siguiente persona.
            bus = _primer_bus_desde(llegadas[orden[siguiente]], frecuencia)
        # Entran a la fila todos los que llegaron hasta la salida del bus (incluida).
        while siguiente < p and llegadas[orden[siguiente]] <= bus:
            cola.encolar(orden[siguiente])
            siguiente += 1
        suben = 0
        while suben < capacidad and not cola.esta_vacia():
            salidas[cola.desencolar()] = bus
            suben += 1
        bus += frecuencia
    return salidas


def _primer_bus_desde(segundo, frecuencia):
    """Primer bus (frecuencia, 2*frecuencia, ...) que sale en ese segundo o después. O(1)."""
    if segundo <= frecuencia:
        return frecuencia
    # División hacia arriba: -(-a // f) * f.
    return -(-segundo // frecuencia) * frecuencia
