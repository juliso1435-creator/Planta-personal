import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import clean_sentinels, crosstab_pct


def render(df: pd.DataFrame):
    st.subheader("📋 Reclutamiento: reemplazo vs. ampliación")

    con_requisicion = df[df["tipo_requisicion"].notna()].copy()
    if con_requisicion.empty:
        st.warning("No hay datos de Tipo de requisición en el conjunto filtrado.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        dist = con_requisicion["tipo_requisicion"].value_counts().reset_index()
        dist.columns = ["Tipo de requisición", "Ingresos"]
        dist["% del total"] = (dist["Ingresos"] / dist["Ingresos"].sum() * 100).round(1)
        fig = px.pie(dist, names="Tipo de requisición", values="Ingresos", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dist, use_container_width=True)

    with col2:
        fi = clean_sentinels(con_requisicion["fecha_ingreso"])
        tmp = con_requisicion.assign(periodo=fi.dt.to_period("M").astype(str))
        evol = tmp.groupby(["periodo", "tipo_requisicion"]).size().reset_index(name="Ingresos")
        fig2 = px.area(evol, x="periodo", y="Ingresos", color="tipo_requisicion", groupnorm="percent",
                        labels={"periodo": "Mes"})
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Permite ver si el crecimiento reciente responde a expansión (ampliación de planta) o a cobertura de rotación (reemplazo).")

    st.markdown("---")
    ver_pct = st.checkbox("Ver cruces como % (por fila)", key="recl_cross_pct")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Por UEN — dónde se concentran los reemplazos**")
        cross1_abs = pd.crosstab(con_requisicion["uen"], con_requisicion["tipo_requisicion"])
        if "Reemplazo" in cross1_abs.columns:
            cross1_abs = cross1_abs.sort_values("Reemplazo", ascending=False)
        if ver_pct:
            cross1 = crosstab_pct(con_requisicion["uen"], con_requisicion["tipo_requisicion"]).reindex(cross1_abs.index)
            st.dataframe(cross1.style.format("{:.1f}%"), use_container_width=True, height=400)
        else:
            st.dataframe(cross1_abs, use_container_width=True, height=400)
    with c2:
        st.markdown("**Por cargo — dónde se concentran los reemplazos (Top 20)**")
        top_cargos = con_requisicion["cargo"].value_counts().head(20).index
        subset = con_requisicion[con_requisicion["cargo"].isin(top_cargos)]
        cross2_abs = pd.crosstab(subset["cargo"], subset["tipo_requisicion"])
        if "Reemplazo" in cross2_abs.columns:
            cross2_abs = cross2_abs.sort_values("Reemplazo", ascending=False)
        if ver_pct:
            cross2 = crosstab_pct(subset["cargo"], subset["tipo_requisicion"]).reindex(cross2_abs.index)
            st.dataframe(cross2.style.format("{:.1f}%"), use_container_width=True, height=400)
        else:
            st.dataframe(cross2_abs, use_container_width=True, height=400)
