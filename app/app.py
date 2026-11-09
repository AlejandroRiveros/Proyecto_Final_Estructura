import streamlit as st
import time
import os
from motor.red import Red

st.set_page_config(page_title="Planeador TransMilenio", layout="wide")

st.title("🚌 Planeador de Viajes TransMilenio - Motor EDA")

ruta_datos = "datos"
if os.path.exists(ruta_datos):
    if "app_red" not in st.session_state:
        st.session_state["app_red"] = Red()
    red = st.session_state["app_red"]
else:
    st.error(f"No se encuentra la carpeta de datos en '{ruta_datos}'.")

tab1, tab2, tab3 = st.tabs(["🔍 Consultas y Viajes", "⚙️ Operar Red", "📊 Panel de Rendimiento (R11)"])

with tab1:
    st.header("Consulta de Estaciones y Rutas")
    
    st.subheader("Autocompletar (R2)")
    prefijo_r2 = st.text_input("Prefijo para autocompletar:")
    if prefijo_r2:
        res_r2 = red.autocompletar(prefijo_r2)
        st.write(res_r2)

    st.subheader("Rango (R3)")
    inf_r3 = st.text_input("Estación inferior:")
    sup_r3 = st.text_input("Estación superior:")
    if st.button("Buscar en Rango"):
        res_r3 = red.rango(inf_r3, sup_r3)
        st.write(res_r3)

    st.subheader("Proximo Bus (R4)")
    est_r4 = st.text_input("Estación para proximo_bus:")
    if st.button("Consultar Proximo Bus"):
        res_r4 = red.proximo_bus(est_r4)
        if res_r4 is None:
            st.info("Hoy este bus ya no se encuentra disponible")
        else:
            st.write(res_r4)

    st.subheader("Viaje (R5)")
    orig_r5 = st.text_input("Origen viaje:")
    dest_r5 = st.text_input("Destino viaje:")
    if st.button("Calcular Viaje"):
        res_r5 = red.viaje(orig_r5, dest_r5)
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
    freq_r10 = st.number_input("Frecuencia:", min_value=1, value=10)
    lleg_r10 = st.number_input("Llegadas:", min_value=0, value=5)
    if st.button("Simular Fila"):
        res_r10 = red.simular_fila(int(freq_r10), int(lleg_r10))
        st.write(res_r10)

with tab2:
    st.header("Operaciones de la Red")

    estacion_id = st.text_input("Nombre o ID de estación:")

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

        ruta_r7 = st.text_input("Ruta para agregar/quitar parada:")
        if st.button("Agregar Parada (R7)"):
            if red.agregar_parada(ruta_r7, estacion_id):
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
    if st.button("Obtener Recorrido"):
        res_r7 = red.recorrido(ruta_r7)
        st.write(res_r7)

with tab3:
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
