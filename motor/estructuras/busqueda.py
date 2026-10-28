def primer_mayor_o_igual(arreglo, valor):
    """Búsqueda binaria sobre un arreglo ordenado. O(log n).

    Devuelve la posición del primer elemento >= valor, o len(arreglo)
    si todos son menores. Si valor está, es su posición; si no, es
    donde habría que insertarlo para no romper el orden.
    """
    bajo = 0
    alto = len(arreglo)
    while bajo < alto:
        medio = (bajo + alto) // 2
        if arreglo[medio] < valor:
            bajo = medio + 1
        else:
            alto = medio
    return bajo
