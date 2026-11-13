"""Conversión del GTFS de TransMilenio (2021-07-14) a los tres CSV del motor.

Uso (desde la raíz del repositorio):

    python conversion/convertir.py GTFS-2021-07-14.zip carpeta_salida
    python conversion/convertir.py GTFS-2021-07-14.zip carpeta_salida --comparar datos

Lee el .zip directamente (no hay que descomprimirlo) y escribe en carpeta_salida
estaciones.csv, rutas.csv y horarios.csv. Con --comparar, además compara el
resultado con otra carpeta de CSV (por ejemplo, los que entregó el profesor).
También escribe coordenadas.csv (estacion, lat, lon), que usa solo la app para
dibujar el mapa del viaje; el motor no lo lee.

Este archivo está fuera de motor/, así que aquí se usan pandas, dict y set.

Reglas de la conversión (deducidas comparando con los CSV del profesor):
1. Solo rutas troncales (route_desc = TRONCAL) y solo los viajes de un día
   hábil: los servicios que operan el lunes según calendar.txt.
2. Estación = nombre de la parada sin el sufijo del vagón o la plataforma
   ("Av. Jiménez A - 2 ó 5" -> "AV. JIMENEZ", "Portal 80 T-1A" -> "PORTAL 80"),
   en mayúsculas, sin tildes ni "º".
3. Cada viaje se convierte en su secuencia de estaciones (por stop_sequence).
   Si dos paradas seguidas son la misma estación (dos vagones), se deja la primera.
4. Una ruta del GTFS (route_short_name, p. ej. "B74") puede tener varias
   secuencias distintas: cada una es una variante. Se conserva una variante si
   tiene al menos 3 viajes y no la "absorbe" otra. Una variante v es absorbida
   por w si:
   - v es un tramo seguido de w (un viaje que hace solo parte del recorrido), o
   - v es w saltándose paradas y tiene menos de la mitad de los viajes de w, o
   - v es una rotación de w (el mismo ciclo empezando en otra parada) con menos viajes.
5. Cada viaje se asigna a su variante; si la suya no se conservó, a la variante
   conservada más corta que la contiene, y si ninguna la contiene, a la que
   comparte más estaciones con ella. Del viaje solo se guardan las paradas que
   están en la variante asignada.
6. Las variantes de una ruta se numeran por viajes asignados, de más a menos
   (en empate, la de más viajes propios y luego la primera en trips.txt):
   "B74-1", "B74-2"... Si la ruta tiene una sola variante, queda sin sufijo ("B52").
7. horarios.csv tiene una fila por cada parada de cada viaje, con la hora de
   salida en "HH:MM" (los segundos se descartan). No se quitan repetidas: el
   motor las cuenta como buses (R6) y las deduplica solo para R4. Las horas
   extendidas del GTFS se conservan (25:10:00 -> "25:10", la 01:10 del día
   siguiente dentro del mismo día de servicio): así se ordenan después de las
   23:59 y siguen contando en R6. El GTFS de 2021-07-14 no trae ninguna.
8. coordenadas.csv: la posición de cada estación es el promedio de stop_lat y
   stop_lon de sus paradas (vagones y plataformas) que usan los viajes troncales
   elegidos. Así no entran paraderos zonales que tienen el mismo nombre.
"""

import argparse
import io
import os
import re
import sys
import unicodedata
import zipfile
from collections import Counter

import pandas as pd

MINIMO_VIAJES = 3
FACTOR_SALTOS = 2


def nombre_estacion(nombre_parada):
    """'Av. Jiménez A - 2 ó 5' -> 'AV. JIMENEZ'; 'Portal 80 T-1A' -> 'PORTAL 80'."""
    n = re.sub(r"\s+([A-F]\s*-\s*\S.*|T-?\d+[A-Z]?(\s+[A-Z])?)$", "", nombre_parada.strip())
    n = n.replace("º", "")
    n = "".join(c for c in unicodedata.normalize("NFD", n) if unicodedata.category(c) != "Mn")
    return n.upper().strip()


