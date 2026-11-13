import streamlit as st
from datetime import datetime, timedelta, timezone
import csv
import math
import os
import pydeck as pdk
from motor import Red, simular_fila

st.set_page_config(page_title="Planeador TransMilenio", layout="wide")

st.title("🚌 Planeador de viajes TransMilenio")
st.caption("Proyecto final · Estructuras de datos y algoritmos")

ruta_datos = "datos"
if os.path.exists(ruta_datos):
    if "app_red" not in st.session_state:
        st.session_state["app_red"] = Red(ruta_datos)
    red = st.session_state["app_red"]
else:
    st.error(f"No se encuentra la carpeta de datos en '{ruta_datos}'.")
    st.stop()


def nombre(texto):
    # Las estaciones y rutas del motor están en mayúsculas ("PORTAL 80", "B74-1").
    return texto.strip().upper()


# R2 sin límite práctico: el buscador muestra todas las estaciones abiertas que
# empiezan por el texto. autocompletar se detiene sola al acabarse el prefijo.
K_SUGERENCIAS = 10**9
# Botones de sugerencias por fila.
POR_FILA = 4
# Con más de estas sugerencias van en un recuadro con scroll propio, para que no
# empujen la página hacia abajo (en celular cada botón ocupa una fila).
MAX_SIN_RECUADRO = 8
ALTO_BOTON, ESPACIO = 40, 16  # px aproximados de un botón y del espacio entre filas


def caja_sugerencias(cantidad, filas_visibles):
    """Recuadro con scroll que deja ver unas `filas_visibles` filas de botones
    (y media fila más, para que se note que hay más abajo), o un contenedor
    normal si son pocas sugerencias."""
    if cantidad <= MAX_SIN_RECUADRO:
        return st.container()
    alto = ESPACIO + filas_visibles * (ALTO_BOTON + ESPACIO) + ALTO_BOTON // 2
    return st.container(height=alto)


def elegir_estacion(nombre_estacion):
    st.session_state["estacion"] = nombre_estacion


def fijar(clave, valor):
    # Origen o destino del viaje: se escribe en su campo de texto, como si el
    # usuario lo hubiera tecleado.
    st.session_state["txt_" + clave] = valor


def campo_estacion(clave, etiqueta):
    """Campo con sugerencias en vivo (R2). Devuelve la estación si el texto es
    exactamente una estación de la red (R1), o None."""
    texto = st.text_input(etiqueta, type="search", live="150ms", key="txt_" + clave,
                          placeholder="Escribe y elige")
    if not texto:
        return None
    exacto = nombre(texto)
    estado = red.estado(exacto)
    if estado is not None:
        st.caption(f"✓ {exacto}" + (" (cerrada)" if estado == "cerrada" else ""))
        return exacto
    sugerencias = red.autocompletar(exacto, K_SUGERENCIAS)
    if not sugerencias:
        st.caption("Ninguna estación abierta empieza así.")
    caja = caja_sugerencias(len(sugerencias), 4)
    for i in range(0, len(sugerencias), 2):
        columnas = caja.columns(2)
        for col, sug in zip(columnas, sugerencias[i:i + 2]):
            col.button(sug, key=clave + "_sug_" + sug, on_click=fijar, args=(clave, sug),
                       use_container_width=True)
    return None


def hora_legible(hora):
    # Horas extendidas del GTFS (ver README, "Horas"): "25:10" es la 01:10 del día siguiente.
    h, m = hora.split(":")
    if int(h) >= 24:
        return f"{hora} ({int(h) - 24:02d}:{m} del día siguiente)"
    return hora


def hora_actual():
    # Hora de Bogotá (UTC-5, sin horario de verano) para no depender de tzdata en Windows.
    return datetime.now(timezone(timedelta(hours=-5))).time().replace(second=0, microsecond=0)



def ir(clave, vista):
    st.session_state[clave] = vista


def usar_en_viaje(clave, valor):
    # Desde la ficha de una estación: la pone en origen o destino y abre el viaje.
    fijar(clave, valor)
    ir("vista_consultas", "viaje")


