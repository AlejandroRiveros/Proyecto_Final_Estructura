import streamlit as st
import time
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


tab1, tab2, tab3 = st.tabs(["🔍 Consultas y Viajes", "⚙️ Operar Red", "📊 Panel de Rendimiento (R11)"])

with tab1:
    st.header("Consulta de Estaciones y Rutas")

    st.subheader("Estado (R1)")
    est_r1 = st.text_input("Estación a consultar:")
    if est_r1:
        estado = red.estado(nombre(est_r1))
        if estado is None:
            st.warning("La estación no existe.")
        else:
            st.write(f"Estado de la estación: {estado}")

    st.subheader("Autocompletar (R2)")
    prefijo_r2 = st.text_input("Prefijo para autocompletar:")
    k_r2 = st.number_input("Cuántas sugerencias (k):", min_value=1, value=5, step=1)
    if prefijo_r2:
        res_r2 = red.autocompletar(nombre(prefijo_r2), int(k_r2))
        st.write(res_r2)

    st.subheader("Rango (R3)")
    inf_r3 = st.text_input("Estación inferior:")
    sup_r3 = st.text_input("Estación superior:")
    if st.button("Buscar en Rango"):
        res_r3 = red.rango(nombre(inf_r3), nombre(sup_r3))
        st.write(res_r3)

    st.subheader("Proximo Bus (R4)")
    est_r4 = st.text_input("Estación para proximo_bus:")
    ruta_r4 = st.text_input("Ruta para proximo_bus:")
    hora_r4 = st.time_input("Hora:", value=None, step=60)
    if st.button("Consultar Proximo Bus"):
        if hora_r4 is None:
            st.warning("Escoge una hora.")
            st.stop()
        res_r4 = red.proximo_bus(nombre(est_r4), nombre(ruta_r4), hora_r4.strftime("%H:%M"))
        if res_r4 is None:
            st.info("Hoy este bus ya no se encuentra disponible")
        else:
            st.write(res_r4)

    st.subheader("Viaje (R5)")
    orig_r5 = st.text_input("Origen viaje:")
    dest_r5 = st.text_input("Destino viaje:")
    if st.button("Calcular Viaje"):
        res_r5 = red.viaje(nombre(orig_r5), nombre(dest_r5))
        if res_r5 is None:
            st.write("None")
        else:
            st.write(res_r5)

    st.subheader("Ranking (R6)")
    k_r6 = st.number_input("Valor k:", min_value=1, step=1)
    if st.button("Obtener Ranking"):
        res_r6 = red.ranking(int(k_r6))
        st.write(res_r6)

    st.subheader("Simular Fila (R10)")
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

with tab3:
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
