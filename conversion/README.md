# Conversión GTFS → CSV

`convertir.py` lee el GTFS estático de TransMilenio del 14 de julio de 2021 y genera los tres CSV que usa el motor:

- `estaciones.csv`: nombre
- `rutas.csv`: ruta, orden, estacion
- `horarios.csv`: ruta, estacion, hora

## Qué hay en cada carpeta

| Carpeta | Origen y uso |
|---|---|
| `datos/` | CSV entregados por el profesor. Los usan la app y las pruebas. |
| `conversion/generados/` | CSV producidos por `convertir.py`. Es el entregable reproducible, con sus diferencias documentadas abajo. |

Para regenerarlos:

```
python conversion/convertir.py GTFS-2021-07-14.zip conversion/generados --comparar datos
```

## De dónde sale el GTFS

"GTFS Estático 2021-07-14" de la Secretaría Distrital de Movilidad (fuente TransMilenio, licencia CC-BY):
https://datos.movilidadbogota.gov.co/datasets/6def68cda70c43ab8d93d74f43c5915a/about

Se descarga como `GTFS-2021-07-14.zip` (unos 57 MB). No se sube al repositorio por su tamaño, y no hay que descomprimirlo.

## Cómo correrlo

Desde la raíz del repositorio:

```
python conversion/convertir.py GTFS-2021-07-14.zip salida
python conversion/convertir.py GTFS-2021-07-14.zip salida --comparar datos
```

La segunda forma compara lo generado con los CSV de `datos/` (los que entregó el profesor). Tarda unos 10 segundos.

## Reglas

Están explicadas al inicio de `convertir.py`. En resumen:

1. Solo rutas troncales y viajes de un día hábil (los servicios que operan el lunes en `calendar.txt`).
2. Estación = nombre de la parada sin el vagón ni la plataforma, en mayúsculas y sin tildes ("Av. Jiménez A - 2 ó 5" → "AV. JIMENEZ").
3. Cada ruta del GTFS se separa en variantes, una por cada secuencia distinta de estaciones con al menos 3 viajes. Las que son solo un tramo de otra, se saltan paradas con muchos menos viajes, o son la misma vuelta empezando en otra parada, se juntan con la variante que las contiene.
4. Las variantes se numeran por viajes, de más a menos ("B74-1", "B74-2"…). Una ruta con una sola variante queda sin sufijo ("B52").
5. Una fila de horarios por cada parada de cada viaje, con la hora en "HH:MM". No se quitan repetidas, porque el motor las cuenta como buses en R6. Las horas extendidas del GTFS se conservan: 25:10:00 queda como 25:10 (la 01:10 del día siguiente dentro del mismo día de servicio; ver "Horas" en el README principal). El GTFS de 2021-07-14 no trae ninguna.

## Resultado comparado con los CSV del profesor

| Archivo | Generadas | Profesor | Diferencias |
|---|---|---|---|
| `estaciones.csv` | 147 | 147 | ninguna |
| `rutas.csv` | 1.927 | 1.927 | ninguna (las 181 rutas con el mismo nombre y las mismas paradas en el mismo orden) |
| `horarios.csv` | 140.528 | 140.492 | 36 filas de más (0,03 %), 0 de menos |

Las 36 filas de más vienen de 7 viajes atípicos (1 o 2 viajes en su secuencia, en las rutas B44, E32, F32 y K10) que el profesor no incluyó y que nuestra regla asigna a una variante. No encontramos una regla general que los descarte sin descartar también otros viajes atípicos que el profesor sí incluyó, así que se dejan documentados.

No se agregó una lista de excepciones para borrar esos siete viajes: igualar el archivo a la fuerza no es una regla de conversión.

Las reglas se dedujeron comparando el GTFS con los CSV del profesor; no tenemos su script. Son decisiones nuestras y así se presentan.

## El motor con los CSV generados

`pruebas/test_generados.py` carga `Red("conversion/generados")` y comprueba:

- estaciones, `estado`, `autocompletar` y `recorrido` (ida y vuelta) de las 181 rutas: iguales que con `datos/`;
- `viaje` en 400 pares al azar: igual que con `datos/` (R5 solo depende de rutas y estaciones);
- `proximo_bus` en 3.000 consultas y el ranking completo: iguales a un cálculo a lo bruto sobre `conversion/generados/horarios.csv`.

Con las 36 filas de más, el top 10 del ranking no cambia y solo 4 estaciones cambian de puesto.
