class TablaHash:
    """Tabla hash con encadenamiento: cada cubeta es una lista de pares [clave, valor].

    La usamos en lugar de dict (prohibido en el motor).
    Buscar, insertar y borrar cuestan O(1) en promedio, porque la tabla
    se duplica cuando el factor de carga pasa de 0.75 y así las cubetas
    se mantienen cortas.
    """

    CAPACIDAD_INICIAL = 16
    FACTOR_MAXIMO = 0.75

    def __init__(self, capacidad=CAPACIDAD_INICIAL):
        self._cubetas = [[] for _ in range(capacidad)]
        self._tamano = 0

    def _indice(self, clave, capacidad):
        # Hash polinomial de la cadena (base 31), como el de Java.
        h = 0
        for c in clave:
            h = (h * 31 + ord(c)) & 0xFFFFFFFF
        return h % capacidad

    def _redimensionar(self):
        nueva_capacidad = len(self._cubetas) * 2
        nuevas = [[] for _ in range(nueva_capacidad)]
        for cubeta in self._cubetas:
            for par in cubeta:
                nuevas[self._indice(par[0], nueva_capacidad)].append(par)
        self._cubetas = nuevas

    def poner(self, clave, valor):
        cubeta = self._cubetas[self._indice(clave, len(self._cubetas))]
        for par in cubeta:
            if par[0] == clave:
                par[1] = valor
                return
        cubeta.append([clave, valor])
        self._tamano += 1
        if self._tamano > len(self._cubetas) * self.FACTOR_MAXIMO:
            self._redimensionar()

    def obtener(self, clave, defecto=None):
        cubeta = self._cubetas[self._indice(clave, len(self._cubetas))]
        for par in cubeta:
            if par[0] == clave:
                return par[1]
        return defecto

    def contiene(self, clave):
        cubeta = self._cubetas[self._indice(clave, len(self._cubetas))]
        for par in cubeta:
            if par[0] == clave:
                return True
        return False

    def eliminar(self, clave):
        cubeta = self._cubetas[self._indice(clave, len(self._cubetas))]
        for i in range(len(cubeta)):
            if cubeta[i][0] == clave:
                cubeta[i] = cubeta[len(cubeta) - 1]
                cubeta.pop()
                self._tamano -= 1
                return True
        return False

    def claves(self):
        salida = []
        for cubeta in self._cubetas:
            for par in cubeta:
                salida.append(par[0])
        return salida

    def __len__(self):
        return self._tamano
