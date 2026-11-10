import streamlit as st
from datetime import datetime, timedelta, timezone
import os
from motor import Red, simular_fila

st.set_page_config(page_title="Planeador TransMilenio", layout="wide")

st.title("🚌 Planeador de Viajes TransMilenio - Motor EDA")

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


def elegir_estacion(nombre_estacion):
    st.session_state["estacion"] = nombre_estacion


def fijar(clave, valor):
    st.session_state[clave] = valor


def hora_actual():
    # Hora de Bogotá (UTC-5, sin horario de verano) para no depender de tzdata en Windows.
    return datetime.now(timezone(timedelta(hours=-5))).time().replace(second=0, microsecond=0)



tab1, tab2, tab3 = st.tabs(["🔍 Consultas y Viajes", "⚙️ Operar Red", "📊 Panel de Rendimiento (R11)"])

with tab1:
    st.header("Buscar una estación")

    # Un solo buscador: R2 sugiere mientras se escribe y R1 consulta el texto exacto
    # (una estación cerrada no aparece en las sugerencias, pero sí en la consulta exacta).
    texto = st.text_input("Escribe el nombre de una estación:", type="search",
                          live="150ms", placeholder="Ej. CAL", key="buscador")
    if texto:
        sugerencias = red.autocompletar(nombre(texto), K_SUGERENCIAS)
        if sugerencias:
            st.caption(f"{len(sugerencias)} estaciones abiertas empiezan así (R2), en orden alfabético")
            for i in range(0, len(sugerencias), POR_FILA):
                columnas = st.columns(POR_FILA)
                for col, sug in zip(columnas, sugerencias[i:i + POR_FILA]):
                    col.button(sug, key="sug_" + sug, on_click=elegir_estacion, args=(sug,),
                               use_container_width=True)
        else:
            st.caption("Ninguna estación abierta empieza así (R2).")
        st.button(f"Consultar «{nombre(texto)}» exacto (R1)", on_click=elegir_estacion,
                  args=(nombre(texto),))

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
                    bus = red.proximo_bus(elegida, ruta_r4, hora_r4.strftime("%H:%M"))
                    if bus is None:
                        st.info("Hoy este bus ya no se encuentra disponible")
                    else:
                        st.success(f"El próximo {ruta_r4} pasa a las {bus}.")
            b1, b2 = st.columns(2)
            b1.button("Usar como origen del viaje (R5)", on_click=fijar, args=("origen", elegida),
                      use_container_width=True)
            b2.button("Usar como destino del viaje (R5)", on_click=fijar, args=("destino", elegida),
                      use_container_width=True)

    st.divider()
    st.header("Planear un viaje (R5)")
    origen = st.session_state.get("origen")
    destino = st.session_state.get("destino")
    v1, v2 = st.columns(2)
    v1.metric("Origen", origen or "—")
    v2.metric("Destino", destino or "—")
    st.caption("Busca una estación arriba y usa los botones de origen y destino.")
    if origen and destino:
        tramos = red.viaje(origen, destino)
        if tramos is None:
            st.warning("No hay viaje directo ni con un solo transbordo entre esas estaciones.")
        else:
            for n, (ruta, sube, baja) in enumerate(tramos, 1):
                st.write(f"{n}. Toma la ruta **{ruta}** en **{sube}** y bájate en **{baja}**.")
            if len(tramos) == 2:
                st.caption(f"Transbordo en {tramos[0][2]}.")

    st.divider()
    st.header("Otras consultas")

    st.subheader("Estaciones en un rango (R3)")
    r1, r2 = st.columns(2)
    inf_r3 = r1.text_input("Desde:", placeholder="Ej. CALLE 26")
    sup_r3 = r2.text_input("Hasta:", placeholder="Ej. CALLE 80")
    if st.button("Listar rango (R3)"):
        st.write(red.rango(nombre(inf_r3), nombre(sup_r3)))

    st.subheader("Ranking de estaciones con más buses (R6)")
    k_r6 = st.number_input("Cuántas (k):", min_value=1, value=10, step=1)
    if st.button("Ver ranking (R6)"):
        for n, est in enumerate(red.ranking(int(k_r6)), 1):
            st.write(f"{n}. {est}")

with tab2:
    st.header("Operaciones de la Red")

    estacion_id = nombre(st.text_input("Estación:"))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cerrar Estación"):
            if red.cerrar(estacion_id):
                st.success("Estación cerrada con éxito.")
            else:
                st.warning("No se pudo realizar la acción (la estación no existe o el estado no es válido).")

        if st.button("Reabrir Estación (R8)"):
            if red.reabrir(estacion_id):
                st.success("Estación reabierta con éxito.")
            else:
                st.warning("No se pudo realizar la acción.")

        ruta_r7 = nombre(st.text_input("Ruta para agregar/quitar parada:"))
        despues_r7 = nombre(st.text_input("Agregarla después de la estación:"))
        if st.button("Agregar Parada (R7)"):
            if red.agregar_parada(ruta_r7, estacion_id, despues_r7):
                st.success("Parada agregada con éxito.")
            else:
                st.warning("No se pudo realizar la acción.")

    with col2:
        if st.button("Quitar Parada (R7)"):
            if red.quitar_parada(ruta_r7, estacion_id):
                st.success("Parada quitada con éxito.")
            else:
                st.warning("No se pudo realizar la acción.")

        if st.button("Deshacer última acción"):
            if red.deshacer():
                st.success("Acción deshecha con éxito.")
            else:
                st.warning("No hay acciones para deshacer.")

        if st.button("Rehacer acción (R9)"):
            if red.rehacer():
                st.success("Acción rehecha con éxito.")
            else:
                st.warning("No hay acciones para rehacer.")

    st.subheader("Recorrido (R7)")
    al_reves_r7 = st.checkbox("De vuelta (al revés)")
    if st.button("Obtener Recorrido"):
        res_r7 = red.recorrido(ruta_r7, al_reves=al_reves_r7)
        st.write(res_r7)

    st.divider()
    st.subheader("Simular fila de abordaje (R10)")
    lleg_r10 = st.text_input("Minuto de llegada de cada pasajero (separados por coma):", value="0, 1, 1, 4")
    freq_r10 = st.number_input("Frecuencia (minutos entre buses, el primero sale en el minuto 0):", min_value=1, value=2)
    cap_r10 = st.number_input("Capacidad de cada bus:", min_value=1, value=1)
    if st.button("Simular Fila"):
        try:
            llegadas_r10 = [int(x) for x in lleg_r10.replace(" ", "").split(",") if x != ""]
        except ValueError:
            st.warning("Escribe minutos enteros separados por coma, por ejemplo 0, 1, 1, 4.")
            st.stop()
        esperas = simular_fila(llegadas_r10, int(freq_r10), int(cap_r10))
        if not esperas:
            st.info("No hay pasajeros.")
        else:
            st.write("Espera de cada pasajero, en orden de llegada (minutos):", esperas)
            st.write(f"Espera promedio: {sum(esperas) / len(esperas):.2f} min · máxima: {max(esperas)} min")


with tab3:
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