def menu(clave, grupos):
    """Inicio de una pestaña: tarjetas de acción agrupadas. grupos es una lista
    de (título del grupo o None, opciones, tarjetas por fila). Devuelve la vista
    elegida, o None mientras se muestra el menú (con su botón para volver)."""
    vista = st.session_state.get(clave)
    if vista is not None:
        st.button("← Volver al menú", key="volver_" + clave, on_click=ir, args=(clave, None))
        return vista
    for titulo_grupo, opciones, por_fila in grupos:
        st.subheader(titulo_grupo or "¿Qué quieres hacer?")
        for i in range(0, len(opciones), por_fila):
            columnas = st.columns(por_fila)
            for col, (id_vista, titulo, detalle) in zip(columnas, opciones[i:i + por_fila]):
                with col.container(border=True):
                    st.markdown(f"#### {titulo}")
                    st.caption(detalle)
                    st.button("Abrir", key=f"abrir_{clave}_{id_vista}", on_click=ir,
                              args=(clave, id_vista), type="primary", use_container_width=True)
    return None


# Coordenadas de las estaciones: las genera conversion/convertir.py desde el GTFS
# (promedio de sus vagones). Solo las usa la app para el mapa; el motor no las lee.
RUTA_COORDENADAS = os.path.join("conversion", "generados", "coordenadas.csv")
NOTA_HORARIOS = "Horarios programados según el GTFS de TransMilenio de julio de 2021."
COLORES_TRAMO = [[200, 16, 46], [0, 114, 178], [0, 158, 115], [230, 159, 0], [204, 121, 167]]


@st.cache_data
def coordenadas():
    if not os.path.exists(RUTA_COORDENADAS):
        return {}
    with open(RUTA_COORDENADAS, encoding="utf-8") as f:
        return {fila["estacion"]: (float(fila["lat"]), float(fila["lon"]))
                for fila in csv.DictReader(f) if fila["lat"]}


def paradas_del_tramo(ruta, sube, baja):
    """Estaciones de la ruta desde `sube` hasta `baja`, en el orden en que las recorre (R7)."""
    camino = []
    for estacion in red.recorrido(ruta):
        if camino or estacion == sube:
            camino.append(estacion)
            if estacion == baja and len(camino) > 1:
                return camino
    return [sube, baja]


def mapa_viaje(tramos, clave):
    """Mapa con cada tramo de un color, y puntos en origen, transbordos y destino."""
    coord = coordenadas()
    caminos, puntos = [], []
    for n, (ruta, sube, baja) in enumerate(tramos):
        color = COLORES_TRAMO[n % len(COLORES_TRAMO)]
        estaciones = paradas_del_tramo(ruta, sube, baja)
        if any(e not in coord for e in estaciones):
            return  # sin coordenadas para alguna estación: no se dibuja nada
        caminos.append({"nombre": f"Ruta {ruta}: {sube} → {baja}", "color": color,
                        "camino": [[coord[e][1], coord[e][0]] for e in estaciones]})
        tipo = "Origen" if n == 0 else "Transbordo"
        puntos.append({"nombre": f"{tipo}: {sube}", "lat": coord[sube][0],
                       "lon": coord[sube][1], "color": color})
    destino = tramos[-1][2]
    puntos.append({"nombre": f"Destino: {destino}", "lat": coord[destino][0],
                   "lon": coord[destino][1], "color": [40, 40, 40]})
    # Encuadre: centro del recuadro que contiene el viaje y el zoom más cercano en
    # que cabe en unos 700 x 300 px (en Web Mercator, a zoom z un grado mide
    # 256·2^z/360 px; cerca del ecuador vale igual para latitud y longitud).
    lons = [p[0] for c in caminos for p in c["camino"]]
    lats = [p[1] for c in caminos for p in c["camino"]]
    ancho = max(max(lons) - min(lons), 0.005)
    alto = max(max(lats) - min(lats), 0.005)
    zoom = min(math.log2(700 * 360 / (256 * ancho)), math.log2(300 * 360 / (256 * alto)), 14)
    vista = pdk.ViewState(latitude=(min(lats) + max(lats)) / 2,
                          longitude=(min(lons) + max(lons)) / 2, zoom=zoom)
    capas = [
        pdk.Layer("PathLayer", caminos, get_path="camino", get_color="color",
                  width_min_pixels=5, pickable=True),
        pdk.Layer("ScatterplotLayer", puntos, get_position=["lon", "lat"],
                  get_fill_color="color", get_radius=120, radius_min_pixels=6,
                  stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=2,
                  pickable=True),
    ]
    st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=vista, map_style="light",
                             tooltip={"text": "{nombre}"}),
                    height=360, key="mapa_" + clave)
    st.caption("Posición de las estaciones según el GTFS de julio de 2021. Las líneas unen "
               "estaciones en orden; no siguen el trazado exacto de la vía.")


