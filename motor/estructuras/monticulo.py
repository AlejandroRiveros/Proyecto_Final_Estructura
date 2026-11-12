class MonticuloMin:
    """Cola de prioridad (sesión 11) con un montículo binario de mínimos sobre
    un arreglo: el hijo izquierdo de i está en 2i + 1 y el derecho en 2i + 2.
    La raíz (posición 0) siempre tiene la menor prioridad.

    Hace falta uno propio porque heapq está prohibido dentro de motor/.
    Las prioridades se comparan con <, así que pueden ser números o tuplas.
    meter y sacar_minimo: O(log n); n = elementos en el montículo.
    """

    def __init__(self):
        self._datos = []  # pares (prioridad, valor)

    def meter(self, prioridad, valor):
        """Agrega al final y lo sube mientras sea menor que su padre. O(log n)."""
        self._datos.append((prioridad, valor))
        i = len(self._datos) - 1
        while i > 0:
            padre = (i - 1) // 2
            if self._datos[i][0] < self._datos[padre][0]:
                self._intercambiar(i, padre)
                i = padre
            else:
                break

    def sacar_minimo(self):
        """Saca la raíz: el último pasa a la raíz y baja hasta su lugar. O(log n).
        Devuelve (prioridad, valor), o None si está vacío."""
        n = len(self._datos)
        if n == 0:
            return None
        minimo = self._datos[0]
        ultimo = self._datos.pop()  # pop() del final: O(1)
        if n > 1:
            self._datos[0] = ultimo
            self._bajar(0)
        return minimo

    def _bajar(self, i):
        n = len(self._datos)
        while True:
            menor = i
            izq = 2 * i + 1
            der = 2 * i + 2
            if izq < n and self._datos[izq][0] < self._datos[menor][0]:
                menor = izq
            if der < n and self._datos[der][0] < self._datos[menor][0]:
                menor = der
            if menor == i:
                return
            self._intercambiar(i, menor)
            i = menor

    def _intercambiar(self, i, j):
        aux = self._datos[i]
        self._datos[i] = self._datos[j]
        self._datos[j] = aux

    def esta_vacio(self):
        return len(self._datos) == 0

    def __len__(self):
        return len(self._datos)
