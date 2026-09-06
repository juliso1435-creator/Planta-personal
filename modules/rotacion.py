import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import compute_tenure, is_activo, clean_sentinels, add_pct_column


def render(df: pd.DataFrame):
    st.subheader("🔄 Rotación y antigüedad")

    df = df.copy()
    df["antiguedad_anios"] = compute_tenure(df)
    activo = is_activo(df["estado_empleado"])

    c1, c2 = st.columns(2)
    c1.metric("Antigüedad promedio (activos)", f"{df.loc[activo, 'antiguedad_anios'].mean():.1f} años")
    c2.metric("Antigüedad mediana (activos)", f"{df.loc[activo, 'antiguedad_anios'].median():.1f} años")

    st.markdown("---")

    # --- Tasa de rotación ---
    st.markdown("**Tasa de rotación**")
    periodo = st.radio("Periodo de cálculo", ["Mensual", "Anual"], horizontal=True)
    freq = "M" if periodo == "Mensual" else "Y"

    fi = clean_sentinels(df["fecha_ingreso"])
    ft = clean_sentinels(df["fecha_terminacion"])

    ingresos = fi.dropna().dt.to_period(freq).value_counts().sort_index()
    retiros = ft.dropna().dt.to_period(freq).value_counts().sort_index()

    idx = sorted(set(ingresos.index) | set(retiros.index))
    serie = pd.DataFrame(index=idx)
    serie["Ingresos"] = ingresos.reindex(idx, fill_value=0)
    serie["Retiros"] = retiros.reindex(idx, fill_value=0)

    # headcount aproximado al final de cada periodo, para calcular headcount promedio
    all_periods = pd.period_range(min(idx), max(idx), freq=freq) if idx else []
    headcount_fin = []
    for p in all_periods:
        end_ts = p.end_time
        activos_a_esa_fecha = ((fi <= end_ts) & (ft.isna() | (ft > end_ts))).sum()
        headcount_fin.append(activos_a_esa_fecha)
    serie_hc = pd.Series(headcount_fin, index=all_periods, name="Headcount fin de periodo")
    serie = serie.reindex(all_periods, fill_value=0)
    serie["Headcount fin de periodo"] = serie_hc
    serie["Headcount promedio"] = serie["Headcount fin de periodo"].rolling(2, min_periods=1).mean()
    serie["Tasa de rotación (%)"] = (serie["Retiros"] / serie["Headcount promedio"].replace(0, np.nan) * 100).round(2)

    serie_reset = serie.reset_index().rename(columns={"index": "Periodo"})
    serie_reset["Periodo"] = serie_reset["Periodo"].astype(str)

    fig_rot = px.line(serie_reset, x="Periodo", y="Tasa de rotación (%)", markers=True)
    st.plotly_chart(fig_rot, use_container_width=True)

    st.markdown("**Serie de tiempo: ingresos vs retiros**")
    fig_iv = px.bar(serie_reset, x="Periodo", y=["Ingresos", "Retiros"], barmode="group")
    st.plotly_chart(fig_iv, use_container_width=True)

    with st.expander("Ver tabla de rotación por periodo"):
        st.dataframe(serie_reset, use_container_width=True)

    st.markdown("---")

    # --- Distribución de antigüedad al retiro ---
    st.markdown("**Distribución de antigüedad al retiro**")
    seg_by = st.selectbox("Segmentar por", ["(Sin segmentar)", "Tipo de cargo", "Cargo", "Agencia"])
    seg_col = {"Tipo de cargo": "tipo_cargo", "Cargo": "cargo", "Agencia": "agencia_nombre"}.get(seg_by)

    retirados = df[df["fecha_terminacion"].notna() & ~is_activo(df["estado_empleado"])]
    if retirados.empty:
        st.info("No hay colaboradores retirados en el conjunto filtrado.")
    else:
        if seg_col:
            fig_h = px.histogram(retirados, x="antiguedad_anios", color=seg_col, nbins=30,
                                  labels={"antiguedad_anios": "Antigüedad al retiro (años)"})
        else:
            fig_h = px.histogram(retirados, x="antiguedad_anios", nbins=30,
                                  labels={"antiguedad_anios": "Antigüedad al retiro (años)"})
        st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    st.markdown("**Ranking de mayor rotación**")
    col1, col2 = st.columns(2)
    with col1:
        rank_cargo = (
            retirados.groupby("cargo", dropna=True).size().reset_index(name="Retiros")
            .sort_values("Retiros", ascending=False)
        )
        rank_cargo = add_pct_column(rank_cargo, "Retiros", "% del total de retiros").head(15)
        st.markdown("_Por cargo_")
        st.dataframe(rank_cargo, use_container_width=True, height=350)
    with col2:
        rank_agencia = (
            retirados.groupby("agencia_nombre", dropna=True).size().reset_index(name="Retiros")
            .sort_values("Retiros", ascending=False)
        )
        rank_agencia = add_pct_column(rank_agencia, "Retiros", "% del total de retiros").head(15)
        st.markdown("_Por agencia_")
        st.dataframe(rank_agencia, use_container_width=True, height=350)