def mostrar_tramos(tramos, paradas, hora_txt, clave="principal"):
    """Pasos del viaje, cuántas paradas (las cuenta el motor) y transbordos, y
    con R4 cuándo pasa el bus del primer tramo."""
    for n, (ruta, sube, baja) in enumerate(tramos, 1):
        st.write(f"{n}. Toma la ruta **{ruta}** en **{sube}** y bájate en **{baja}**.")
    cambios = [baja for _, _, baja in tramos[:-1]]
    resumen = f"{paradas} paradas · "
    if not cambios:
        resumen += "sin transbordos"
    else:
        resumen += (f"{len(cambios)} transbordo" + ("s" if len(cambios) > 1 else "") + " en "
                    + ", ".join(cambios[:-1]) + (" y " if len(cambios) > 1 else "") + cambios[-1])
    st.caption(resumen + ".")
    ruta_1, sube_1 = tramos[0][0], tramos[0][1]
    bus_1 = red.proximo_bus(sube_1, ruta_1, hora_txt)
    if bus_1 is None:
        st.info(f"Próximo bus (R4): la ruta {ruta_1} en {sube_1} desde las "
                f"{hora_txt}: hoy este bus ya no se encuentra disponible.")
    else:
        st.success(f"Próximo bus (R4): la ruta {ruta_1} pasa por {sube_1} "
                   f"a las {hora_legible(bus_1)}.")
    st.caption(NOTA_HORARIOS)
    with st.expander("🗺️ Ver el viaje en el mapa", expanded=(clave == "principal")):
        mapa_viaje(tramos, clave)


# R10: pasajeros que caben en cada tipo de bus (sitio oficial de TransMilenio).
# En "Personalizado" se escriben los cupos libres, porque el bus puede llegar con gente.
TIPOS_BUS = {"Articulado (160 pasajeros)": 160, "Biarticulado (260 pasajeros)": 260,
             "Personalizado": None}


def caso_calle_100():
    # 3.862 validaciones entre las 17:00 y las 18:00 son unas 64 por minuto; la
    # F14-1 pasa cada 3 minutos (mediana en datos/horarios.csv).
    st.session_state["r10_ritmo"] = 64
    st.session_state["r10_pasajeros"] = 3862
    st.session_state["r10_frecuencia"] = 3


MENU_VIAJES = [
    ("viaje", "🧭 Planear un viaje", "De una estación a otra: directo o con un transbordo (R5), y alternativas con más transbordos."),
    ("proximo", "🕒 Próximo bus", "A qué hora pasa el siguiente bus de una ruta por una estación (R4)."),
]
MENU_ESTACIONES = [
    ("buscar", "🔍 Buscar una estación", "Sugerencias mientras escribes, estado, rutas que pasan y su próximo bus (R1, R2, R4)."),
    ("rango", "🔤 Estaciones en un rango", "Estaciones abiertas entre dos nombres, en orden alfabético (R3)."),
    ("ranking", "🏆 Ranking de estaciones", "Las estaciones con más buses al día (R6)."),
]
MENU_OPERAR = [
    ("r8", "🚧 Cerrar o reabrir", "Cierra una estación o vuelve a abrirla (R8)."),
    ("r7", "✏️ Editar una ruta", "Quita o agrega paradas y mira el recorrido (R7)."),
    ("r10", "⏱️ Simular fila", "Pasajeros por minuto y buses con cupo: cuánto espera cada uno en hora pico (R10)."),
]


