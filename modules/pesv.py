import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, pct, add_pct_column


def _es_conductor(valor) -> bool:
    if pd.isna(valor):
        return False
    v = str(valor).strip().lower()
    return v in {"si", "sí", "conductor", "1", "true", "x", "s"}


def render(df: pd.DataFrame):
    st.subheader("🚗 PESV — Plan Estratégico de Seguridad Vial")

    activos = df[is_activo(df["estado_empleado"])].copy()
    activos["es_conductor"] = activos["pesv"].apply(_es_conductor)

    total = len(activos)
    conductores = int(activos["es_conductor"].sum())

    c1, c2 = st.columns(2)
    c1.metric("Colaboradores con rol de conductor", f"{conductores:,}")
    c2.metric("% del headcount activo", f"{pct(conductores, total)}%")

    if conductores == 0:
        st.info("No se identificaron colaboradores marcados con rol de conductor en el conjunto filtrado. "
                 "Verifica el mapeo de la columna 'Información PESV' en la pestaña de carga.")
        return

    st.markdown("---")
    solo_conductores = activos[activos["es_conductor"]]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Por UEN**")
        d1 = solo_conductores["uen"].value_counts().reset_index()
        d1.columns = ["UEN", "Conductores"]
        d1 = add_pct_column(d1, "Conductores")
        fig1 = px.bar(d1, x="UEN", y="Conductores", text="% del total")
        fig1.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        st.markdown("**Por agencia**")
        d2 = solo_conductores["agencia_nombre"].value_counts().reset_index()
        d2.columns = ["Agencia", "Conductores"]
        d2 = add_pct_column(d2, "Conductores")
        fig2 = px.bar(d2, x="Agencia", y="Conductores", text="% del total")
        fig2.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)
    with c3:
        st.markdown("**Por tipo de contrato**")
        dist = solo_conductores["tipo_contrato"].value_counts().reset_index()
        dist.columns = ["Tipo de contrato", "Conductores"]
        dist = add_pct_column(dist, "Conductores")
        fig3 = px.pie(dist, names="Tipo de contrato", values="Conductores", hole=0.4)
        fig3.update_traces(textinfo="label+percent")
        st.plotly_chart(fig3, use_container_width=True)

    tercerizados = solo_conductores["tipo_contrato"].astype(str).str.lower().str.contains(
        "temporal|tercer|outsourc|contratista", na=False
    )
    st.info(f"**{pct(tercerizados.sum(), len(solo_conductores))}%** de los conductores tienen un tipo de "
            f"contrato temporal, tercerizado o de contratista.")
