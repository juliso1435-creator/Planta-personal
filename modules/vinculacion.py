import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, clean_sentinels, add_pct_column, crosstab_pct


def render(df: pd.DataFrame):
    st.subheader("📄 Tipo de vinculación")

    activos = df[is_activo(df["estado_empleado"])].copy()

    col1, col2 = st.columns(2)
    with col1:
        dist = activos["tipo_contrato"].value_counts(dropna=True).reset_index()
        dist.columns = ["Tipo de contrato", "Headcount"]
        dist = add_pct_column(dist, "Headcount")
        fig = px.pie(dist, names="Tipo de contrato", values="Headcount", hole=0.4)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(dist, use_container_width=True, height=350)

    st.markdown("---")
    st.markdown("**Evolución de la mezcla de tipos de contrato en el tiempo**")
    fi = clean_sentinels(df["fecha_ingreso"])
    tmp = df.assign(anio_ingreso=fi.dt.year)
    tmp = tmp[tmp["anio_ingreso"].notna()]
    evol = tmp.groupby(["anio_ingreso", "tipo_contrato"]).size().reset_index(name="Ingresos")
    fig2 = px.area(evol, x="anio_ingreso", y="Ingresos", color="tipo_contrato", groupnorm="percent",
                    labels={"anio_ingreso": "Año de ingreso", "Ingresos": "% de ingresos"})
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Muestra si, con los años, la contratación se ha desplazado hacia tipos de contrato más temporales o tercerizados.")

    st.markdown("---")
    ver_pct = st.checkbox("Ver cruces como % (por fila)", key="vinc_cross_pct")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Tipo de contrato × UEN**")
        if ver_pct:
            cross1 = crosstab_pct(activos["uen"], activos["tipo_contrato"], normalize="index")
            st.dataframe(cross1.style.format("{:.1f}%"), use_container_width=True, height=350)
        else:
            cross1 = pd.crosstab(activos["uen"], activos["tipo_contrato"])
            st.dataframe(cross1, use_container_width=True, height=350)
    with c2:
        st.markdown("**Tipo de contrato × Cargo (Top 20 cargos)**")
        top_cargos = activos["cargo"].value_counts(dropna=True).head(20).index
        subset = activos[activos["cargo"].isin(top_cargos)]
        if ver_pct:
            cross2 = crosstab_pct(subset["cargo"], subset["tipo_contrato"], normalize="index")
            st.dataframe(cross2.style.format("{:.1f}%"), use_container_width=True, height=350)
        else:
            cross2 = pd.crosstab(subset["cargo"], subset["tipo_contrato"])
            st.dataframe(cross2, use_container_width=True, height=350)