tab1, tab2, tab3 = st.tabs(["🔍 Consultas", "⚙️ Operar red", "📊 Rendimiento (R11)"])

with tab1:
    vista = menu("vista_consultas", [("🚌 Viajes", MENU_VIAJES, 2),
                                      ("🚏 Estaciones", MENU_ESTACIONES, 3)])
    if vista == "buscar":
        st.header("Buscar una estación")

        # Un solo buscador: R2 sugiere mientras se escribe y R1 consulta el texto exacto
        # (una estación cerrada no aparece en las sugerencias, pero sí en la consulta exacta).
        texto = st.text_input("Escribe el nombre de una estación:", type="search",
                              live="150ms", placeholder="Ej. CAL", key="buscador")
        if texto:
            sugerencias = red.autocompletar(nombre(texto), K_SUGERENCIAS)
            if sugerencias:
                st.caption(("1 estación abierta empieza así (R2)" if len(sugerencias) == 1 else
                            f"{len(sugerencias)} estaciones abiertas empiezan así (R2), en orden alfabético"))
                caja = caja_sugerencias(len(sugerencias), 3)
                for i in range(0, len(sugerencias), POR_FILA):
                    columnas = caja.columns(POR_FILA)
                    for col, sug in zip(columnas, sugerencias[i:i + POR_FILA]):
                        col.button(sug, key="sug_" + sug, on_click=elegir_estacion, args=(sug,),
                                   use_container_width=True)
            else:
                st.caption("Ninguna estación abierta empieza así (R2).")
            if nombre(texto) in sugerencias:
                etiqueta_r1 = f"Consultar «{nombre(texto)}» exacto (R1)"
            else:
                # Las cerradas no salen en R2, pero R1 sí las encuentra por nombre exacto.
                etiqueta_r1 = f"¿No aparece? Buscar «{nombre(texto)}» aunque esté cerrada (R1)"
            st.button(etiqueta_r1, on_click=elegir_estacion, args=(nombre(texto),))

        elegida = st.session_state.get("estacion")
        if elegida:
            st.subheader(f"📍 {elegida}")
            estado = red.estado(elegida)
            if estado is None:
                st.warning("Esa estación no existe (R1).")
            else:
                if estado == "abierta":
                    st.success("Estado (R1): abierta")
                else:
                    st.error("Estado (R1): cerrada. Nadie sube, baja ni transborda aquí (R8).")
                rutas = red.rutas_de(elegida)
                st.write(f"Pasan {len(rutas)} rutas por aquí.")
                if rutas:
                    c1, c2, c3 = st.columns([2, 1, 1])
                    ruta_r4 = c1.selectbox("Ruta", rutas, key="ruta_r4")
                    hora_r4 = c2.time_input("Hora", value=hora_actual(), step=60, key="hora_r4")
                    c3.write("")
                    if c3.button("Próximo bus (R4)", use_container_width=True):
                        # El último resultado queda en session_state para que no se borre
                        # al tocar otro widget; se guarda con qué estación, ruta y hora se pidió.
                        hora_txt = hora_r4.strftime("%H:%M")
                        st.session_state["res_r4"] = {
                            "estacion": elegida, "ruta": ruta_r4, "hora": hora_txt,
                            "bus": red.proximo_bus(elegida, ruta_r4, hora_txt)}
                    res_r4 = st.session_state.get("res_r4")
                    if res_r4 and res_r4["estacion"] == elegida:
                        if res_r4["bus"] is None:
                            st.info(f"Ruta {res_r4['ruta']} desde las {res_r4['hora']}: "
                                    "hoy este bus ya no se encuentra disponible.")
                        else:
                            st.success(f"Ruta {res_r4['ruta']} desde las {res_r4['hora']}: "
                                       f"el próximo bus pasa a las {hora_legible(res_r4['bus'])}.")
                        st.caption(NOTA_HORARIOS)
                b1, b2 = st.columns(2)
                b1.button("Usar como origen del viaje (R5)", on_click=usar_en_viaje, args=("origen", elegida),
                          use_container_width=True)
                b2.button("Usar como destino del viaje (R5)", on_click=usar_en_viaje, args=("destino", elegida),
                          use_container_width=True)

    elif vista == "viaje":
        st.header("Planear un viaje (R5)")
        v1, v2 = st.columns(2)
        with v1:
            origen = campo_estacion("origen", "Origen:")
        with v2:
            destino = campo_estacion("destino", "Destino:")
        if origen and destino:
            # Una sola búsqueda por opción: el motor entrega tramos y total de paradas.
            r5 = red.viaje_y_paradas(origen, destino)
            cerradas = [e for e in (origen, destino) if red.estado(e) == "cerrada"]
            if cerradas:
                st.warning(f"{' y '.join(cerradas)} está cerrada: nadie sube ni baja ahí (R8).")
            elif origen == destino:
                st.info("Origen y destino son la misma estación.")
            else:
                principal = r5
                if r5 is None:
                    st.warning("No hay viaje directo ni con un solo transbordo entre esas "
                               "estaciones (R5).")
                    # Búsqueda aparte (no es R5). Se guarda solo qué par se pidió; los
                    # viajes se recalculan en cada vista para seguir cierres y ediciones.
                    st.button("Buscar con más transbordos", on_click=ir,
                              args=("mas_transbordos", (origen, destino)))
                    if st.session_state.get("mas_transbordos") == (origen, destino):
                        principal = red.viaje_con_transbordos(origen, destino)
                        if principal is None:
                            st.info("Tampoco hay forma de llegar con más transbordos.")
                if principal is not None:
                    hora_v = st.time_input("¿A qué hora sales?", value=hora_actual(), step=60,
                                           key="hora_viaje")
                    hora_txt = hora_v.strftime("%H:%M")
                    # Alternativa: menos paradas sin límite de transbordos (Dijkstra).
                    # Solo se muestra si de verdad ahorra paradas.
                    alterna = red.viaje_menos_paradas(origen, destino)
                    if alterna is not None and alterna[1] >= principal[1]:
                        alterna = None
                    if r5 is None:
                        st.markdown("**Con menos transbordos (BFS)**")
                    elif alterna is not None:
                        st.markdown("**Con hasta un transbordo (R5)**")
                    mostrar_tramos(principal[0], principal[1], hora_txt)
                    if alterna is not None:
                        ahorro = principal[1] - alterna[1]
                        extra = len(alterna[0]) - len(principal[0])
                        st.markdown(f"**Alternativa con menos paradas (Dijkstra):** {ahorro} "
                                    f"parada{'s' if ahorro > 1 else ''} menos, {extra} "
                                    f"transbordo{'s' if extra > 1 else ''} más.")
                        mostrar_tramos(alterna[0], alterna[1], hora_txt, "alterna")

    elif vista == "proximo":
        st.header("Próximo bus (R4)")
        est_r4 = campo_estacion("r4_estacion", "Estación:")
        if est_r4 is not None:
            if red.estado(est_r4) == "cerrada":
                st.warning(f"{est_r4} está cerrada: ningún bus para ahí (R8).")
            else:
                rutas_r4 = red.rutas_de(est_r4)
                if not rutas_r4:
                    st.info("Ninguna ruta pasa por esta estación.")
                else:
                    c1, c2 = st.columns([2, 1])
                    ruta_p = c1.selectbox("Ruta:", rutas_r4, key="r4_ruta")
                    hora_p = c2.time_input("Hora:", value=hora_actual(), step=60, key="r4_hora")
                    hora_p_txt = hora_p.strftime("%H:%M")
                    bus_p = red.proximo_bus(est_r4, ruta_p, hora_p_txt)
                    if bus_p is None:
                        st.info(f"Ruta {ruta_p} desde las {hora_p_txt}: hoy este bus ya no "
                                "se encuentra disponible.")
                    else:
                        st.success(f"Ruta {ruta_p} desde las {hora_p_txt}: el próximo bus pasa "
                                   f"por {est_r4} a las {hora_legible(bus_p)}.")
                    st.caption(NOTA_HORARIOS)

    elif vista == "rango":
        st.header("Estaciones en un rango (R3)")
        r1, r2 = st.columns(2)
        with r1:
            inf_r3 = campo_estacion("r3_desde", "Desde:")
        with r2:
            sup_r3 = campo_estacion("r3_hasta", "Hasta:")
        if st.button("Listar rango (R3)", disabled=not (inf_r3 and sup_r3)):
            st.session_state["res_r3"] = {
                "desde": inf_r3, "hasta": sup_r3, "estaciones": red.rango(inf_r3, sup_r3)}
        res_r3 = st.session_state.get("res_r3")
        if res_r3:
            estaciones_r3 = res_r3["estaciones"]
            if not estaciones_r3:
                st.info(f"No hay estaciones abiertas entre «{res_r3['desde']}» y «{res_r3['hasta']}».")
            else:
                st.caption(f"{len(estaciones_r3)} estaciones abiertas entre «{res_r3['desde']}» "
                           f"y «{res_r3['hasta']}», en orden alfabético:")
                # Con muchas estaciones la lista va en una caja con scroll.
                caja_r3 = st.container(height=300) if len(estaciones_r3) > 10 else st.container()
                caja_r3.markdown("\n".join(f"{n}. {est}" for n, est in enumerate(estaciones_r3, 1)))

    elif vista == "ranking":
        st.header("Ranking de estaciones con más buses (R6)")
        k_r6 = st.number_input("Cuántas (k):", min_value=1, value=10, step=1)
        if st.button("Ver ranking (R6)"):
            st.session_state["res_r6"] = {"k": int(k_r6), "ranking": red.ranking(int(k_r6))}
        res_r6 = st.session_state.get("res_r6")
        if res_r6:
            if not res_r6["ranking"]:
                st.info("No hay estaciones abiertas para el ranking.")
            else:
                st.caption(f"Top {res_r6['k']} de estaciones con más buses al día:")
                st.markdown("\n".join(f"{n}. {est}" for n, est in enumerate(res_r6["ranking"], 1)))

