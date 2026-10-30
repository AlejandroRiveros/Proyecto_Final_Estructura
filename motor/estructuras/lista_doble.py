class NodoDoble:
    def __init__(self, valor):
        self.valor = valor
        self.anterior = None
        self.siguiente = None


class ListaDoble:
    """Lista doblemente enlazada (sesión 4): cada nodo conoce al anterior y al siguiente.

    Insertar después de un nodo conocido y quitar un nodo conocido cuestan O(1):
    solo se reconectan punteros, sin recorrer ni correr elementos.
    Recorrer en cualquiera de los dos sentidos cuesta O(L), L = número de nodos.
    """

    def __init__(self):
        self.cabeza = None
        self.cola = None
        self._tamano = 0

    def agregar_al_final(self, valor):
        nodo = NodoDoble(valor)
        if self.cola is None:
            self.cabeza = nodo
            self.cola = nodo
        else:
            nodo.anterior = self.cola
            self.cola.siguiente = nodo
            self.cola = nodo
        self._tamano += 1
        return nodo

    def agregar_al_inicio(self, valor):
        nodo = NodoDoble(valor)
        if self.cabeza is None:
            self.cabeza = nodo
            self.cola = nodo
        else:
            nodo.siguiente = self.cabeza
            self.cabeza.anterior = nodo
            self.cabeza = nodo
        self._tamano += 1
        return nodo

    def insertar_despues(self, nodo, valor):
        nuevo = NodoDoble(valor)
        nuevo.anterior = nodo
        nuevo.siguiente = nodo.siguiente
        if nodo.siguiente is None:
            self.cola = nuevo
        else:
            nodo.siguiente.anterior = nuevo
        nodo.siguiente = nuevo
        self._tamano += 1
        return nuevo

    def quitar(self, nodo):
        if nodo.anterior is None:
            self.cabeza = nodo.siguiente
        else:
            nodo.anterior.siguiente = nodo.siguiente
        if nodo.siguiente is None:
            self.cola = nodo.anterior
        else:
            nodo.siguiente.anterior = nodo.anterior
        nodo.anterior = None
        nodo.siguiente = None
        self._tamano -= 1

    def a_lista(self, al_reves=False):
        salida = []
        if al_reves:
            nodo = self.cola
            while nodo is not None:
                salida.append(nodo.valor)
                nodo = nodo.anterior
        else:
            nodo = self.cabeza
            while nodo is not None:
                salida.append(nodo.valor)
                nodo = nodo.siguiente
        return salida

    def __len__(self):
        return self._tamano
