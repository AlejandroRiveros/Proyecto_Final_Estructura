"""Vista del panel de rendimiento (R11) para Streamlit.

app.py solo tiene que llamar a mostrar_panel_rendimiento() dentro de su pestaña.
Las redes que se miden son propias (carpetas temporales), no la Red de la app.
Las mediciones están en rendimiento.py; aquí solo se dibujan.
"""

import math
import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

# La raíz del repositorio (para motor/) y esta carpeta (para rendimiento.py)
# en el path. No se importa "app.rendimiento" porque app/app.py taparía al paquete.
_AQUI = os.path.dirname(os.path.abspath(__file__))
for _carpeta in (os.path.dirname(_AQUI), _AQUI):
    if _carpeta not in sys.path:
        sys.path.insert(0, _carpeta)

import rendimiento  # noqa: E402

# Todas las claves de st.session_state del panel empiezan con "r11_".
CLAVE = "r11_escalamiento"
CLAVE_REPLICADA = "r11_replicada"
# Diferencia máxima aceptada entre el exponente medido y el esperado
# (pendiente en escala log-log). Es una guía visual, no una prueba.
TOLERANCIA = 0.3


def _exponente_esperado(puntos, esperado):
    f = rendimiento.FUNCIONES[esperado]
    x0, x1 = puntos[0][0], puntos[-1][0]
    return math.log(f(x1) / f(x0)) / math.log(x1 / x0)


def _grafica(r):
    medidos = pd.DataFrame(r["puntos"], columns=["x", "µs"]).assign(serie="Medido")
    esperada = pd.DataFrame(rendimiento.referencia(r["puntos"], r["esperado"]), columns=["x", "µs"])
    nombre_esperada = "Esperado %s (escalado)" % r["esperado"]
    esperada = esperada.assign(serie=nombre_esperada)
    datos = pd.concat([medidos, esperada])
    series = ["Medido", nombre_esperada]
    xs = [x for x, _ in r["puntos"]]
    return (
        alt.Chart(datos)
        .mark_line(point=True)
        .encode(
            x=alt.X("x:Q", scale=alt.Scale(type="log", base=2),
                    axis=alt.Axis(values=xs, format="d"), title=r["variable"]),
            y=alt.Y("µs:Q", title="µs por llamada"),
            color=alt.Color("serie:N", title=None, sort=series,
                            scale=alt.Scale(domain=series, range=["#2563eb", "#9ca3af"]),
                            legend=alt.Legend(orient="bottom")),
            strokeDash=alt.StrokeDash("serie:N", sort=series, legend=None,
                                      scale=alt.Scale(domain=series, range=[[1, 0], [6, 4]])),
            tooltip=["serie", "x", alt.Tooltip("µs:Q", format=".2f")],
        )
        .properties(height=260)
    )


def _miles(x):
    return f"{x:,}".replace(",", ".")


def _tabla_duplicaciones(r):
    filas = []
    for x0, x1, medido, esperado in rendimiento.crecimiento(r["puntos"], r["esperado"]):
        filas.append({
            "De → a": "%s → %s" % (_miles(x0), _miles(x1)),
            "Creció": "×%.2f" % medido,
            "Debía crecer": "×%.2f" % esperado,
        })
    tabla = pd.DataFrame(filas)
    if "extra" in r:
        # Dato que acompaña a cada tamaño (m, d o el tiempo solo en la copia 1).
        nombre, valores = r["extra"]
        tabla[nombre + " (de → a)"] = ["%s → %s" % (a, b) for a, b in zip(valores, valores[1:])]
    return tabla


def _experimento(r):
    st.markdown("**%s** · esperado **%s**" % (r["operacion"], r["esperado"]))
    st.caption("Crece: %s. Fijo: %s." % (r["variable"], r["fijos"]))
    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        st.altair_chart(_grafica(r), use_container_width=True)
    with derecha:
        st.dataframe(_tabla_duplicaciones(r), hide_index=True, use_container_width=True)
        b = rendimiento.exponente(r["puntos"])
        b_esp = _exponente_esperado(r["puntos"], r["esperado"])
        resumen = "Exponente medido %.2f, esperado %.2f (0 = constante, 1 = lineal)." % (b, b_esp)
        if abs(b - b_esp) <= TOLERANCIA:
            st.success("Coincide. " + resumen)
        else:
            st.warning("No coincide del todo. " + resumen + " Ver la explicación.")
    st.info(r["explicacion"])


