def esta_ordenado(arreglo):
    """True si el arreglo ya está de menor a mayor. O(n): un solo recorrido."""
    for i in range(1, len(arreglo)):
        if arreglo[i - 1] > arreglo[i]:
            return False
    return True


def merge_sort(arreglo):
    """Devuelve una lista nueva ordenada de menor a mayor. O(n log n) siempre.

    Lo usamos en lugar de sorted() y .sort() (prohibidos en el motor).
    """
    n = len(arreglo)
    if n <= 1:
        return arreglo[:]
    mitad = n // 2
    izquierda = merge_sort(arreglo[:mitad])
    derecha = merge_sort(arreglo[mitad:])
    return _mezclar(izquierda, derecha)


def _mezclar(izquierda, derecha):
    salida = []
    i = 0
    j = 0
    while i < len(izquierda) and j < len(derecha):
        # <= mantiene el orden original de los iguales (estable).
        if izquierda[i] <= derecha[j]:
            salida.append(izquierda[i])
            i += 1
        else:
            salida.append(derecha[j])
            j += 1
    while i < len(izquierda):
        salida.append(izquierda[i])
        i += 1
    while j < len(derecha):
        salida.append(derecha[j])
        j += 1
    return salida
