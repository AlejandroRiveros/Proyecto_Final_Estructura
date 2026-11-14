"""Mediciones del panel de rendimiento (R11).

Este archivo está fuera de motor/, así que aquí sí se permite todo
(dict, sorted, statistics...). El motor se usa solo por su API pública:
cada red se escribe como los tres CSV y se carga con Red(carpeta), para
medir exactamente lo que se entrega, con sus índices y su ranking.

Reglas de medición (decididas con el equipo):
- La generación de los CSV y la carga de la red quedan fuera del tiempo
  de las operaciones. La carga se mide aparte, como su propio experimento.
- Las consultas, que tardan 1 o 2 µs, se miden por lotes de muchas llamadas.
  Se hacen varias rondas y se reporta la mediana por llamada.
- Las operaciones que modifican la red se cronometran solas, llamada por
  llamada (al tiempo se le resta el costo del propio reloj). La red se
  restaura después, fuera del cronómetro, con deshacer(). Así los datos y
  las dos pilas del historial vuelven al mismo estado en cada repetición.
- Durante cada tiempo medido se apaga el recolector de basura de Python
  (lo mismo que hace el módulo timeit). Si no, sus pasadas recorren todos
  los objetos vivos, y en redes grandes inflan el tiempo de cualquier
  operación que cree objetos (por ejemplo viaje()).
- La curva esperada se escala con la mediana de tiempo / f(x). Esa curva
  es una referencia para comparar la forma; no prueba la complejidad.
"""

import csv
import gc
import math
import os
import random
import statistics
import tempfile
import time

from motor import Red, simular_fila

# ---------------------------------------------------------------------------
# Generación de redes
# ---------------------------------------------------------------------------


