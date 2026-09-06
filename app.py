"""
Dashboard de Gestión Humana – Corbeta
Ejecutar con: streamlit run app.py
"""
import streamlit as st
import pandas as pd

from modules import data_loader, quality_checks, headcount, rotacion, geografia
from modules import vinculacion, demografia, reclutamiento, estructura, pesv, exportar
from modules.utils import (
    EXPECTED_COLUMNS, auto_map_columns, apply_mapping, coerce_dates,
    get_filter_options, apply_global_filters,
)

st.set_page_config(
    page_title="Dashboard de Gestión Humana – Corbeta",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Dashboard de Gestión Humana – Corbeta")

# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
for key, default in [
    ("df_raw", None), ("column_mapping", None), ("df_mapped", None),
    ("mapping_confirmado", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

TAB_NAMES = [
    "0️⃣ Carga y calidad",
    "1️⃣ Headcount",
    "2️⃣ Rotación",
    "3️⃣ Geografía",
    "4️⃣ Vinculación",
    "5️⃣ Demografía",
    "6️⃣ Reclutamiento",
    "7️⃣ Estructura",
    "8️⃣ PESV",
    "9️⃣ Exportar",
]
tabs = st.tabs(TAB_NAMES)

# ---------------------------------------------------------------------------
# PESTAÑA 0 — Carga, mapeo y calidad de datos
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("📁 Carga de archivo")
    uploaded = st.file_uploader("Selecciona el archivo de colaboradores (CSV, XLSX o XLS)",
                                 type=["csv", "xlsx", "xls"])

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        sheet_name = None
        if uploaded.name.lower().endswith((".xlsx", ".xls")):
            sheets = data_loader.list_excel_sheets(file_bytes)
            sheet_name = st.selectbox("Selecciona la hoja a analizar", sheets)

        if st.button("Cargar archivo", type="primary"):
            with st.spinner("Leyendo archivo..."):
                st.session_state["df_raw"] = data_loader.load_dataframe(file_bytes, uploaded.name, sheet_name)
                st.session_state["mapping_confirmado"] = False
            st.success(f"Archivo cargado: {len(st.session_state['df_raw']):,} filas, "
                       f"{len(st.session_state['df_raw'].columns)} columnas.")

    df_raw = st.session_state["df_raw"]

    if df_raw is not None:
        st.markdown("---")
        st.subheader("🔗 Mapeo de columnas")
        st.caption("Confirma o corrige el emparejamiento automático de columnas. "
                   "Esto permite que la app funcione aunque los nombres exactos varíen entre cargas.")

        auto_mapping = st.session_state["column_mapping"] or auto_map_columns(df_raw.columns)
        columnas_disponibles = ["(No disponible)"] + list(df_raw.columns)

        with st.form("form_mapeo"):
            nuevo_mapping = {}
            cols_form = st.columns(2)
            for i, (key, meta) in enumerate(EXPECTED_COLUMNS.items()):
                col_widget = cols_form[i % 2]
                valor_actual = auto_mapping.get(key)
                idx = columnas_disponibles.index(valor_actual) if valor_actual in columnas_disponibles else 0
                seleccion = col_widget.selectbox(meta["label"], columnas_disponibles, index=idx, key=f"map_{key}")
                nuevo_mapping[key] = None if seleccion == "(No disponible)" else seleccion
            confirmar = st.form_submit_button("✅ Confirmar mapeo y continuar", type="primary")

        if confirmar:
            st.session_state["column_mapping"] = nuevo_mapping
            df_mapped = apply_mapping(df_raw, nuevo_mapping)
            df_mapped = coerce_dates(df_mapped)
            st.session_state["df_mapped"] = df_mapped
            st.session_state["mapping_confirmado"] = True
            st.success("Mapeo confirmado. Ya puedes revisar la calidad de datos y navegar por las demás pestañas.")

        faltantes = [meta["label"] for key, meta in EXPECTED_COLUMNS.items() if not auto_mapping.get(key)]
        if faltantes:
            st.warning("Columnas que no se detectaron automáticamente (puedes asignarlas manualmente arriba): "
                       + ", ".join(faltantes))

    if st.session_state["mapping_confirmado"] and st.session_state["df_mapped"] is not None:
        st.markdown("---")
        quality_checks.render(st.session_state["df_mapped"])

# ---------------------------------------------------------------------------
# Si aún no hay datos mapeados, detener aquí con un mensaje
# ---------------------------------------------------------------------------
if not st.session_state["mapping_confirmado"] or st.session_state["df_mapped"] is None:
    with tabs[1]:
        st.info("⬅️ Carga un archivo y confirma el mapeo de columnas en la pestaña **0️⃣ Carga y calidad** para comenzar.")
    st.stop()

df_mapped = st.session_state["df_mapped"]

# ---------------------------------------------------------------------------
# Filtro global persistente (sidebar) — aplica a todas las pestañas 1-9
# ---------------------------------------------------------------------------
st.sidebar.header("🔎 Filtros globales")
opts = get_filter_options(df_mapped)

fecha_min = opts.get("fecha_min")
fecha_max = opts.get("fecha_max")
if fecha_min and fecha_max and fecha_min < fecha_max:
    fecha_rango = st.sidebar.date_input("Rango de fecha de ingreso", value=(fecha_min, fecha_max),
                                         min_value=fecha_min, max_value=fecha_max)
    if isinstance(fecha_rango, tuple) and len(fecha_rango) == 2:
        fecha_rango = fecha_rango
    else:
        fecha_rango = (fecha_min, fecha_max)
else:
    fecha_rango = None

uen_sel = st.sidebar.multiselect("Unidad Estratégica de Negocio", opts.get("uen", []))
division_sel = st.sidebar.multiselect("División", opts.get("division", []))
agencia_sel = st.sidebar.multiselect("Agencia (Ubicación física)", opts.get("agencia", []))
estado_sel = st.sidebar.multiselect("Estado de empleado", opts.get("estado", []))
ciudad_sel = st.sidebar.multiselect("Ciudad", opts.get("ciudad", []))

filters = {
    "fecha_rango": fecha_rango, "uen": uen_sel, "division": division_sel,
    "agencia": agencia_sel, "estado": estado_sel, "ciudad": ciudad_sel,
}
df_filtrado = apply_global_filters(df_mapped, filters)

st.sidebar.markdown("---")
st.sidebar.metric("Filas tras filtro", f"{len(df_filtrado):,} / {len(df_mapped):,}")

if st.sidebar.button("🔁 Rehacer mapeo de columnas"):
    st.session_state["mapping_confirmado"] = False
    st.rerun()

# ---------------------------------------------------------------------------
# PESTAÑAS 1-9
# ---------------------------------------------------------------------------
with tabs[1]:
    headcount.render(df_filtrado)
with tabs[2]:
    rotacion.render(df_filtrado)
with tabs[3]:
    geografia.render(df_filtrado)
with tabs[4]:
    vinculacion.render(df_filtrado)
with tabs[5]:
    demografia.render(df_filtrado)
with tabs[6]:
    reclutamiento.render(df_filtrado)
with tabs[7]:
    estructura.render(df_filtrado)
with tabs[8]:
    pesv.render(df_filtrado)
with tabs[9]:
    exportar.render(df_filtrado)