def _leer(z, archivo, **kw):
    with z.open(archivo) as f:
        return pd.read_csv(io.TextIOWrapper(f, encoding="utf-8-sig"), dtype=str, **kw)


def _es_tramo(v, w):
    n = len(v)
    return any(w[i:i + n] == v for i in range(len(w) - n + 1))


def _es_subsecuencia(v, w):
    resto = iter(w)
    return all(x in resto for x in v)


def _es_rotacion(v, w):
    return len(v) == len(w) and v != w and _es_tramo(v, w + w)


def _absorbe(w, v, viajes):
    """True si la variante w absorbe a v (regla 4)."""
    return (_es_tramo(v, w)
            or (_es_subsecuencia(v, w) and viajes[v] * FACTOR_SALTOS < viajes[w])
            or (_es_rotacion(v, w) and viajes[v] < viajes[w]))


def _sin_repetidas_seguidas(secuencia):
    salida = []
    for x in secuencia:
        if not salida or salida[-1] != x:
            salida.append(x)
    return tuple(salida)


def convertir(ruta_zip):
    """Devuelve (estaciones, rutas, horarios, coordenadas) como DataFrames."""
    z = zipfile.ZipFile(ruta_zip)
    routes = _leer(z, "routes.txt")
    troncales = routes[routes.route_desc == "TRONCAL"][["route_id", "route_short_name"]]
    calendar = _leer(z, "calendar.txt")
    habiles = set(calendar[calendar.monday == "1"].service_id)
    trips = _leer(z, "trips.txt")
    trips = trips[trips.service_id.isin(habiles)].merge(troncales, on="route_id")
    ids = set(trips.trip_id)

    stops = _leer(z, "stops.txt")
    estacion_de = dict(zip(stops.stop_id, stops.stop_name.map(nombre_estacion)))

    # stop_times pesa ~300 MB: se lee por partes y solo se guardan los viajes elegidos.
    partes = []
    with z.open("stop_times.txt") as f:
        lector = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8-sig"), dtype=str,
                             usecols=["trip_id", "departure_time", "stop_id", "stop_sequence"],
                             chunksize=500_000)
        for parte in lector:
            partes.append(parte[parte.trip_id.isin(ids)])
    st = pd.concat(partes)
    st["orden"] = st.stop_sequence.astype(int)
    st["estacion"] = st.stop_id.map(estacion_de)
    st = st.sort_values(["trip_id", "orden"])
    # Regla 3: dos vagones seguidos de la misma estación cuentan una vez (el primero).
    st = st[st.estacion != st.groupby("trip_id").estacion.shift(1)]
    secuencia = st.groupby("trip_id").estacion.apply(tuple)
    trips = trips.set_index("trip_id")
    trips["secuencia"] = secuencia.map(_sin_repetidas_seguidas)

    filas_rutas = []
    asignacion = {}  # trip_id -> (nombre de la variante, set de sus estaciones)
    for corto, grupo in trips.groupby("route_short_name"):
        viajes = grupo.secuencia.value_counts().to_dict()
        conservadas = [v for v in viajes
                       if viajes[v] >= MINIMO_VIAJES
                       and not any(w != v and _absorbe(w, v, viajes) for w in viajes)]
        destino = {}
        for v in viajes:
            if v in conservadas:
                destino[v] = v
                continue
            contienen = [w for w in conservadas if _absorbe(w, v, viajes) or _es_subsecuencia(v, w)]
            if contienen:
                destino[v] = min(contienen, key=lambda w: (len(w), -viajes[w]))
            else:
                destino[v] = max(conservadas, key=lambda w: (len(set(v) & set(w)), viajes[w]))
        total = Counter()
        for v, n in viajes.items():
            total[destino[v]] += n
        # Empate: primero la que tenía más viajes propios y, si siguen empatadas,
        # la que aparece primero en trips.txt.
        aparece = {}
        for v in grupo.secuencia:
            aparece.setdefault(v, len(aparece))
        orden = sorted(conservadas, key=lambda w: (-total[w], -viajes[w], aparece[w]))
        nombres = {w: (corto if len(orden) == 1 else "%s-%d" % (corto, i + 1)) for i, w in enumerate(orden)}
        for w in orden:
            for i, e in enumerate(w):
                filas_rutas.append((nombres[w], i + 1, e))
        for trip_id, v in grupo.secuencia.items():
            w = destino[v]
            asignacion[trip_id] = (nombres[w], set(w))

    st["ruta"] = st.trip_id.map(lambda t: asignacion[t][0])
    st = st[[e in asignacion[t][1] for t, e in zip(st.trip_id, st.estacion)]]
    st["hora"] = st.departure_time.str[:5]
    inicio = st.groupby("trip_id").hora.transform("min")
    st = st.assign(inicio=inicio).sort_values(["ruta", "inicio", "trip_id", "orden"])
    horarios = st[["ruta", "estacion", "hora"]]

    rutas = pd.DataFrame(filas_rutas, columns=["ruta", "orden", "estacion"]).sort_values(["ruta", "orden"])
    estaciones = pd.DataFrame({"nombre": sorted(set(rutas.estacion))})

    # Regla 8: solo las paradas que usan los viajes troncales elegidos.
    usadas = stops[stops.stop_id.isin(set(st.stop_id))].copy()
    usadas["estacion"] = usadas.stop_id.map(estacion_de)
    usadas["lat"] = usadas.stop_lat.astype(float)
    usadas["lon"] = usadas.stop_lon.astype(float)
    coordenadas = (usadas.groupby("estacion")[["lat", "lon"]].mean().round(6)
                   .reindex(estaciones.nombre).rename_axis("estacion").reset_index())
    return estaciones, rutas, horarios, coordenadas


