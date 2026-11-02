class Nodo:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None

class Cola:
    def __init__(self):
        self.primero = None
        self.ultimo = None
        self._tamanio = 0

    def esta_vacia(self):
        return self.primero is None

    def encolar(self, item):
        nuevo = Nodo(item)
        if self.esta_vacia():
            self.primero = nuevo
            self.ultimo = nuevo
        else:
            self.ultimo.siguiente = nuevo
            self.ultimo = nuevo
        self._tamanio += 1

    def desencolar(self):
        if self.esta_vacia():
            return None
        dato = self.primero.dato
        self.primero = self.primero.siguiente
        if self.primero is None:
            self.ultimo = None
        self._tamanio -= 1
        return dato

    def __len__(self):
        return self._tamanio
