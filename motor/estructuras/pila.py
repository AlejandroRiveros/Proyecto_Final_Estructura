class Pila:
    """Pila LIFO (sesión 6) sobre un arreglo: el tope es el final de la lista.

    apilar = append y desapilar = pop() del final: los dos O(1),
    porque nunca se corre ningún otro elemento.
    """

    def __init__(self):
        self._datos = []

    def apilar(self, valor):
        self._datos.append(valor)

    def desapilar(self):
        if len(self._datos) == 0:
            return None
        return self._datos.pop()

    def esta_vacia(self):
        return len(self._datos) == 0

    def vaciar(self):
        self._datos = []

    def __len__(self):
        return len(self._datos)
