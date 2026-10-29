import csv

from motor.estructuras import ListaDoble, TablaHash, merge_sort, esta_ordenado, primer_mayor_o_igual

# Respuestas de estado(). Si el enunciado pide otro formato, solo se cambian aquí.
ABIERTA = "abierta"
CERRADA = "cerrada"


class Estacion:
    def __init__(self, nombre):
        self.nombre = nombre
        self.abierta = True


class Ruta:
    """Paradas de una ruta en orden de recorrido (R7).

    paradas: lista doblemente enlazada con los nombres de las estaciones.
    nodos: tabla hash estación -> su nodo en la lista, para llegar a una
    parada en O(1) sin recorrer la ruta.
    """

    def __init__(self, nombre):
        self.nombre = nombre
        self.paradas = ListaDoble()
        self.nodos = TablaHash()


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
        # nombre de ruta -> Ruta.
        self._rutas = TablaHash()
        self._cargar_rutas(carpeta + "/rutas.csv")

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

    def _cargar_rutas(self, ruta_archivo):
        # Las filas de cada ruta se ordenan por la columna orden antes de
        # enlazarlas: no suponemos que el CSV las traiga en orden.
        filas_por_ruta = TablaHash()
        nombres_rutas = []
        with open(ruta_archivo, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                ruta = fila["ruta"].strip()
                filas = filas_por_ruta.obtener(ruta)
                if filas is None:
                    filas = []
                    filas_por_ruta.poner(ruta, filas)
                    nombres_rutas.append(ruta)
                # (orden, estación): merge_sort compara primero por orden.
                filas.append((int(fila["orden"]), fila["estacion"].strip()))
        for nombre in nombres_rutas:
            filas = filas_por_ruta.obtener(nombre)
            if not esta_ordenado(filas):
                filas = merge_sort(filas)
            ruta = Ruta(nombre)
            for par in filas:
                estacion = par[1]
                if not ruta.nodos.contiene(estacion):
                    ruta.nodos.poner(estacion, ruta.paradas.agregar_al_final(estacion))
            self._rutas.poner(nombre, ruta)

    # Mantenimiento del arreglo de abiertas (R8).
    # Sacar o meter un nombre cuesta O(n) por el corrimiento de los demás;
    # se acepta porque cerrar y reabrir son mucho menos frecuentes que consultar.
    def _sacar_de_abiertas(self, nombre):
        a = self._abiertas
        i = primer_mayor_o_igual(a, nombre)
        if i == len(a) or a[i] != nombre:
            return
        # Corre una casilla a la izquierda todo lo que está después de i
        # y descarta la última, que quedó repetida.
        for j in range(i, len(a) - 1):
            a[j] = a[j + 1]
        a.pop()

    def _meter_en_abiertas(self, nombre):
        a = self._abiertas
        i = primer_mayor_o_igual(a, nombre)
        if i < len(a) and a[i] == nombre:
            return
        # Abre un hueco en i: agrega una casilla al final y corre una
        # casilla a la derecha todo lo que está desde i.
        a.append(nombre)
        j = len(a) - 1
        while j > i:
            a[j] = a[j - 1]
            j -= 1
        a[i] = nombre

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