def _mostrar_resultados(resultados):
    grupos = []
    for r in resultados:
        if r["requisito"] not in grupos:
            grupos.append(r["requisito"])
    for g in grupos:
        with st.expander(g, expanded=False):
            primero = True
            for r in resultados:
                if r["requisito"] == g:
                    if not primero:
                        st.divider()
                    _experimento(r)
                    primero = False


def _modo_replicada():
    st.write(
        "La red real (`datos/`) se copia 1, 2, 4 y 8 veces como copias separadas: la copia c "
        "agrega \" ~c\" a cada estación y ruta en los tres CSV, y se conservan todas las filas de "
        "horarios. Las consultas son al azar sobre datos reales (caso típico). **No es una "
        "reproducción del script del profesor**: sabemos que duplica la red, pero no cómo."
    )
    if st.button("Medir", key="r11_medir_replicada", type="primary"):
        barra = st.progress(0.0, text="Midiendo...")

        def avance(i, total, c):
            barra.progress(i / total, text="Red real ×%d (%d de %d)" % (c, i + 1, total))

        st.session_state[CLAVE_REPLICADA] = rendimiento.medir_red_replicada(avance=avance)
        barra.empty()
    guardado = st.session_state.get(CLAVE_REPLICADA)
    if guardado is None:
        st.caption("Tarda alrededor de un minuto. Los resultados quedan guardados mientras la app esté abierta.")
        return
    tabla, resultados = guardado
    st.subheader("Qué cambia al replicar")
    st.dataframe(pd.DataFrame(tabla), hide_index=True, use_container_width=True)
    st.caption("Calculado de los CSV generados, no supuesto. Lo que queda igual explica por qué "
               "varias gráficas se esperan planas: una curva plana también es evidencia.")
    _mostrar_resultados(resultados)
    _como_se_mide()


def _medir_todo():
    resultados = []
    barra = st.progress(0.0, text="Midiendo...")
    total = len(rendimiento.EXPERIMENTOS)
    for i, exp in enumerate(rendimiento.EXPERIMENTOS):
        barra.progress(i / total, text="Midiendo %s (%d de %d)" % (exp.__name__[4:], i + 1, total))
        resultados.append(exp())
    barra.empty()
    return resultados


def _modo_escalamiento():
    st.write(
        "Cada gráfica hace crecer solo la variable que controla el trabajo de esa "
        "operación (redes sintéticas, cargadas con `Red(carpeta)` y medidas por la "
        "API pública). La curva punteada es la complejidad esperada escalada con la "
        "mediana de tiempo / f(x): sirve para comparar la forma, no prueba nada por sí sola."
    )
    if st.button("Medir", key="r11_medir_escalamiento", type="primary"):
        st.session_state[CLAVE] = _medir_todo()
    resultados = st.session_state.get(CLAVE)
    if resultados is None:
        st.caption("Tarda alrededor de un minuto. Los resultados quedan guardados mientras la app esté abierta.")
        return
    _mostrar_resultados(resultados)
    _como_se_mide()


def _como_se_mide():
    with st.expander("Cómo se mide"):
        st.markdown(
            "- La generación de los CSV y la carga quedan fuera del tiempo; la carga se mide aparte.\n"
            "- Las consultas se miden por lotes de miles de llamadas, en 7 rondas, y se toma la mediana.\n"
            "- Las operaciones que cambian la red se cronometran solas (restando el costo del reloj, "
            "%.0f ns). Después `deshacer()` restaura datos e historial fuera del cronómetro.\n"
            "- En la red real replicada, la carga es una sola medición por tamaño (no una mediana), "
            "para que el modo termine en un tiempo razonable; no estima la variabilidad.\n"
            "- Durante cada medición se apaga el recolector de basura de Python, como hace `timeit`.\n"
            "- R10 (`simular_fila`) se agrega cuando esté corregida." % rendimiento.COSTO_RELOJ_NS
        )


def mostrar_panel_rendimiento():
    """Única función pública: la pestaña R11 de app.py solo la llama."""
    st.header("Panel de rendimiento (R11)")
    modo = st.radio(
        "Modo", ["Escalamiento por operación", "Red real replicada"], horizontal=True,
        label_visibility="collapsed", key="r11_modo",
    )
    if modo == "Escalamiento por operación":
        _modo_escalamiento()
    else:
        _modo_replicada()


if __name__ == "__main__":
    st.set_page_config(page_title="Panel R11", layout="wide")
    mostrar_panel_rendimiento()
