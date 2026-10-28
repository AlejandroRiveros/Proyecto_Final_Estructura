import csv

from motor.estructuras import TablaHash, merge_sort, esta_ordenado, primer_mayor_o_igual

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
        # Nombres de las estaciones ABIERTAS en orden alfabético (R2, R3).
        # Arreglo ordenado + búsqueda binaria: las consultas son O(log n),
        # y solo cerrar/reabrir (poco frecuentes) pagan O(n) por mantenerlo.
        self._abiertas = []
        self._cargar_estaciones(carpeta + "/estaciones.csv")

    def _cargar_estaciones(self, ruta_archivo):
        nombres = []
        with open(ruta_archivo, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                nombre = fila["nombre"].strip()
                if nombre != "" and not self._estaciones.contiene(nombre):
                    self._estaciones.poner(nombre, Estacion(nombre))
                    nombres.append(nombre)
        # No suponemos que el CSV venga ordenado: la red de prueba puede no estarlo.
        # Verificamos en O(n) y solo pagamos el merge sort O(n log n) si hace falta.
        if esta_ordenado(nombres):
            self._abiertas = nombres
        else:
            self._abiertas = merge_sort(nombres)

    # R1
    def estado(self, nombre):
        """Devuelve "abierta", "cerrada" o None si la estación no existe. O(1) promedio."""
        estacion = self._estaciones.obtener(nombre)
        if estacion is None:
            return None
        if estacion.abierta:
            return ABIERTA
        return CERRADA

    # Mantenimiento del arreglo de abiertas (R8).
    # Sacar o meter un nombre cuesta O(n) por el corrimiento de los demás;
    # se acepta porque cerrar y reabrir son mucho menos frecuentes que consultar.
    def _sacar_de_abiertas(self, nombre):
        i = primer_mayor_o_igual(self._abiertas, nombre)
        if i < len(self._abiertas) and self._abiertas[i] == nombre:
            self._abiertas.pop(i)

    def _meter_en_abiertas(self, nombre):
        i = primer_mayor_o_igual(self._abiertas, nombre)
        if i == len(self._abiertas) or self._abiertas[i] != nombre:
            self._abiertas.insert(i, nombre)

    def _cerrar_estacion(self, estacion):
        estacion.abierta = False
        self._sacar_de_abiertas(estacion.nombre)

    def _abrir_estacion(self, estacion):
        estacion.abierta = True
        self._meter_en_abiertas(estacion.nombre)

    # R2
    def autocompletar(self, prefijo, k):
        """Hasta k estaciones abiertas que empiezan por prefijo, en orden alfabético.

        O(log n + k), n = estaciones abiertas: la binaria encuentra la primera
        candidata y desde ahí todas las que comparten prefijo están seguidas.
        """
        salida = []
        if k <= 0:
            return salida
        i = primer_mayor_o_igual(self._abiertas, prefijo)
        while i < len(self._abiertas) and len(salida) < k and self._abiertas[i].startswith(prefijo):
            salida.append(self._abiertas[i])
            i += 1
        return salida

    # R3
    def rango(self, desde, hasta):
        """Estaciones abiertas entre desde y hasta (ambos incluidos), en orden alfabético.

        O(log n + m), n = estaciones abiertas, m = estaciones devueltas.
        """
        salida = []
        i = primer_mayor_o_igual(self._abiertas, desde)
        while i < len(self._abiertas) and self._abiertas[i] <= hasta:
            salida.append(self._abiertas[i])
            i += 1
        return salida

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
        """True si la estación existía y estaba abierta; False si no había nada que cerrar.

        O(n), n = estaciones abiertas (corrimiento en el arreglo ordenado).
        """
        estacion = self._estaciones.obtener(nombre)
        if estacion is None or not estacion.abierta:
            return False
        self._cerrar_estacion(estacion)
        return True

    def reabrir(self, nombre):
        """True si la estación existía y estaba cerrada; False si no había nada que reabrir.

        O(n), n = estaciones abiertas.
        """
        estacion = self._estaciones.obtener(nombre)
        if estacion is None or estacion.abierta:
            return False
        self._abrir_estacion(estacion)
        return True

    # R9
    def deshacer(self):
        raise NotImplementedError

    def rehacer(self):
        raise NotImplementedError
