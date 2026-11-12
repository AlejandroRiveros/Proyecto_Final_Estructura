import streamlit as st
from datetime import datetime, timedelta, timezone
import os
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


def menu(clave, opciones, por_fila):
    """Inicio de una pestaña: una tarjeta por acción. Devuelve la vista elegida,
    o None mientras se muestra el menú (con su botón para volver)."""
    vista = st.session_state.get(clave)
    if vista is not None:
        st.button("← Volver al menú", key="volver_" + clave, on_click=ir, args=(clave, None))
        return vista
    st.markdown("**¿Qué quieres hacer?**")
    for i in range(0, len(opciones), por_fila):
        columnas = st.columns(por_fila)
        for col, (id_vista, titulo, detalle) in zip(columnas, opciones[i:i + por_fila]):
            with col.container(border=True):
                st.markdown(f"#### {titulo}")
                st.caption(detalle)
                st.button("Abrir", key=f"abrir_{clave}_{id_vista}", on_click=ir,
                          args=(clave, id_vista), type="primary", use_container_width=True)
    return None


def paradas_de(tramos):
    # Solo para mostrar: la app puede usar .index sobre el recorrido.
    total = 0
    for ruta, sube, baja in tramos:
        recorrido = red.recorrido(ruta)
        total += recorrido.index(baja) - recorrido.index(sube)
    return total


def mostrar_tramos(tramos, hora_txt):
    """Pasos del viaje, cuántas paradas y transbordos, y con R4 cuándo pasa
    el bus del primer tramo."""
    for n, (ruta, sube, baja) in enumerate(tramos, 1):
        st.write(f"{n}. Toma la ruta **{ruta}** en **{sube}** y bájate en **{baja}**.")
    cambios = [baja for _, _, baja in tramos[:-1]]
    resumen = f"{paradas_de(tramos)} paradas · "
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


MENU_CONSULTAS = [
    ("buscar", "🔍 Buscar una estación", "Sugerencias mientras escribes, estado, rutas y próximo bus (R1, R2, R4)."),
    ("viaje", "🧭 Planear un viaje", "De una estación a otra, directo o con un transbordo (R5)."),
    ("rango", "🔤 Estaciones en un rango", "Estaciones abiertas entre dos nombres, en orden alfabético (R3)."),
    ("ranking", "🏆 Ranking de estaciones", "Las estaciones con más buses al día (R6)."),
]
MENU_OPERAR = [
    ("r8", "🚧 Cerrar o reabrir", "Cierra una estación o vuelve a abrirla (R8)."),
    ("r7", "✏️ Editar una ruta", "Quita o agrega paradas y mira el recorrido (R7)."),
    ("r10", "⏱️ Simular fila", "Esperas de los pasajeros en hora pico (R10)."),
]


tab1, tab2, tab3 = st.tabs(["🔍 Consultas", "⚙️ Operar red", "📊 Rendimiento (R11)"])

with tab1:
    vista = menu("vista_consultas", MENU_CONSULTAS, 2)
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
            tramos = red.viaje(origen, destino)
            cerradas = [e for e in (origen, destino) if red.estado(e) == "cerrada"]
            if cerradas:
                st.warning(f"{' y '.join(cerradas)} está cerrada: nadie sube ni baja ahí (R8).")
            elif origen == destino:
                st.info("Origen y destino son la misma estación.")
            else:
                principal = tramos
                if tramos is None:
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
                    if alterna is not None and paradas_de(alterna) >= paradas_de(principal):
                        alterna = None
                    if tramos is None:
                        st.markdown("**Con menos transbordos (BFS)**")
                    elif alterna is not None:
                        st.markdown("**Con hasta un transbordo (R5)**")
                    mostrar_tramos(principal, hora_txt)
                    if alterna is not None:
                        ahorro = paradas_de(principal) - paradas_de(alterna)
                        extra = len(alterna) - len(principal)
                        st.markdown(f"**Alternativa con menos paradas (Dijkstra):** {ahorro} "
                                    f"parada{'s' if ahorro > 1 else ''} menos, {extra} "
                                    f"transbordo{'s' if extra > 1 else ''} más.")
                        mostrar_tramos(alterna, hora_txt)

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

    vista = menu("vista_operar", MENU_OPERAR, 3)
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
        lleg_r10 = st.text_input("Minuto de llegada de cada pasajero (separados por coma):", value="0, 1, 1, 4")
        freq_r10 = st.number_input("Frecuencia (minutos entre buses, el primero sale en el minuto 0):", min_value=1, value=2)
        cap_r10 = st.number_input("Capacidad de cada bus:", min_value=1, value=1)
        if st.button("Simular fila (R10)"):
            try:
                llegadas_r10 = [int(x) for x in lleg_r10.replace(" ", "").split(",") if x != ""]
            except ValueError:
                llegadas_r10 = None
            st.session_state["res_r10"] = {
                "frecuencia": int(freq_r10), "capacidad": int(cap_r10),
                "esperas": (None if llegadas_r10 is None else
                            simular_fila(llegadas_r10, int(freq_r10), int(cap_r10)))}
        res_r10 = st.session_state.get("res_r10")
        if res_r10:
            esperas = res_r10["esperas"]
            if esperas is None:
                st.warning("Escribe minutos enteros separados por coma, por ejemplo 0, 1, 1, 4.")
            elif not esperas:
                st.info("No hay pasajeros.")
            else:
                st.caption(f"Bus cada {res_r10['frecuencia']} min con capacidad {res_r10['capacidad']}.")
                st.write("Espera de cada pasajero, en orden de llegada (minutos):",
                         ", ".join(str(e) for e in esperas))
                st.write(f"Espera promedio: {sum(esperas) / len(esperas):.2f} min · máxima: {max(esperas)} min")



with tab3:
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
