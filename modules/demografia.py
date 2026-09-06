import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, compute_age, add_pct_column, crosstab_pct


def _bar_distribucion(st, df, col, titulo):
    dist = df[col].value_counts(dropna=True).reset_index()
    dist.columns = [titulo, "Headcount"]
    dist = add_pct_column(dist, "Headcount")
    fig = px.bar(dist, x=titulo, y="Headcount", color=titulo, text="% del total")
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(dist, use_container_width=True, height=200)


def render(df: pd.DataFrame):
    st.subheader("🧑‍🤝‍🧑 Demografía y bienestar")

    activos = df[is_activo(df["estado_empleado"])].copy()

    tabs = st.tabs(["Sexo", "Estado civil", "Estrato", "Nivel educativo", "Tipo de sangre"])
    campos = ["sexo", "estado_civil", "estrato", "nivel_educativo", "tipo_sangre"]
    titulos = ["Sexo", "Estado civil", "Estrato", "Nivel educativo", "Tipo de sangre"]
    for tab, campo, titulo in zip(tabs, campos, titulos):
        with tab:
            _bar_distribucion(st, activos, campo, titulo)

    st.markdown("---")
    st.markdown("**Pirámide / histograma de edades**")
    activos["edad"] = compute_age(activos["fecha_nacimiento"])
    edad_valida = activos[activos["edad"].between(15, 90)]
    fig_edad = px.histogram(edad_valida, x="edad", color="sexo", nbins=25, barmode="overlay", opacity=0.7,
                             labels={"edad": "Edad (años)"})
    st.plotly_chart(fig_edad, use_container_width=True)
    st.caption("Se excluyen registros con fecha de nacimiento inválida o centinela.")

    st.markdown("---")
    st.markdown("**Cruces relevantes**")
    ver_pct = st.checkbox("Ver cruces como % (por fila)", key="demo_cross_pct")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("_Sexo × Cargo (Top 15)_")
        top_cargos = activos["cargo"].value_counts(dropna=True).head(15).index
        subset1 = activos[activos["cargo"].isin(top_cargos)]
        cross1 = crosstab_pct(subset1["cargo"], subset1["sexo"]) if ver_pct else pd.crosstab(subset1["cargo"], subset1["sexo"])
        st.dataframe(cross1.style.format("{:.1f}%") if ver_pct else cross1, use_container_width=True, height=350)
    with c2:
        st.markdown("_Sexo × UEN_")
        cross2 = crosstab_pct(activos["uen"], activos["sexo"]) if ver_pct else pd.crosstab(activos["uen"], activos["sexo"])
        st.dataframe(cross2.style.format("{:.1f}%") if ver_pct else cross2, use_container_width=True, height=350)
    with c3:
        st.markdown("_Estrato × Ciudad_")
        cross3 = crosstab_pct(activos["ciudad"], activos["estrato"]) if ver_pct else pd.crosstab(activos["ciudad"], activos["estrato"])
        st.dataframe(cross3.style.format("{:.1f}%") if ver_pct else cross3, use_container_width=True, height=350)