def escribir_red(carpeta, estaciones, rutas=(), horarios=(), desordenar=False, semilla=0):
    """Escribe estaciones.csv, rutas.csv y horarios.csv en carpeta.

    rutas: lista de (nombre_ruta, [estaciones en orden]).
    horarios: lista de (ruta, estacion, "HH:MM").
    desordenar=True baraja las filas, para que la carga tenga que ordenar.
    """
    filas_est = [[e] for e in estaciones]
    filas_rut = [[r, i + 1, e] for r, paradas in rutas for i, e in enumerate(paradas)]
    filas_hor = [list(h) for h in horarios]
    if desordenar:
        azar = random.Random(semilla)
        azar.shuffle(filas_est)
        azar.shuffle(filas_rut)
        azar.shuffle(filas_hor)
    for nombre, encabezado, filas in (
        ("estaciones.csv", ["nombre"], filas_est),
        ("rutas.csv", ["ruta", "orden", "estacion"], filas_rut),
        ("horarios.csv", ["ruta", "estacion", "hora"], filas_hor),
    ):
        with open(os.path.join(carpeta, nombre), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(encabezado)
            w.writerows(filas)


def cargar_red(estaciones, rutas=(), horarios=(), desordenar=False):
    """Escribe la red en una carpeta temporal y la carga con Red(carpeta).

    Red lee los CSV solo al construirse, así que la carpeta se borra al salir
    del with (también si hay una excepción) y no quedan archivos en disco.
    """
    with tempfile.TemporaryDirectory(prefix="r11_") as carpeta:
        escribir_red(carpeta, estaciones, rutas, horarios, desordenar)
        return Red(carpeta)


def nombres(n, prefijo="E"):
    """n nombres de estación distintos y en orden: "E 000000", "E 000001"..."""
    return ["%s %06d" % (prefijo, i) for i in range(n)]


def hora_de(minuto):
    return "%02d:%02d" % (minuto // 60, minuto % 60)


# ---------------------------------------------------------------------------
# Cronómetro
# ---------------------------------------------------------------------------


def _costo_reloj():
    """Lo que tarda un par de llamadas a perf_counter_ns (se resta en cada medición)."""
    muestras = []
    for _ in range(20000):
        a = time.perf_counter_ns()
        b = time.perf_counter_ns()
        muestras.append(b - a)
    return statistics.median(muestras)


COSTO_RELOJ_NS = _costo_reloj()


class _SinRecolector:
    """Apaga el recolector de basura mientras se mide (como timeit)."""

    def __enter__(self):
        self.estaba = gc.isenabled()
        gc.collect()
        gc.disable()

    def __exit__(self, *_):
        if self.estaba:
            gc.enable()


def por_lote(llamar, argumentos, rondas=7):
    """Mediana, sobre varias rondas, del tiempo por llamada (µs) de un lote de consultas."""
    tiempos = []
    for _ in range(rondas):
        with _SinRecolector():
            inicio = time.perf_counter_ns()
            for args in argumentos:
                llamar(*args)
            fin = time.perf_counter_ns()
        tiempos.append((fin - inicio) / len(argumentos))
    return statistics.median(tiempos) / 1000


def por_llamada(preparar, medir, restaurar, repeticiones):
    """Mediana del tiempo (µs) de medir(), cronometrado solo.

    preparar() y restaurar() corren fuera del cronómetro. Las tres funciones
    llaman a operaciones del motor que devuelven True/False, y cada una tiene
    que devolver True: si alguna no cambió nada, la medición mezclaría
    cambios con llamadas sin efecto, así que se detiene con un error.
    Cada repetición parte del mismo estado: datos iguales, y las pilas con
    pocos registros que no crecen entre repeticiones: uno en casi todos los
    experimentos, y dos en el de reabrir, cuya restauración hace dos deshacer().
    """
    tiempos = []
    with _SinRecolector():
        for _ in range(repeticiones):
            _exigir(preparar(), "preparar")
            inicio = time.perf_counter_ns()
            hecho = medir()
            fin = time.perf_counter_ns()
            _exigir(hecho, "la operación medida")
            _exigir(restaurar(), "restaurar")
            tiempos.append(max(fin - inicio - COSTO_RELOJ_NS, 0))
    return statistics.median(tiempos) / 1000


def _exigir(resultado, paso):
    if resultado is not True:
        raise RuntimeError("R11: %s no hizo ningún cambio; la medición no sería válida" % paso)


def _nada():
    return True


# ---------------------------------------------------------------------------
# Complejidades esperadas y comparación
# ---------------------------------------------------------------------------

FUNCIONES = {
    "O(1)": lambda x: 1.0,
    "O(log n)": lambda x: math.log2(x),
    "O(n)": lambda x: float(x),
    "O(n log n)": lambda x: x * math.log2(x),
}


def referencia(puntos, esperado):
    """Curva esperada escalada: c * f(x), con c = mediana de tiempo / f(x)."""
    f = FUNCIONES[esperado]
    c = statistics.median(t / f(x) for x, t in puntos)
    return [(x, c * f(x)) for x, _ in puntos]


def crecimiento(puntos, esperado):
    """Para cada duplicación: cuántas veces creció el tiempo y cuántas debía crecer."""
    f = FUNCIONES[esperado]
    filas = []
    for (x0, t0), (x1, t1) in zip(puntos, puntos[1:]):
        filas.append((x0, x1, t1 / t0 if t0 > 0 else float("nan"), f(x1) / f(x0)))
    return filas


def exponente(puntos):
    """Pendiente en escala log-log entre el primer y el último punto.

    Sirve de resumen: 0 = constante, 1 = lineal; un logaritmo da algo cercano a 0.
    """
    (x0, t0), (x1, t1) = puntos[0], puntos[-1]
    if t0 <= 0 or t1 <= 0:
        return float("nan")
    return math.log(t1 / t0) / math.log(x1 / x0)


# ---------------------------------------------------------------------------
# Experimentos del modo "Escalamiento por operación"
# ---------------------------------------------------------------------------
# Cada experimento devuelve un dict con:
#   requisito, operacion, variable (qué crece), fijos (qué se mantiene),
#   esperado (clave de FUNCIONES), puntos [(x, µs)], explicacion.

TAMANOS_N = [10000, 20000, 40000, 80000]
TAMANOS_K = [10, 20, 40, 80, 160]
TAMANOS_L = [1000, 2000, 4000, 8000]
TAMANOS_H = [180, 360, 720, 1440]

_azar = random.Random(11)


def _red_estaciones(n, cache={}):
    """Red con n estaciones y sin rutas (se reutiliza entre experimentos de consulta)."""
    if n not in cache:
        cache[n] = cargar_red(nombres(n))
    return cache[n]


def exp_estado():
    puntos = []
    for n in TAMANOS_N:
        red = _red_estaciones(n)
        nom = nombres(n)
        consultas = [(_azar.choice(nom),) for _ in range(5000)]
        puntos.append((n, por_lote(red.estado, consultas)))
    return dict(
        requisito="R1", operacion="estado(nombre)",
        variable="n = estaciones de la red", fijos="Consultas a estaciones que existen",
        esperado="O(1)", puntos=puntos,
        explicacion="Tabla hash propia: el nombre lleva directo a su cubeta, así que "
        "el tiempo no depende de n. Pequeñas subidas vienen de la memoria caché del "
        "procesador, no del algoritmo.",
    )


def exp_autocompletar_n():
    puntos = []
    for n in TAMANOS_N:
        red = _red_estaciones(n)
        # Prefijo de 6 caracteres ("E 0123"): hay al menos 10 coincidencias, así que
        # siempre se devuelven k = 10 y solo cambia el tamaño de la búsqueda binaria.
        consultas = [("E %04d" % _azar.randrange(n // 100), 10) for _ in range(3000)]
        puntos.append((n, por_lote(red.autocompletar, consultas)))
    return dict(
        requisito="R2", operacion="autocompletar(prefijo, k)",
        variable="n = estaciones abiertas", fijos="k = 10, siempre con 10 resultados",
        esperado="O(log n)", puntos=puntos,
        explicacion="Búsqueda binaria del primer nombre >= prefijo y luego k pasos. "
        "Con k fijo solo crece la parte log n, que de 10.000 a 80.000 pasa de 13,3 a "
        "16,3 pasos (+23 %). Como los k pasos y el costo de la llamada no cambian, la "
        "curva medida sube menos que la referencia, y eso es lo esperado.",
    )


def exp_autocompletar_k():
    n = 40000
    red = _red_estaciones(n)
    puntos = []
    for k in TAMANOS_K:
        consultas = [("E", k)] * 1000
        puntos.append((k, por_lote(red.autocompletar, consultas)))
    return dict(
        requisito="R2", operacion="autocompletar(prefijo, k)",
        variable="k = resultados pedidos", fijos="n = 40.000; el prefijo coincide con todas",
        esperado="O(n)", puntos=puntos,
        explicacion="Con n fijo, la búsqueda binaria cuesta lo mismo y lo que crece es "
        "copiar los k resultados: lineal en k (en la gráfica, x = k).",
    )


def exp_rango_n():
    puntos = []
    for n in TAMANOS_N:
        red = _red_estaciones(n)
        nom = nombres(n)
        consultas = []
        for _ in range(3000):
            i = _azar.randrange(n - 10)
            consultas.append((nom[i], nom[i + 9]))
        puntos.append((n, por_lote(red.rango, consultas)))
    return dict(
        requisito="R3", operacion="rango(desde, hasta)",
        variable="n = estaciones abiertas", fijos="m = 10 resultados por consulta",
        esperado="O(log n)", puntos=puntos,
        explicacion="Búsqueda binaria del inicio y luego se copian los m resultados. "
        "Con m fijo solo crece log n, así que la curva es casi plana.",
    )


def exp_rango_m():
    n = 40000
    red = _red_estaciones(n)
    nom = nombres(n)
    puntos = []
    for m in [50, 100, 200, 400, 800]:
        consultas = []
        for _ in range(300):
            i = _azar.randrange(n - m)
            consultas.append((nom[i], nom[i + m - 1]))
        puntos.append((m, por_lote(red.rango, consultas)))
    return dict(
        requisito="R3", operacion="rango(desde, hasta)",
        variable="m = estaciones dentro del rango", fijos="n = 40.000",
        esperado="O(n)", puntos=puntos,
        explicacion="Con n fijo, el costo lo pone copiar los m resultados: lineal en m "
        "(en la gráfica, x = m).",
    )


def exp_proximo_bus():
    puntos = []
    for h in TAMANOS_H:
        minutos = sorted(_azar.sample(range(1440), h))
        horarios = [("R", "E 000000", hora_de(m)) for m in minutos]
        red = cargar_red(nombres(2), [("R", nombres(2))], horarios)
        consultas = [("E 000000", "R", hora_de(_azar.randrange(1440))) for _ in range(5000)]
        puntos.append((h, por_lote(red.proximo_bus, consultas)))
    return dict(
        requisito="R4", operacion="proximo_bus(estacion, ruta, hora)",
        variable="h = horas distintas de ese par (ruta, estación), ya sin repetidas",
        fijos="Una ruta, una estación; horas al azar dentro del día (máximo 1.440)",
        esperado="O(log n)", puntos=puntos,
        explicacion="Búsqueda binaria sobre el arreglo de horas sin repetidas. De 180 a "
        "1.440 horas, log h pasa de 7,5 a 10,5 (+40 %), y el costo fijo de la llamada "
        "(dos búsquedas en tablas hash) hace que se note todavía menos. Una curva casi "
        "plana aquí no significa O(1). Filas repetidas en el CSV no cambian h.",
    )


def _red_ranking(n):
    """n estaciones y una ruta de 2.000 paradas con 0 a 5 buses cada una."""
    nom = nombres(n)
    paradas = nom[:2000]
    horarios = []
    for e in paradas:
        for b in range(_azar.randrange(6)):
            horarios.append(("R", e, hora_de(b * 60)))
    return cargar_red(nom, [("R", paradas)], horarios)


def exp_ranking_k():
    red = _red_ranking(40000)
    puntos = [(k, por_lote(red.ranking, [(k,)] * 2000)) for k in TAMANOS_K]
    return dict(
        requisito="R6", operacion="ranking(k)",
        variable="k = estaciones pedidas", fijos="n = 40.000",
        esperado="O(n)", puntos=puntos,
        explicacion="El arreglo ya está ordenado; ranking(k) solo copia los primeros k: "
        "lineal en k (en la gráfica, x = k).",
    )


def exp_ranking_n():
    puntos = []
    for n in TAMANOS_N:
        red = _red_ranking(n)
        puntos.append((n, por_lote(red.ranking, [(10,)] * 5000)))
    return dict(
        requisito="R6", operacion="ranking(k)",
        variable="n = estaciones de la red", fijos="k = 10",
        esperado="O(1)", puntos=puntos,
        explicacion="Con k fijo, la consulta no depende del tamaño de la red: el orden "
        "se mantiene al editar, no al consultar.",
    )


def exp_recorrido():
    puntos = []
    for L in TAMANOS_L:
        nom = nombres(L)
        red = cargar_red(nom, [("R", nom)])
        puntos.append((L, por_lote(red.recorrido, [("R",)] * 200)))
    return dict(
        requisito="R7", operacion="recorrido(ruta)",
        variable="L = paradas de la ruta", fijos="Una sola ruta",
        esperado="O(n)", puntos=puntos,
        explicacion="Recorre la lista doblemente enlazada de la ruta de cabeza a cola: "
        "lineal en L (en la gráfica, x = L).",
    )


def _red_edicion(n, con_zzz_en_t=True):
    """AAA (6 buses, ruta S) y ZZZ (5 buses, ruta T) arriba del ranking; el resto con 0.

    Quitar AAA la baja 1 puesto (d = 1). Quitar ZZZ la manda al final (d ~ n).
    """
    nom = ["AAA"] + nombres(n - 2) + ["ZZZ"]
    t = ["ZZZ", "E 000001"] if con_zzz_en_t else ["E 000001"]
    rutas = [("S", ["AAA", "E 000000"]), ("T", t)]
    horarios = [("S", "AAA", hora_de(60 * i)) for i in range(6)]
    horarios += [("T", "ZZZ", hora_de(60 * i)) for i in range(5)]
    return cargar_red(nom, rutas, horarios)


def _exp_edicion(operacion, d, construir, medir, esperado, explicacion):
    puntos = []
    for n in TAMANOS_N:
        red = construir(n)
        reps = 300 if esperado == "O(1)" else 40
        puntos.append((n, por_llamada(_nada, lambda: medir(red), red.deshacer, reps)))
    return dict(
        requisito="R7 + R6", operacion=operacion,
        variable="n = estaciones de la red",
        fijos="Desplazamiento en el ranking: " + d,
        esperado=esperado, puntos=puntos, explicacion=explicacion,
    )


def exp_quitar_pequeno():
    return _exp_edicion(
        "quitar_parada (d = 1)", "d = 1 (la estación baja un solo puesto)",
        _red_edicion, lambda red: red.quitar_parada("S", "AAA"), "O(1)",
        "Lista doble + tabla hash: quitar es O(1). Mantener el ranking cuesta O(d + 1) "
        "intercambios, y aquí d = 1. Se cronometra solo quitar_parada; deshacer() "
        "restaura la red fuera del cronómetro.",
    )


def exp_quitar_extremo():
    return _exp_edicion(
        "quitar_parada (d ~ n)", "d ~ n (la estación pasa del puesto 2 al último)",
        _red_edicion, lambda red: red.quitar_parada("T", "ZZZ"), "O(n)",
        "La ruta se edita en O(1), pero la estación cruza todo el ranking: O(d + 1) con "
        "d ~ n. Es el costo de tener ranking(k) en O(k). Pendiente de que el profesor "
        "confirme si R7 se mide con este mantenimiento incluido.",
    )


def exp_agregar_pequeno():
    return _exp_edicion(
        "agregar_parada (d = 0)", "d = 0 (AAA2 pasa de 0 a 1 bus sin cambiar de puesto)",
        lambda n: _red_edicion_agregar(n), lambda red: red.agregar_parada("T", "AAA2", "E 000001"),
        "O(1)",
        "Insertar en la lista doble es O(1). La estación nueva tiene 1 bus en esa ruta y "
        "ya iba primera entre las de 0 buses, así que no cambia de puesto.",
    )


def _red_edicion_agregar(n):
    """Como _red_edicion, pero con AAA2 fuera de T y 1 bus de T registrado para ella."""
    nom = ["AAA", "AAA2"] + nombres(n - 3) + ["ZZZ"]
    rutas = [("S", ["AAA", "E 000000"]), ("T", ["ZZZ", "E 000001"])]
    horarios = [("S", "AAA", hora_de(60 * i)) for i in range(6)]
    horarios += [("T", "ZZZ", hora_de(60 * i)) for i in range(5)]
    horarios += [("T", "AAA2", "00:00")]
    return cargar_red(nom, rutas, horarios)


def _red_cierre(n):
    return _red_estaciones(n)


def exp_cerrar():
    puntos = []
    for n in TAMANOS_N:
        red = _red_cierre(n)
        puntos.append((n, por_llamada(_nada, lambda: red.cerrar("E 000000"), red.deshacer, 40)))
    return dict(
        requisito="R8", operacion="cerrar(nombre)",
        variable="n = estaciones abiertas", fijos="Se cierra la primera en orden alfabético (peor caso)",
        esperado="O(n)", puntos=puntos,
        explicacion="Sacarla del arreglo ordenado de abiertas obliga a correr las n que "
        "siguen (y lo mismo en el ranking). Es el precio de tener R2 y R3 en O(log n).",
    )


def exp_reabrir():
    puntos = []
    for n in TAMANOS_N:
        red = _red_cierre(n)

        def preparar(red=red):
            return red.cerrar("E 000000")

        def restaurar(red=red):
            # Deshace reabrir y luego cerrar: datos y pilas quedan como al inicio.
            return red.deshacer() and red.deshacer()

        puntos.append((n, por_llamada(preparar, lambda: red.reabrir("E 000000"), restaurar, 40)))
    return dict(
        requisito="R8", operacion="reabrir(nombre)",
        variable="n = estaciones abiertas", fijos="Se reabre la primera en orden alfabético (peor caso)",
        esperado="O(n)", puntos=puntos,
        explicacion="Búsqueda binaria de su lugar y corrimiento de las n que siguen.",
    )


def _exp_historial(operacion, construir, hacer, cronometrar_rehacer, esperado, reps, explicacion, fijos):
    puntos = []
    for n in TAMANOS_N:
        red = construir(n)
        if cronometrar_rehacer:
            def preparar(red=red):
                return hacer(red) and red.deshacer()
            medir = red.rehacer
            restaurar = red.deshacer
        else:
            def preparar(red=red):
                return hacer(red)
            medir = red.deshacer
            restaurar = _nada
        puntos.append((n, por_llamada(preparar, medir, restaurar, reps)))
    return dict(
        requisito="R9", operacion=operacion, variable="n = estaciones de la red",
        fijos=fijos, esperado=esperado, puntos=puntos, explicacion=explicacion,
    )


def exp_deshacer_quitar():
    return _exp_historial(
        "deshacer() de quitar_parada", _red_edicion,
        lambda red: red.quitar_parada("S", "AAA"), False, "O(1)", 300,
        "Sacar de la pila es O(1) y vuelve a meter la parada en O(1) (d = 1).",
        "Cambio restaurado: quitar_parada con d = 1",
    )


def exp_rehacer_quitar():
    return _exp_historial(
        "rehacer() de quitar_parada", _red_edicion,
        lambda red: red.quitar_parada("S", "AAA"), True, "O(1)", 300,
        "Sacar de la pila es O(1) y vuelve a quitar la parada en O(1) (d = 1).",
        "Cambio restaurado: quitar_parada con d = 1",
    )


def exp_deshacer_cerrar():
    return _exp_historial(
        "deshacer() de cerrar", _red_cierre,
        lambda red: red.cerrar("E 000000"), False, "O(n)", 40,
        "La pila es O(1), pero deshacer un cierre es reabrir: O(n). El costo lo pone "
        "el cambio restaurado, no el historial.",
        "Cambio restaurado: cerrar la primera estación (peor caso)",
    )


def exp_rehacer_cerrar():
    return _exp_historial(
        "rehacer() de cerrar", _red_cierre,
        lambda red: red.cerrar("E 000000"), True, "O(n)", 40,
        "Rehacer un cierre es volver a cerrar: O(n), igual que cerrar().",
        "Cambio restaurado: cerrar la primera estación (peor caso)",
    )


def exp_viaje():
    puntos = []
    for L in TAMANOS_L:
        a = nombres(L, "A")
        b = ["A %06d" % (L - 1)] + nombres(L - 1, "B")
        red = cargar_red(a + b[1:], [("RA", a), ("RB", b)])
        consultas = [(a[0], b[-1])] * 20
        puntos.append((L, por_lote(red.viaje, consultas, rondas=5)))
    return dict(
        requisito="R5 (informativo)", operacion="viaje(origen, destino)",
        variable="L = paradas de cada ruta", fijos="Origen y destino con una ruta cada uno; transbordo al final",
        esperado="O(n)", puntos=puntos,
        explicacion="Recorre hacia adelante las rutas del origen y hacia atrás las del "
        "destino: lineal en el largo de esas rutas. R5 no cuenta para los puntos de "
        "rendimiento; se muestra para completar el panel.",
    )


def exp_carga():
    puntos = []
    for n in [5000, 10000, 20000, 40000]:
        nom = nombres(n)
        # 50 rutas que se reparten todas las estaciones: filas de rutas = n.
        rutas = [("R%d" % i, nom[i::50]) for i in range(50)]
        horarios = [(r, e, hora_de(_azar.randrange(1440))) for r, ps in rutas for e in ps for _ in range(4)]
        total = n + sum(len(ps) for _, ps in rutas) + len(horarios)
        tiempos = []
        with tempfile.TemporaryDirectory(prefix="r11_carga_") as carpeta:
            escribir_red(carpeta, nom, rutas, horarios, desordenar=True)
            for _ in range(3):
                with _SinRecolector():
                    inicio = time.perf_counter_ns()
                    red = Red(carpeta)
                    fin = time.perf_counter_ns()
                # La red se libera después de parar el reloj: liberar un objeto
                # grande no es parte de la carga.
                del red
                tiempos.append((fin - inicio) / 1000)
        puntos.append((total, statistics.median(tiempos)))
    return dict(
        requisito="Carga", operacion="Red(carpeta)",
        variable="T = estaciones + filas de rutas + filas de horarios",
        fijos="Los tres CSV barajados (la carga tiene que ordenar: peor caso)",
        esperado="O(n log n)", puntos=puntos,
        explicacion="Leer los CSV es O(T) con tablas hash O(1) en promedio. Lo que se "
        "ordena con merge sort, y solo si viene desordenado, son las estaciones, las "
        "paradas de cada ruta y las horas de cada par; además se arma el ranking en "
        "O(n log n). O(T log T) es una cota global (en la gráfica, x = T).",
    )


TAMANOS_P = [50000, 100000, 200000, 400000]


def _llegadas(p, desordenar):
    # 50 pasajeros por minuto (segundo de llegada, como pide el enunciado): al
    # duplicar P se duplica también la ventana de tiempo.
    llegadas = [i * 60 // 50 for i in range(p)]
    if desordenar:
        random.Random(p).shuffle(llegadas)
    return llegadas


def _exp_fila(desordenar, esperado, fijos, explicacion):
    puntos = []
    for p in TAMANOS_P:
        llegadas = _llegadas(p, desordenar)
        tiempos = []
        for _ in range(3):
            with _SinRecolector():
                inicio = time.perf_counter_ns()
                salidas = simular_fila(llegadas, 180, 160)
                fin = time.perf_counter_ns()
            if len(salidas) != p:
                raise RuntimeError("R11: simular_fila no devolvió una salida por pasajero")
            del salidas
            tiempos.append((fin - inicio) / 1000)
        puntos.append((p, statistics.median(tiempos)))
    return dict(
        requisito="R10", operacion="simular_fila(llegadas, frecuencia, capacidad)",
        variable="P = pasajeros", fijos=fijos, esperado=esperado, puntos=puntos,
        explicacion=explicacion,
    )


def exp_fila_ordenada():
    return _exp_fila(
        False, "O(n)",
        "Llegadas ya ordenadas, 50 por minuto; un bus cada 180 s, capacidad 160",
        "Revisar el orden es una pasada O(P). Luego cada pasajero entra y sale de la "
        "cola una vez, y cada salida con abordaje sube al menos a uno, así que hay a lo "
        "sumo P salidas; las vacías se saltan con una cuenta. Total O(P). La red no "
        "interviene: R10 no depende de estaciones ni rutas.",
    )


def exp_fila_desordenada():
    return _exp_fila(
        True, "O(n log n)",
        "Las mismas llegadas, barajadas; un bus cada 180 s, capacidad 160",
        "La revisión del orden falla, así que se ordenan los pares (segundo, posición) con merge sort, "
        "O(P log P), y después se simula en O(P). Domina el ordenamiento. De 50.000 a "
        "400.000, log P solo pasa de 15,6 a 18,6, así que cuesta distinguir esta curva "
        "de una lineal más empinada.",
    )


EXPERIMENTOS = [
    exp_carga,
    exp_estado,
    exp_autocompletar_n, exp_autocompletar_k,
    exp_rango_n, exp_rango_m,
    exp_proximo_bus,
    exp_viaje,
    exp_ranking_k, exp_ranking_n,
    exp_recorrido,
    exp_quitar_pequeno, exp_quitar_extremo, exp_agregar_pequeno,
    exp_cerrar, exp_reabrir,
    exp_deshacer_quitar, exp_rehacer_quitar, exp_deshacer_cerrar, exp_rehacer_cerrar,
    exp_fila_ordenada, exp_fila_desordenada,
]


# ---------------------------------------------------------------------------
# Modo "Red real replicada"
# ---------------------------------------------------------------------------
# La red real (carpeta datos/) se copia 1, 2, 4 y 8 veces como copias
# separadas: la copia 1 conserva los nombres y la copia c >= 2 agrega " ~c"
# a cada estación y a cada ruta, de forma consistente en los tres CSV.
# Se conservan todas las filas de horarios, incluidas las repetidas.
# No es una reproducción del script del profesor: no sabemos cómo transforma
# él rutas, horarios o consultas.

COPIAS = [1, 2, 4, 8]
DATOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos")


def _leer(carpeta, archivo, columnas):
    """Filas del CSV con solo las columnas pedidas, en ese orden."""
    with open(os.path.join(carpeta, archivo), newline="", encoding="utf-8") as f:
        lector = csv.reader(f)
        encabezado = [c.strip() for c in next(lector)]
        pos = [encabezado.index(c) for c in columnas]
        return [[fila[i].strip() for i in pos] for fila in lector if fila]


def leer_red_real(carpeta=DATOS):
    return {
        "estaciones": [f[0] for f in _leer(carpeta, "estaciones.csv", ["nombre"])],
        "rutas": _leer(carpeta, "rutas.csv", ["ruta", "orden", "estacion"]),
        "horarios": _leer(carpeta, "horarios.csv", ["ruta", "estacion", "hora"]),
    }


def sufijo(nombre, copia):
    return nombre if copia == 1 else "%s ~%d" % (nombre, copia)


def escribir_replica(carpeta, real, copias):
    filas_est, filas_rut, filas_hor = [], [], []
    for c in range(1, copias + 1):
        filas_est += [[sufijo(e, c)] for e in real["estaciones"]]
        filas_rut += [[sufijo(r, c), o, sufijo(e, c)] for r, o, e in real["rutas"]]
        filas_hor += [[sufijo(r, c), sufijo(e, c), h] for r, e, h in real["horarios"]]
    for nombre, encabezado, filas in (
        ("estaciones.csv", ["nombre"], filas_est),
        ("rutas.csv", ["ruta", "orden", "estacion"], filas_rut),
        ("horarios.csv", ["ruta", "estacion", "hora"], filas_hor),
    ):
        with open(os.path.join(carpeta, nombre), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(encabezado)
            w.writerows(filas)
    return filas_est, filas_rut, filas_hor


def dimensiones(filas_est, filas_rut, filas_hor):
    """Lo que mide cada dimensión en la réplica escrita (calculado de los CSV, no supuesto)."""
    paradas = {}
    rutas_de = {}
    for r, _, e in filas_rut:
        paradas.setdefault(r, set()).add(e)
        rutas_de.setdefault(e, set()).add(r)
    horas = {}
    for r, e, h in filas_hor:
        horas.setdefault((r, e), set()).add(h)
    largo = [len(v) for v in paradas.values()]
    por_par = [len(v) for v in horas.values()]
    por_est = [len(v) for v in rutas_de.values()]
    return {
        "Estaciones": len(filas_est),
        "Rutas": len(paradas),
        "Filas de rutas.csv": len(filas_rut),
        "Filas de horarios.csv": len(filas_hor),
        "Paradas por ruta (promedio)": round(statistics.mean(largo), 1),
        "Paradas por ruta (máximo)": max(largo),
        "Horas distintas por par ruta–estación (máximo)": max(por_par),
        "Rutas por estación (máximo)": max(por_est),
    }


def _muestras_base(real, azar):
    """Consultas sobre la copia 1. En cada tamaño se mandan a una copia al azar,
    así todos los tamaños hacen el mismo trabajo, solo que en una red más grande."""
    con_horario = sorted({(r, e) for r, e, _ in real["horarios"]})
    rutas = sorted({r for r, _, _ in real["rutas"]})
    paradas = sorted({(r, e) for r, _, e in real["rutas"]})
    est = real["estaciones"]
    return {
        "estaciones": [azar.choice(est) for _ in range(2000)],
        "prefijos": [azar.choice(est)[:3] for _ in range(2000)],
        "proximo": [(e, r, hora_de(azar.randrange(1440))) for r, e in
                    (azar.choice(con_horario) for _ in range(2000))],
        "viajes": [tuple(azar.sample(est, 2)) for _ in range(100)],
        "rutas": [azar.choice(rutas) for _ in range(500)],
        "paradas": [azar.choice(paradas) for _ in range(300)],
        "cierres": [azar.choice(est) for _ in range(100)],
    }


def _posicion(red, nombre):
    """Puesto de la estación en el ranking, por la API pública (fuera del cronómetro)."""
    for puesto, (estacion, _) in enumerate(red.ranking(10 ** 9)):
        if estacion == nombre:
            return puesto
    raise ValueError(nombre)


def _medir_replica(red, base, c, azar, todos_ordenados):
    """Diccionario operación -> (µs, dato extra o None) para una réplica con c copias."""
    copia = lambda: azar.randrange(1, c + 1)
    res = {}
    # En estado, proximo_bus y recorrido se mide además consultando solo la
    # copia 1: el algoritmo hace lo mismo, pero los datos tocados caben mejor
    # en la caché. La diferencia entre las dos mediciones es efecto de memoria.
    res["estado"] = (por_lote(red.estado, [(sufijo(e, copia()),) for e in base["estaciones"]]),
                     round(por_lote(red.estado, [(e,) for e in base["estaciones"]]), 2))
    res["autocompletar"] = (por_lote(red.autocompletar, [(p, 10) for p in base["prefijos"]]), None)
    consultas = []
    for _ in range(2000):
        i = azar.randrange(len(todos_ordenados) - 10)
        consultas.append((todos_ordenados[i], todos_ordenados[i + 9]))
    m = statistics.median(len(red.rango(a, b)) for a, b in consultas[:200])
    res["rango"] = (por_lote(red.rango, consultas), m)
    proximo = []
    for e, r, h in base["proximo"]:
        k = copia()
        proximo.append((sufijo(e, k), sufijo(r, k), h))
    res["proximo_bus"] = (por_lote(red.proximo_bus, proximo),
                          round(por_lote(red.proximo_bus, base["proximo"]), 2))
    viajes = []
    for a, b in base["viajes"]:
        k = copia()
        viajes.append((sufijo(a, k), sufijo(b, k)))
    res["viaje"] = (por_lote(red.viaje, viajes, rondas=5), None)
    res["ranking"] = (por_lote(red.ranking, [(10,)] * 2000), None)
    res["recorrido"] = (por_lote(red.recorrido, [(sufijo(r, copia()),) for r in base["rutas"]]),
                        round(por_lote(red.recorrido, [(r,) for r in base["rutas"]]), 2))

    # Ediciones: cada una se cronometra sola y se restaura con deshacer() fuera
    # del cronómetro. d = puestos que se movió la estación en el ranking.
    tiempos, ds, tiempos_deshacer = [], [], []
    with _SinRecolector():
        for r, e in base["paradas"]:
            k = copia()
            r, e = sufijo(r, k), sufijo(e, k)
            antes = _posicion(red, e)
            inicio = time.perf_counter_ns()
            hecho = red.quitar_parada(r, e)
            fin = time.perf_counter_ns()
            _exigir(hecho, "quitar_parada")
            ds.append(abs(_posicion(red, e) - antes))
            inicio2 = time.perf_counter_ns()
            hecho = red.deshacer()
            fin2 = time.perf_counter_ns()
            _exigir(hecho, "deshacer")
            tiempos.append(max(fin - inicio - COSTO_RELOJ_NS, 0))
            tiempos_deshacer.append(max(fin2 - inicio2 - COSTO_RELOJ_NS, 0))
    res["quitar_parada"] = (statistics.median(tiempos) / 1000, statistics.median(ds))
    res["deshacer"] = (statistics.median(tiempos_deshacer) / 1000, statistics.median(ds))

    tiempos, tiempos_reabrir = [], []
    with _SinRecolector():
        for e in base["cierres"]:
            e = sufijo(e, copia())
            inicio = time.perf_counter_ns()
            hecho = red.cerrar(e)
            fin = time.perf_counter_ns()
            _exigir(hecho, "cerrar")
            inicio2 = time.perf_counter_ns()
            hecho = red.reabrir(e)
            fin2 = time.perf_counter_ns()
            _exigir(hecho, "reabrir")
            # Deshace reabrir y cerrar: datos y pilas vuelven a quedar iguales.
            _exigir(red.deshacer() and red.deshacer(), "restaurar")
            tiempos.append(max(fin - inicio - COSTO_RELOJ_NS, 0))
            tiempos_reabrir.append(max(fin2 - inicio2 - COSTO_RELOJ_NS, 0))
    res["cerrar"] = (statistics.median(tiempos) / 1000, None)
    res["reabrir"] = (statistics.median(tiempos_reabrir) / 1000, None)
    return res


# operación -> (requisito, firma, esperado al replicar, extra, explicación)
_REPLICADA = [
    ("carga", "Carga", "Red(carpeta)", "O(n log n)", None,
     "Se multiplican todas las filas, así que crece T. Cota global O(T log T); aquí el eje "
     "es n = estaciones, que crece en la misma proporción que T. Cada punto es una sola "
     "medición (no una mediana): sirve para ver la tendencia, sin estimar su variabilidad."),
    ("estado", "R1", "estado(nombre)", "O(1)", "µs solo copia 1",
     "Tabla hash: con factor de carga acotado, más estaciones no cambian el costo promedio. "
     "Consultar solamente la copia 1 resulta más rápido (columna \"µs solo copia 1\"), lo que es "
     "compatible con una mejor localidad de memoria. También pueden influir la longitud de las "
     "claves (las otras copias agregan \" ~c\" y el hash recorre cada carácter) y las colisiones "
     "de las tablas hash, que no son idénticas; esta comparación no separa esos efectos."),
    ("autocompletar", "R2", "autocompletar(prefijo, 10)", "O(log n)", None,
     "Búsqueda binaria sobre más estaciones; k = 10 fijo. De 147 a 1.176 estaciones, "
     "log n pasa de 7,2 a 10,2: la subida es pequeña."),
    ("rango", "R3", "rango(desde, hasta)", "O(log n)", "m (mediana)",
     "desde y hasta son vecinos a 10 puestos en la lista ordenada de la réplica, así que "
     "m = 10 en todos los tamaños y solo crece la búsqueda binaria."),
    ("proximo_bus", "R4", "proximo_bus(estacion, ruta, hora)", "O(1)", "µs solo copia 1",
     "Es O(log h), y h (horas distintas del par) no cambia al copiar la red: ver la tabla "
     "de dimensiones. La búsqueda binaria es igual en todos los tamaños; lo que crece son "
     "las tablas hash que se consultan antes (estaciones, rutas y horarios). "
     "Consultar solamente la copia 1 resulta más rápido (columna \"µs solo copia 1\"), lo que es "
     "compatible con una mejor localidad de memoria. También pueden influir la longitud de las "
     "claves (las otras copias agregan \" ~c\" y el hash recorre cada carácter) y las colisiones "
     "de las tablas hash, que no son idénticas; esta comparación no separa esos efectos."),
    ("viaje", "R5 (informativo)", "viaje(origen, destino)", "O(1)", None,
     "Origen y destino siempre en la misma copia, y las rutas que pasan por ellos no "
     "cambian: los recorridos son del mismo largo. Puede variar algo por memoria, por la "
     "longitud de las claves y por las colisiones de las tablas hash."),
    ("ranking", "R6", "ranking(10)", "O(1)", None,
     "El ranking ya está ordenado: pedir 10 cuesta lo mismo con más estaciones. "
     "Que quede plano es la evidencia de que la consulta no depende de n."),
    ("recorrido", "R7", "recorrido(ruta)", "O(1)", "µs solo copia 1",
     "Es O(L), y el largo de cada ruta no cambia al copiar la red. "
     "Consultar solamente la copia 1 resulta más rápido (columna \"µs solo copia 1\"), lo que es "
     "compatible con una mejor localidad de memoria. También pueden influir la longitud de las "
     "claves (las otras copias agregan \" ~c\" y el hash recorre cada carácter) y las colisiones "
     "de las tablas hash, que no son idénticas; esta comparación no separa esos efectos."),
    ("quitar_parada", "R7 + R6", "quitar_parada(ruta, estacion)", "O(n)", "d (mediana)",
     "La lista doble se edita en O(1), pero el ranking es global y cuesta O(d + 1). Con "
     "más copias hay más estaciones con conteos de buses parecidos, así que una parada "
     "típica cruza más puestos: d crece en proporción a n (ver la columna d). El tiempo "
     "crece menos que n porque a estos tamaños d es pequeño (unas decenas) y pesa más el "
     "costo fijo de la edición; con redes más grandes la parte O(d) dominaría. Es la "
     "tensión entre R6 y R7, pendiente de lo que responda el profesor."),
    ("deshacer", "R9", "deshacer() de quitar_parada", "O(n)", "d (mediana)",
     "Sacar de la pila es O(1); el costo es volver a meter la parada, que mueve la "
     "estación los mismos d puestos. Crece menos que n por la misma razón que quitar."),
    ("cerrar", "R8", "cerrar(nombre)", "O(n)", None,
     "Corrimiento en el arreglo de abiertas y en el ranking: lineal en las estaciones."),
    ("reabrir", "R8", "reabrir(nombre)", "O(n)", None,
     "Búsqueda binaria de su lugar y corrimiento: lineal en las estaciones."),
]


def medir_red_replicada(carpeta_real=DATOS, avance=None):
    """Mide la red real copiada 1, 2, 4 y 8 veces.

    Devuelve (dimensiones, experimentos): dimensiones es una lista de filas
    {"Dimensión": ..., "×1": ..., "×2": ...}; experimentos tiene el mismo
    formato que el modo de escalamiento, con x = estaciones totales.
    """
    real = leer_red_real(carpeta_real)
    azar = random.Random(7)
    base = _muestras_base(real, azar)
    por_copias = {}
    dims = {}
    for i, c in enumerate(COPIAS):
        if avance:
            avance(i, len(COPIAS), c)
        with tempfile.TemporaryDirectory(prefix="r11_real_") as carpeta:
            filas = escribir_replica(carpeta, real, c)
            dims[c] = dimensiones(*filas)
            todos = sorted(f[0] for f in filas[0])
            # Una sola carga por tamaño: tarda segundos, así que el ruido pesa poco
            # y repetirla haría que el modo pasara del minuto.
            with _SinRecolector():
                inicio = time.perf_counter_ns()
                red = Red(carpeta)
                fin = time.perf_counter_ns()
        res = _medir_replica(red, base, c, azar, todos)
        res["carga"] = ((fin - inicio) / 1000, None)
        por_copias[c] = (len(filas[0]), res)
        del red
    tabla = []
    for nombre in dims[COPIAS[0]]:
        fila = {"Dimensión": nombre}
        for c in COPIAS:
            fila["×%d" % c] = dims[c][nombre]
        primero, ultimo = dims[COPIAS[0]][nombre], dims[COPIAS[-1]][nombre]
        fila["Al replicar"] = "Se multiplica" if ultimo != primero else "Queda igual"
        tabla.append(fila)
    experimentos = []
    for clave, req, firma, esperado, extra, explicacion in _REPLICADA:
        puntos = [(por_copias[c][0], por_copias[c][1][clave][0]) for c in COPIAS]
        r = dict(
            requisito=req, operacion=firma, variable="n = estaciones totales de la réplica",
            fijos="Copias ×1, ×2, ×4, ×8 de la red real; consultas al azar sobre datos reales",
            esperado=esperado, puntos=puntos, explicacion=explicacion,
        )
        if extra:
            r["extra"] = (extra, [por_copias[c][1][clave][1] for c in COPIAS])
        experimentos.append(r)
    return tabla, experimentos


def _imprimir(r, segundos=0.0):
    filas = " | ".join("%d: %.2f" % p for p in r["puntos"])
    if "extra" in r:
        filas += "   %s: %s" % (r["extra"][0], r["extra"][1])
    print("%-34s %-11s b=%.2f  (%.1fs)  %s" % (
        r["operacion"], r["esperado"], exponente(r["puntos"]), segundos, filas))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "replicada":
        inicio = time.perf_counter()
        tabla, exps = medir_red_replicada()
        for fila in tabla:
            print(fila)
        for r in exps:
            _imprimir(r)
        print("Total %.1fs" % (time.perf_counter() - inicio))
        sys.exit(0)
    for exp in EXPERIMENTOS:
        inicio = time.perf_counter()
        r = exp()
        _imprimir(r, time.perf_counter() - inicio)
