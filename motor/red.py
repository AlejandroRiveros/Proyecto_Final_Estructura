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
        # R6: buses al día que paran aquí (suma de las rutas que la tienen
        # como parada) y su posición en el arreglo del ranking (-1 si está
        # cerrada y por eso fuera del ranking).
        self.buses = 0
        self.pos_ranking = -1


def _va_antes(a, b):
    """Orden del ranking: más buses primero; a igual número, orden alfabético."""
    if a.buses != b.buses:
        return a.buses > b.buses
    return a.nombre < b.nombre


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
        # R4: ruta -> (estación -> arreglo ordenado y sin repetidos de horas "HH:MM").
        self._horarios = TablaHash()
        # R6: ruta -> (estación -> número de filas de horarios.csv, con repetidas).
        self._conteos = TablaHash()
        self._cargar_horarios(carpeta + "/horarios.csv")
        # R6: estaciones abiertas ordenadas con _va_antes. Cada estación guarda
        # su posición, así que se encuentra en O(1) sin recorrer el arreglo.
        self._ranking = []
        self._construir_ranking()
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

    def _cargar_horarios(self, ruta_archivo):
        # 1) Juntar las horas de cada par (ruta, estación).
        pares = []
        for fila in _leer_csv(ruta_archivo, ["ruta", "estacion", "hora"]):
            por_estacion = self._horarios.obtener(fila[0])
            if por_estacion is None:
                por_estacion = TablaHash()
                self._horarios.poner(fila[0], por_estacion)
            horas = por_estacion.obtener(fila[1])
            if horas is None:
                horas = []
                por_estacion.poner(fila[1], horas)
                pares.append((por_estacion, fila[1]))
            horas.append(fila[2])
            conteo_ruta = self._conteos.obtener(fila[0])
            if conteo_ruta is None:
                conteo_ruta = TablaHash()
                self._conteos.poner(fila[0], conteo_ruta)
            conteo_ruta.poner(fila[1], conteo_ruta.obtener(fila[1], 0) + 1)
        # 2) Ordenar cada arreglo (solo si hace falta) y quitar repetidas.
        # "HH:MM" con dos dígitos se compara bien como texto: "07:05" < "13:40".
        for par in pares:
            por_estacion = par[0]
            horas = por_estacion.obtener(par[1])
            if not esta_ordenado(horas):
                horas = merge_sort(horas)
            sin_repetidas = []
            for hora in horas:
                if len(sin_repetidas) == 0 or sin_repetidas[len(sin_repetidas) - 1] != hora:
                    sin_repetidas.append(hora)
            por_estacion.poner(par[1], sin_repetidas)

    def _buses_de(self, ruta, estacion):
        """Buses al día que aporta esta ruta a esta estación (0 si no hay horarios)."""
        conteo_ruta = self._conteos.obtener(ruta)
        if conteo_ruta is None:
            return 0
        return conteo_ruta.obtener(estacion, 0)

    def _construir_ranking(self):
        # Una sola vez al cargar: sumar los buses de cada parada de cada ruta
        # y ordenar las abiertas con merge sort, O(n log n).
        for nombre_ruta in self._rutas.claves():
            r = self._rutas.obtener(nombre_ruta)
            for estacion in r.paradas.a_lista():
                self._estaciones.obtener(estacion).buses += self._buses_de(nombre_ruta, estacion)
        # (-buses, nombre) ordena de mayor a menor y desempata alfabéticamente.
        claves = []
        for nombre in self._abiertas:
            claves.append((-self._estaciones.obtener(nombre).buses, nombre))
        claves = merge_sort(claves)
        self._ranking = []
        for clave in claves:
            estacion = self._estaciones.obtener(clave[1])
            estacion.pos_ranking = len(self._ranking)
            self._ranking.append(estacion)

    def _intercambiar_en_ranking(self, i, j):
        a = self._ranking
        a[i], a[j] = a[j], a[i]
        a[i].pos_ranking = i
        a[j].pos_ranking = j

    def _reubicar_en_ranking(self, estacion):
        """Mueve la estación a su lugar tras cambiar sus buses. O(d + 1), d = posiciones que salta."""
        i = estacion.pos_ranking
        while i > 0 and _va_antes(estacion, self._ranking[i - 1]):
            self._intercambiar_en_ranking(i, i - 1)
            i -= 1
        while i < len(self._ranking) - 1 and _va_antes(self._ranking[i + 1], estacion):
            self._intercambiar_en_ranking(i, i + 1)
            i += 1

    def _sacar_de_ranking(self, estacion):
        # O(n): se corre a la izquierda todo lo que está después y se
        # actualiza la posición guardada de cada estación corrida.
        a = self._ranking
        for j in range(estacion.pos_ranking, len(a) - 1):
            a[j] = a[j + 1]
            a[j].pos_ranking = j
        a.pop()
        estacion.pos_ranking = -1

    def _meter_en_ranking(self, estacion):
        # Búsqueda binaria de su lugar, O(log n), y corrimiento a la derecha, O(n).
        a = self._ranking
        bajo = 0
        alto = len(a)
        while bajo < alto:
            medio = (bajo + alto) // 2
            if _va_antes(a[medio], estacion):
                bajo = medio + 1
            else:
                alto = medio
        a.append(estacion)
        j = len(a) - 1
        while j > bajo:
            a[j] = a[j - 1]
            a[j].pos_ranking = j
            j -= 1
        a[bajo] = estacion
        estacion.pos_ranking = bajo

    def _cambiar_buses(self, nombre, delta):
        if delta == 0:
            return
        estacion = self._estaciones.obtener(nombre)
        estacion.buses += delta
        if estacion.pos_ranking != -1:
            self._reubicar_en_ranking(estacion)

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
        self._sacar_de_ranking(estacion)

    def _abrir_estacion(self, estacion):
        estacion.abierta = True
        self._meter_en_abiertas(estacion.nombre)
        self._meter_en_ranking(estacion)

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
        """Hora ("HH:MM") del primer bus de la ruta en la estación a la hora dada o después.

        None si la estación está cerrada (R8), la parada ya no está en la ruta (R7),
        no hay horarios para ese par o no pasan más buses ese día.
        O(log h), h = horas de esa ruta en esa estación: las dos revisiones son O(1).
        Los horarios no se borran al cerrar ni al quitar la parada, así que al
        reabrir o deshacer vuelven a valer sin hacer nada más.
        """
        est = self._estaciones.obtener(estacion)
        if est is None or not est.abierta:
            return None
        r = self._rutas.obtener(ruta)
        if r is None or not r.nodos.contiene(estacion):
            return None
        por_estacion = self._horarios.obtener(ruta)
        if por_estacion is None:
            return None
        horas = por_estacion.obtener(estacion)
        if horas is None:
            return None
        i = primer_mayor_o_igual(horas, hora)
        if i == len(horas):
            return None
        return horas[i]

    # R5
    def viaje(self, origen, destino):
        raise NotImplementedError

    # R6
    def ranking(self, k):
        """Las k estaciones abiertas con más buses al día, de mayor a menor. O(k).

        Empates: orden alfabético. Las cerradas no están en el arreglo.
        """
        salida = []
        i = 0
        while i < k and i < len(self._ranking):
            salida.append(self._ranking[i].nombre)
            i += 1
        return salida

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
        # R6: la parada suma los buses que esta ruta tiene ahí (0 si no hay horarios).
        self._cambiar_buses(nueva, self._buses_de(r.nombre, nueva))

    def _sacar_parada(self, r, estacion):
        r.paradas.quitar(r.nodos.obtener(estacion))
        r.nodos.eliminar(estacion)
        self._cambiar_buses(estacion, -self._buses_de(r.nombre, estacion))

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
