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

from motor import Red

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
]


if __name__ == "__main__":
    for exp in EXPERIMENTOS:
        inicio = time.perf_counter()
        r = exp()
        filas = " | ".join("%d: %.2f" % p for p in r["puntos"])
        print("%-34s %-11s b=%.2f  (%.1fs)  %s" % (
            r["operacion"], r["esperado"], exponente(r["puntos"]),
            time.perf_counter() - inicio, filas))