with tab2:
    import csv

    # Lista de rutas para el selector de R7: se lee una vez del CSV (es la app,
    # no el motor) y se guarda en la sesión.
    if "op_rutas" not in st.session_state:
        with open(os.path.join(ruta_datos, "rutas.csv"), encoding="utf-8", newline="") as f:
            st.session_state["op_rutas"] = sorted({fila["ruta"] for fila in csv.DictReader(f)})

    def operar(bloque, ok, exito, fallo):
        # El mensaje se guarda en la sesión para que sobreviva al rerun del clic.
        st.session_state["msg_operar"] = (bloque, ok, exito if ok else fallo)

    def mostrar_msg(bloque):
        msg = st.session_state.get("msg_operar")
        if msg is not None and msg[0] == bloque:
            del st.session_state["msg_operar"]
            if msg[1]:
                st.success(msg[2])
            else:
                st.warning(msg[2])

    def op_texto(clave):
        return nombre(st.session_state.get("txt_" + clave) or "")

    def op_cerrar():
        est = op_texto("op_estacion")
        operar("r8", red.cerrar(est), f"Estación {est} cerrada.",
               f"No se pudo cerrar {est or 'la estación'}: no existe o ya está cerrada.")

    def op_reabrir():
        est = op_texto("op_estacion")
        operar("r8", red.reabrir(est), f"Estación {est} reabierta.",
               f"No se pudo reabrir {est or 'la estación'}: no existe o ya está abierta.")

    def op_quitar():
        ruta = st.session_state["op_ruta"]
        parada = st.session_state.get("op_quitar_" + ruta)
        operar("r7", red.quitar_parada(ruta, parada), f"{parada} quitada de la ruta {ruta}.",
               f"No se pudo quitar la parada de la ruta {ruta}.")

    def op_agregar():
        ruta = st.session_state["op_ruta"]
        nueva = op_texto("op_nueva")
        despues = st.session_state.get("op_despues_" + ruta)
        operar("r7", red.agregar_parada(ruta, nueva, despues),
               f"{nueva} agregada a la ruta {ruta} después de {despues}.",
               f"No se pudo agregar {nueva or 'la estación'} a la ruta {ruta}: "
               "no es una estación de la red o ya está en la ruta.")

    def op_deshacer():
        operar("r9", red.deshacer(), "Última acción deshecha.", "No hay acciones para deshacer.")

    def op_rehacer():
        operar("r9", red.rehacer(), "Acción rehecha.", "No hay acciones para rehacer.")

    # R9 siempre a la vista: deshace o rehace cambios de R7 y de R8.
    with st.container(border=True):
        st.markdown("**Historial (R9)**: deshace o rehace el último cambio de rutas o estaciones.")
        col1, col2 = st.columns(2)
        col1.button("Deshacer (R9)", on_click=op_deshacer, use_container_width=True)
        col2.button("Rehacer (R9)", on_click=op_rehacer, use_container_width=True)
        mostrar_msg("r9")

    vista = menu("vista_operar", [(None, MENU_OPERAR, 3)])
    if vista == "r8":
        st.header("Cerrar o reabrir una estación (R8)")
        est_r8 = campo_estacion("op_estacion", "Estación:")
        if est_r8 is not None:
            st.markdown(f"Estado actual de **{est_r8}**: **{red.estado(est_r8)}**")
        col1, col2 = st.columns(2)
        col1.button("Cerrar estación (R8)", on_click=op_cerrar, disabled=est_r8 is None,
                    use_container_width=True)
        col2.button("Reabrir estación (R8)", on_click=op_reabrir, disabled=est_r8 is None,
                    use_container_width=True)
        mostrar_msg("r8")

    elif vista == "r7":
        st.header("Editar una ruta (R7)")
        ruta_r7 = st.selectbox("Ruta:", st.session_state["op_rutas"], key="op_ruta")
        paradas_r7 = red.recorrido(ruta_r7)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Quitar una parada**")
            st.selectbox("Parada a quitar:", paradas_r7, key="op_quitar_" + ruta_r7, filter_mode=None)
            st.button("Quitar parada (R7)", on_click=op_quitar, disabled=not paradas_r7,
                      use_container_width=True)
        with col2:
            st.markdown("**Agregar una parada**")
            nueva_r7 = campo_estacion("op_nueva", "Estación nueva:")
            st.selectbox("Después de:", paradas_r7, key="op_despues_" + ruta_r7, filter_mode=None)
            st.button("Agregar parada (R7)", on_click=op_agregar,
                      disabled=nueva_r7 is None or not paradas_r7, use_container_width=True)
        mostrar_msg("r7")

        al_reves_r7 = st.checkbox("Ver de vuelta (al revés)", key="op_al_reves")
        recorrido_r7 = red.recorrido(ruta_r7, al_reves=al_reves_r7)
        sentido = "de vuelta" if al_reves_r7 else "de ida"
        st.markdown(f"**Recorrido {sentido} de {ruta_r7}** ({len(recorrido_r7)} paradas):")
        if recorrido_r7:
            st.info(" → ".join(recorrido_r7))
        else:
            st.caption("La ruta no tiene paradas.")

    elif vista == "r10":
        st.header("Simular fila de abordaje (R10)")
        # Como pidió el profesor, las llegadas van a un ritmo fijo; en hora pico son
        # varios pasajeros por minuto. La app arma la lista de minutos de llegada
        # (con N por minuto: N veces 0, N veces 1, ...) y se la pasa al motor.
        # Valores iniciales en session_state (no en value=), porque el botón del caso
        # real los cambia por su clave.
        for clave_r10, inicial in (("r10_ritmo", 100), ("r10_pasajeros", 3000),
                                   ("r10_frecuencia", 3), ("r10_cupos", 160)):
            st.session_state.setdefault(clave_r10, inicial)
        st.button("📍 Caso real: Calle 100, 17:00–18:00 (julio de 2021)", on_click=caso_calle_100)
        st.caption("Ese miércoles 14 de julio de 2021 hubo 3.862 validaciones en Calle 100 entre "
                   "las 17:00 y las 18:00 (unos 64 por minuto), y la ruta F14-1 pasa por ahí cada "
                   "3 minutos en esa hora. Ojo: las validaciones cuentan todas las entradas a la "
                   "estación, no solo los pasajeros de una ruta.")
        c1, c2 = st.columns(2)
        ritmo_r10 = c1.number_input("Llegan pasajeros por minuto:", min_value=1,
                                    max_value=10_000, step=1, key="r10_ritmo")
        pas_r10 = c2.number_input("Cantidad de pasajeros:", min_value=1, max_value=1_000_000,
                                  step=1, key="r10_pasajeros")
        c3, c4, c5 = st.columns(3)
        freq_r10 = c3.number_input("Sale un bus cada (minutos, el primero en el minuto 0):",
                                   min_value=1, max_value=1440, step=1, key="r10_frecuencia")
        # Capacidad del sitio oficial de TransMilenio: articulado ~160, biarticulado ~260.
        tipo_r10 = c4.selectbox("Tipo de bus:", list(TIPOS_BUS), key="r10_tipo", filter_mode=None)
        if TIPOS_BUS[tipo_r10] is None:
            # El bus puede llegar con gente: aquí se dan los cupos que quedan libres.
            cap_r10 = c5.number_input("Cupos disponibles por bus:", min_value=1,
                                      max_value=1000, step=1, key="r10_cupos")
        else:
            cap_r10 = TIPOS_BUS[tipo_r10]
            c5.metric("Pasajeros por bus", cap_r10)
        if st.button("Simular fila (R10)"):
            llegadas_r10 = [i // int(ritmo_r10) for i in range(int(pas_r10))]
            st.session_state["res_r10"] = {
                "ritmo": int(ritmo_r10), "pasajeros": int(pas_r10),
                "frecuencia": int(freq_r10), "capacidad": int(cap_r10),
                "esperas": simular_fila(llegadas_r10, int(freq_r10), int(cap_r10))}
        res_r10 = st.session_state.get("res_r10")
        if res_r10:
            esperas = res_r10["esperas"]
            p = res_r10["pasajeros"]
            st.caption(f"{p} pasajeros, {res_r10['ritmo']} por minuto · bus cada "
                       f"{res_r10['frecuencia']} min con cupo para {res_r10['capacidad']} pasajero"
                       f"{'s' if res_r10['capacidad'] > 1 else ''}.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Espera promedio", f"{sum(esperas) / p:.2f} min")
            m2.metric("Espera máxima", f"{max(esperas)} min")
            m3.metric("Espera del último pasajero", f"{esperas[-1]} min")
            # Si los buses se llevan menos gente de la que llega, la fila crece.
            if res_r10["capacidad"] < res_r10["ritmo"] * res_r10["frecuencia"]:
                st.warning("Llegan más pasajeros de los que caben en los buses: la fila crece "
                           "y la espera aumenta con cada pasajero.")
            if p <= 20:
                st.write("Espera de cada pasajero, en orden de llegada (minutos):",
                         ", ".join(str(e) for e in esperas))
            else:
                # Muestra repartida a lo largo de la fila: así se ve cómo crece la espera.
                puestos = [1 + (p - 1) * j // 9 for j in range(10)]
                st.write("Espera según el puesto de llegada:")
                st.table({"Pasajero n.º": puestos,
                          "Espera (min)": [esperas[n - 1] for n in puestos]})


with tab3:
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
