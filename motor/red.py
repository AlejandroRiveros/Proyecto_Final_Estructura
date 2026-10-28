import csv

from motor.estructuras import TablaHash

# Respuestas de estado(). Si el enunciado pide otro formato, solo se cambian aquí.
ABIERTA = "abierta"
CERRADA = "cerrada"


class Estacion:
    def __init__(self, nombre):
        self.nombre = nombre
        self.abierta = True


class Red:
    """Red de TransMilenio cargada desde estaciones.csv, rutas.csv y horarios.csv."""

    def __init__(self, carpeta):
        self.carpeta = carpeta
        # nombre -> Estacion. Tabla hash porque R1 es la consulta más frecuente.
        self._estaciones = TablaHash()
        self._cargar_estaciones(carpeta + "/estaciones.csv")

    def _cargar_estaciones(self, ruta_archivo):
        with open(ruta_archivo, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                nombre = fila["nombre"].strip()
                if nombre != "":
                    self._estaciones.poner(nombre, Estacion(nombre))

    # R1
    def estado(self, nombre):
        """Devuelve "abierta", "cerrada" o None si la estación no existe. O(1) promedio."""
        estacion = self._estaciones.obtener(nombre)
        if estacion is None:
            return None
        if estacion.abierta:
            return ABIERTA
        return CERRADA

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
