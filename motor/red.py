class Red:
    """Red de TransMilenio cargada desde estaciones.csv, rutas.csv y horarios.csv."""

    def __init__(self, carpeta):
        self.carpeta = carpeta

    # R1
    def estado(self, nombre):
        raise NotImplementedError

    # R2
    def autocompletar(self, prefijo, k):
        raise NotImplementedError

    # R3
    def rango(self, desde, hasta):
        raise NotImplementedError

    # R4
    def proximo_bus(self, estacion, ruta, hora):
        raise NotImplementedError

    # R5
    def viaje(self, origen, destino):
        raise NotImplementedError

    # R6
    def ranking(self, k):
        raise NotImplementedError

    # R7
    def agregar_parada(self, ruta, nueva, despues_de):
        raise NotImplementedError

    def quitar_parada(self, ruta, estacion):
        raise NotImplementedError

    def recorrido(self, ruta, al_reves=False):
        raise NotImplementedError

    # R8
    def cerrar(self, nombre):
        raise NotImplementedError

    def reabrir(self, nombre):
        raise NotImplementedError

    # R9
    def deshacer(self):
        raise NotImplementedError

    def rehacer(self):
        raise NotImplementedError