def comparar(salida, referencia):
    """Compara los CSV generados con otra carpeta y devuelve un resumen en texto."""
    lineas = []
    for archivo, columnas in (("estaciones.csv", ["nombre"]),
                              ("rutas.csv", ["ruta", "orden", "estacion"]),
                              ("horarios.csv", ["ruta", "estacion", "hora"])):
        a = pd.read_csv(os.path.join(salida, archivo), dtype=str)[columnas]
        b = pd.read_csv(os.path.join(referencia, archivo), dtype=str)[columnas]
        ca = Counter(map(tuple, a.values.tolist()))
        cb = Counter(map(tuple, b.values.tolist()))
        sobran, faltan = ca - cb, cb - ca
        lineas.append("%-15s generadas %7d | referencia %7d | sobran %d | faltan %d" % (
            archivo, len(a), len(b), sum(sobran.values()), sum(faltan.values())))
        for fila, n in list(sobran.items())[:3]:
            lineas.append("    sobra %s x%d" % (fila, n))
        for fila, n in list(faltan.items())[:3]:
            lineas.append("    falta %s x%d" % (fila, n))
    return "\n".join(lineas)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("gtfs_zip")
    p.add_argument("salida")
    p.add_argument("--comparar", metavar="CARPETA", help="carpeta con CSV de referencia")
    args = p.parse_args(argv)
    estaciones, rutas, horarios, coordenadas = convertir(args.gtfs_zip)
    os.makedirs(args.salida, exist_ok=True)
    estaciones.to_csv(os.path.join(args.salida, "estaciones.csv"), index=False)
    rutas.to_csv(os.path.join(args.salida, "rutas.csv"), index=False)
    horarios.to_csv(os.path.join(args.salida, "horarios.csv"), index=False)
    coordenadas.to_csv(os.path.join(args.salida, "coordenadas.csv"), index=False)
    print("Escrito en %s: %d estaciones, %d rutas (%d paradas), %d horarios" % (
        args.salida, len(estaciones), rutas.ruta.nunique(), len(rutas), len(horarios)))
    if args.comparar:
        print(comparar(args.salida, args.comparar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
