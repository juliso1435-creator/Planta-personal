import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, add_pct_column, crosstab_pct


def render(df: pd.DataFrame):
    st.subheader("🌎 Distribución geográfica")

    activos = df[is_activo(df["estado_empleado"])]

    ciudad_counts = activos["ciudad"].value_counts(dropna=True).reset_index()
    ciudad_counts.columns = ["Ciudad", "Headcount"]
    ciudad_counts = add_pct_column(ciudad_counts, "Headcount").sort_values("Headcount", ascending=False)

    fig = px.bar(ciudad_counts, x="Ciudad", y="Headcount", color="Ciudad", text="% del total")
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Concentración del headcount (regla 80/20)**")
    ciudad_counts["% acumulado"] = ciudad_counts["% del total"].cumsum().round(1)
    ciudad_counts["Dentro del 80%"] = ciudad_counts["% acumulado"] <= 80

    st.dataframe(ciudad_counts, use_container_width=True, height=400)
    n_ciudades_80 = int(ciudad_counts["Dentro del 80%"].sum()) + 1
    st.info(f"**{n_ciudades_80}** ciudad(es)/agencia(s) concentran aproximadamente el 80% del headcount activo.")

    st.markdown("---")
    st.markdown("**Cruce: Ciudad × Tipo de contrato**")
    ver_pct = st.checkbox("Ver como % (por fila, dentro de cada ciudad)", key="geo_cross_pct")
    if ver_pct:
        cross = crosstab_pct(activos["ciudad"], activos["tipo_contrato"], normalize="index")
        st.dataframe(cross.style.format("{:.1f}%"), use_container_width=True, height=400)
    else:
        cross = pd.crosstab(activos["ciudad"], activos["tipo_contrato"])
        st.dataframe(cross, use_container_width=True, height=400)
