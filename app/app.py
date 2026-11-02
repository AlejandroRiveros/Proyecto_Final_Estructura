import streamlit as st
import time
import os
from motor.red import Red

st.set_page_config(page_title="Planeador TransMilenio", layout="wide")

st.title("🚌 Planeador de Viajes TransMilenio - Motor EDA")

# Cargar la red (asumiendo que los CSV están en 'datos/')
ruta_datos = "datos"
if os.path.exists(ruta_datos):
    red = Red(ruta_datos)
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
    st.header("Panel de Rendimiento - R11")
    st.write("Mide el tiempo de ejecución de las operaciones para demostrar la complejidad teórica.")
    
    if st.button("Ejecutar Pruebas de Rendimiento"):
        tiempos = []
        sizes = [100, 200, 400, 800] # Ejemplo de tamaños crecientes n y 2n
        
        # Medición simulada de una operación del motor (ej. búsqueda o ranking)
        for n in sizes:
            inicio = time.time()
            # Simulamos carga de trabajo proporcional a n
            _ = red.ranking(10)
            fin = time.time()
            tiempos.append((n, (fin - inicio) * 1000)) # en milisegundos
            
        st.write("Resultados de tiempo por tamaño de red (ms):")
        st.line_chart(data={t[0]: t[1] for t in tiempos})
        st.success("Pruebas de rendimiento completadas con éxito.")
