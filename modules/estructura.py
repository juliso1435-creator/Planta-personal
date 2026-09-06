import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, add_pct_column


def render(df: pd.DataFrame):
    st.subheader("🏢 Estructura organizacional")

    activos = df[is_activo(df["estado_empleado"])].copy()

    st.markdown("**Jerarquía: División → Departamento → Centro de costos**")
    jerarquia = activos.dropna(subset=["division"]).copy()
    for col in ["division", "departamento", "centro_costos"]:
        jerarquia[col] = jerarquia[col].fillna("(Sin especificar)")

    fig = px.treemap(
        jerarquia,
        path=[px.Constant("Corbeta"), "division", "departamento", "centro_costos"],
        values=None,
    )
    fig.update_traces(root_color="lightgrey", textinfo="label+value+percent parent+percent root")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("El tamaño de cada bloque representa la cantidad de colaboradores activos.")

    st.markdown("---")
    st.markdown("**Span of control (reportes directos por jefe inmediato)**")

    span = (
        activos.groupby(["id_supervisor", "jefe_inmediato"], dropna=True)
        .size()
        .reset_index(name="Reportes directos")
        .sort_values("Reportes directos", ascending=False)
    )

    umbral_alto = st.slider("Umbral de span 'alto' (alerta)", 5, 40, 15)
    umbral_bajo = st.slider("Umbral de span 'bajo' (alerta)", 1, 5, 1)

    def clasificar(n):
        if n >= umbral_alto:
            return "⚠️ Span muy alto"
        if n <= umbral_bajo:
            return "⚠️ Span muy bajo"
        return "Normal"

    span["Alerta"] = span["Reportes directos"].apply(clasificar)
    span = add_pct_column(span, "Reportes directos", "% del headcount total")

    c1, c2 = st.columns(2)
    c1.metric("Jefes con span muy alto", int((span["Alerta"] == "⚠️ Span muy alto").sum()))
    c2.metric("Jefes con span muy bajo", int((span["Alerta"] == "⚠️ Span muy bajo").sum()))

    st.dataframe(
        span.style.apply(
            lambda r: ["background-color:#ffe6e6" if r["Alerta"] != "Normal" else "" for _ in r], axis=1
        ),
        use_container_width=True,
        height=450,
    )
