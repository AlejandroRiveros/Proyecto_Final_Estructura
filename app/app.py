import streamlit as st
import time
import os
from motor.red import Red

st.set_page_config(page_title="Planeador TransMilenio", layout="wide")

st.title("🚌 Planeador de Viajes TransMilenio - Motor EDA")

# Cargar la red (asumiendo que los CSV están en 'datos/')
ruta_datos = "datos"
# Streamlit vuelve a correr este script en cada clic: la Red se guarda en
# st.session_state para que cierres, ediciones y el historial de deshacer
# sobrevivan entre interacciones. Se carga una sola vez por sesión.
if os.path.exists(ruta_datos):
    if "app_red" not in st.session_state:
        st.session_state["app_red"] = Red(ruta_datos)
    red = st.session_state["app_red"]
else:
    st.error(f"No se encuentra la carpeta de datos en '{ruta_datos}'.")

tab1, tab2, tab3 = st.tabs(["🔍 Consultas y Viajes", "⚙️ Operar Red", "📊 Panel de Rendimiento (R11)"])

with tab1:
    st.header("Consulta de Estaciones y Rutas")
    estacion_buscada = st.text_input("Buscar estación:")
    if estacion_buscada:
        estado = red.estado(estacion_buscada.upper())
        st.write(f"Estado de la estación: {estado}")

with tab2:
    st.header("Operaciones de la Red (Cierres y Edición)")
    estacion_a_cerrar = st.text_input("Nombre de estación a cerrar:")
    if st.button("Cerrar Estación"):
        red.cerrar(estacion_a_cerrar.upper())
        st.success(f"Estación {estacion_a_cerrar.upper()} cerrada con éxito.")
    
    if st.button("Deshacer última acción"):
        red.deshacer()
        st.info("Acción deshecha.")

with tab3:
    # El panel R11 vive en app/panel_r11.py (mediciones en app/rendimiento.py).
    # Mide redes propias, no la Red que usa esta app.
    from panel_r11 import mostrar_panel_rendimiento
    mostrar_panel_rendimiento()
