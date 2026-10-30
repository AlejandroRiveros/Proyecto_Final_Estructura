import csv

from motor.estructuras import ListaDoble, Pila, TablaHash, merge_sort, esta_ordenado, primer_mayor_o_igual

# Respuestas de estado(). Si el enunciado pide otro formato, solo se cambian aquí.
ABIERTA = "abierta"
CERRADA = "cerrada"


def _leer_csv(ruta_archivo, columnas):
    """Lee un CSV con csv.reader (no DictReader: sus filas son dict, prohibido en el motor).

    Devuelve una lista de filas, cada una con los valores de las columnas
    pedidas en ese orden. Las columnas se ubican por el encabezado, así
    que no importa en qué posición vengan en el archivo.
    """
    filas = []
    with open(ruta_archivo, encoding="utf-8", newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        posiciones = []
        for columna in columnas:
            posicion = -1
            for i in range(len(encabezado)):
                if encabezado[i].strip() == columna:
                    posicion = i
            if posicion == -1:
                raise ValueError("Falta la columna " + columna + " en " + ruta_archivo)
            posiciones.append(posicion)
        for fila in lector:
            if len(fila) == 0:
                continue
            valores = []
            for posicion in posiciones:
                valores.append(fila[posicion].strip())
            filas.append(valores)
    return filas


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
        # R9: historial de cambios en dos pilas (sesión 6). Cada entrada es
        # una tupla que describe el cambio, para poder aplicar su contrario.
        self._deshacer = Pila()
        self._rehacer = Pila()

    def _cargar_estaciones(self, ruta_archivo):
        nombres = []
        for fila in _leer_csv(ruta_archivo, ["nombre"]):
            nombre = fila[0]
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
        for fila in _leer_csv(ruta_archivo, ["ruta", "orden", "estacion"]):
            ruta = fila[0]
            filas = filas_por_ruta.obtener(ruta)
            if filas is None:
                filas = []
                filas_por_ruta.poner(ruta, filas)
                nombres_rutas.append(ruta)
            # (orden, estación): merge_sort compara primero por orden.
            filas.append((int(fila[1]), fila[2]))
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
        """Mete nueva justo después de despues_de en la ruta. O(1) promedio.

        True si la ruta cambió. False si la ruta no existe, despues_de no está
        en ella, nueva ya está en ella o nueva no es una estación de la red.
        """
        r = self._rutas.obtener(ruta)
        if r is None or not self._estaciones.contiene(nueva):
            return False
        if not r.nodos.contiene(despues_de) or r.nodos.contiene(nueva):
            return False
        self._registrar(("agregar", ruta, nueva, despues_de))
        self._insertar_parada(r, nueva, despues_de)
        return True

    def quitar_parada(self, ruta, estacion):
        """Saca estacion de la ruta. O(1) promedio.

        True si la ruta cambió. False si la ruta no existe o la estación no está en ella.
        """
        r = self._rutas.obtener(ruta)
        if r is None:
            return False
        nodo = r.nodos.obtener(estacion)
        if nodo is None:
            return False
        # Se guarda la parada anterior para poder deshacer: volver a meterla
        # después de ella, o al inicio si era la primera (anterior = None).
        anterior = None
        if nodo.anterior is not None:
            anterior = nodo.anterior.valor
        self._registrar(("quitar", ruta, estacion, anterior))
        self._sacar_parada(r, estacion)
        return True

    def _insertar_parada(self, r, nueva, despues_de):
        # despues_de = None significa al inicio de la ruta.
        if despues_de is None:
            nodo = r.paradas.agregar_al_inicio(nueva)
        else:
            nodo = r.paradas.insertar_despues(r.nodos.obtener(despues_de), nueva)
        r.nodos.poner(nueva, nodo)

    def _sacar_parada(self, r, estacion):
        r.paradas.quitar(r.nodos.obtener(estacion))
        r.nodos.eliminar(estacion)

    def recorrido(self, ruta, al_reves=False):
        """Paradas de la ruta en orden de ida, o de vuelta si al_reves. [] si la ruta no existe.

        O(L), L = paradas de la ruta.
        """
        r = self._rutas.obtener(ruta)
        if r is None:
            return []
        return r.paradas.a_lista(al_reves)

    # R8
    def cerrar(self, nombre):
        """True si la estación existía y estaba abierta; False si no había nada que cerrar.

        O(n), n = estaciones abiertas (corrimiento en el arreglo ordenado).
        """
        estacion = self._estaciones.obtener(nombre)
        if estacion is None or not estacion.abierta:
            return False
        self._registrar(("cerrar", nombre))
        self._cerrar_estacion(estacion)
        return True

    def reabrir(self, nombre):
        """True si la estación existía y estaba cerrada; False si no había nada que reabrir.

        O(n), n = estaciones abiertas.
        """
        estacion = self._estaciones.obtener(nombre)
        if estacion is None or estacion.abierta:
            return False
        self._registrar(("reabrir", nombre))
        self._abrir_estacion(estacion)
        return True

    # R9
    def _registrar(self, cambio):
        # Un cambio nuevo entra a deshacer y borra lo que había para rehacer.
        self._deshacer.apilar(cambio)
        self._rehacer.vaciar()

    def _aplicar(self, cambio, al_reves):
        """Aplica un cambio guardado (al_reves=False) o su contrario (al_reves=True).

        No pasa por los métodos públicos para no volver a registrar el cambio.
        """
        tipo = cambio[0]
        # El contrario de cada cambio: cerrar <-> reabrir, agregar <-> quitar.
        if al_reves:
            if tipo == "cerrar":
                tipo = "reabrir"
            elif tipo == "reabrir":
                tipo = "cerrar"
            elif tipo == "agregar":
                tipo = "quitar"
            else:
                tipo = "agregar"
        if tipo == "cerrar":
            self._cerrar_estacion(self._estaciones.obtener(cambio[1]))
        elif tipo == "reabrir":
            self._abrir_estacion(self._estaciones.obtener(cambio[1]))
        elif tipo == "agregar":
            # cambio[3] es la parada después de la cual va (None = al inicio).
            self._insertar_parada(self._rutas.obtener(cambio[1]), cambio[2], cambio[3])
        else:
            self._sacar_parada(self._rutas.obtener(cambio[1]), cambio[2])

    def deshacer(self):
        """Deshace el último cambio. True si había algo que deshacer.

        O(1) para sacar de la pila + el costo del cambio contrario
        (O(1) en rutas, O(n) en cerrar/reabrir).
        """
        cambio = self._deshacer.desapilar()
        if cambio is None:
            return False
        self._aplicar(cambio, al_reves=True)
        self._rehacer.apilar(cambio)
        return True

    def rehacer(self):
        """Vuelve a aplicar el último cambio deshecho. True si había algo que rehacer."""
        cambio = self._rehacer.desapilar()
        if cambio is None:
            return False
        self._aplicar(cambio, al_reves=False)
        self._deshacer.apilar(cambio)
        return True
