import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, pct, add_pct_column


def render(df: pd.DataFrame):
    st.subheader("👥 Headcount y composición")

    activo = is_activo(df["estado_empleado"])
    total_activos = int(activo.sum())
    total_retirados = int((~activo & df["estado_empleado"].notna()).sum())
    total = total_activos + total_retirados

    c1, c2, c3 = st.columns(3)
    c1.metric("Total activos", f"{total_activos:,}")
    c2.metric("Total retirados", f"{total_retirados:,}")
    c3.metric("% activos vs retirados", f"{pct(total_activos, total)}% / {pct(total_retirados, total)}%")

    st.markdown("---")

    # Headcount por UEN
    uen_counts = df.loc[activo, "uen"].value_counts(dropna=True).reset_index()
    uen_counts.columns = ["UEN", "Headcount"]
    uen_counts["% del total"] = (uen_counts["Headcount"] / uen_counts["Headcount"].sum() * 100).round(1)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Headcount activo por Unidad Estratégica de Negocio**")
        fig = px.bar(uen_counts, x="UEN", y="Headcount", text="% del total",
                     labels={"Headcount": "Headcount"}, color="UEN")
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Headcount por UEN segmentado por Estado**")
        cross = df.groupby(["uen", "estado_empleado"], dropna=True).size().reset_index(name="Headcount")
        cross["% dentro de la UEN"] = cross.groupby("uen")["Headcount"].transform(lambda s: (s / s.sum() * 100).round(1))
        fig2 = px.bar(cross, x="uen", y="Headcount", color="estado_empleado", barmode="stack",
                      text="% dentro de la UEN",
                      labels={"uen": "UEN", "estado_empleado": "Estado"})
        fig2.update_traces(texttemplate="%{text}%", textposition="inside")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("**Tabla dinámica: headcount por División / Departamento**")
    pivot = (
        df[activo]
        .groupby(["division", "departamento"], dropna=True)
        .size()
        .reset_index(name="Headcount")
        .sort_values("Headcount", ascending=False)
    )
    pivot = add_pct_column(pivot, "Headcount")
    divisiones = sorted(pivot["division"].dropna().unique())
    filtro_div = st.multiselect("Filtrar por División (drill-down)", divisiones, default=[])
    tabla = pivot if not filtro_div else pivot[pivot["division"].isin(filtro_div)]
    st.dataframe(tabla, use_container_width=True, height=400)
