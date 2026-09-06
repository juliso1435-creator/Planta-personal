import io
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.utils import is_activo, compute_tenure, pct, clean_sentinels


def _build_summary_tables(df: pd.DataFrame) -> dict:
    """Recalcula las tablas clave de cada pestaña para exportarlas a Excel."""
    activo = is_activo(df["estado_empleado"])
    activos = df[activo].copy()
    tablas = {}

    # Headcount
    tablas["Headcount_UEN"] = activos["uen"].value_counts(dropna=True).reset_index().rename(
        columns={"index": "UEN", "uen": "Headcount"})
    tablas["Headcount_Div_Depto"] = (
        activos.groupby(["division", "departamento"], dropna=True).size().reset_index(name="Headcount")
    )

    # Rotación
    df2 = df.copy()
    df2["antiguedad_anios"] = compute_tenure(df2)
    tablas["Antiguedad_activos"] = df2.loc[activo, ["codigo_empleado", "nombre_completo", "antiguedad_anios"]]

    # Geografía
    tablas["Headcount_Ciudad"] = activos["ciudad"].value_counts(dropna=True).reset_index().rename(
        columns={"index": "Ciudad", "ciudad": "Headcount"})

    # Vinculación
    tablas["Tipo_Contrato"] = activos["tipo_contrato"].value_counts(dropna=True).reset_index().rename(
        columns={"index": "Tipo de contrato", "tipo_contrato": "Headcount"})

    # Demografía
    tablas["Demografia_Sexo"] = activos["sexo"].value_counts(dropna=True).reset_index().rename(
        columns={"index": "Sexo", "sexo": "Headcount"})
    tablas["Demografia_Estrato"] = activos["estrato"].value_counts(dropna=True).reset_index().rename(
        columns={"index": "Estrato", "estrato": "Headcount"})

    # Reclutamiento
    if df["tipo_requisicion"].notna().any():
        tablas["Reclutamiento"] = df["tipo_requisicion"].value_counts(dropna=True).reset_index().rename(
            columns={"index": "Tipo de requisición", "tipo_requisicion": "Ingresos"})

    # PESV
    from modules.pesv import _es_conductor
    tablas["PESV"] = pd.DataFrame({
        "Métrica": ["Total conductores", "% del headcount activo"],
        "Valor": [int(activos["pesv"].apply(_es_conductor).sum()),
                  pct(activos["pesv"].apply(_es_conductor).sum(), len(activos))],
    })

    return tablas


def _to_excel_bytes(tablas: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre_hoja, tabla in tablas.items():
            tabla.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)
    buffer.seek(0)
    return buffer.getvalue()


def _build_pdf_bytes(df: pd.DataFrame, tablas: dict) -> bytes:
    from fpdf import FPDF

    activo = is_activo(df["estado_empleado"])
    total_activos = int(activo.sum())
    total_retirados = int((~activo & df["estado_empleado"].notna()).sum())

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Resumen Ejecutivo - Gestión Humana Corbeta", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Generado el {date.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "KPIs generales", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total activos: {total_activos:,}", ln=True)
    pdf.cell(0, 8, f"Total retirados: {total_retirados:,}", ln=True)
    pdf.cell(0, 8, f"% activos: {pct(total_activos, total_activos + total_retirados)}%", ln=True)
    pdf.ln(4)

    # Gráfico de headcount por UEN, exportado con kaleido
    try:
        fig = px.bar(tablas["Headcount_UEN"].head(15), x="UEN", y="Headcount", title="Headcount por UEN")
        img_bytes = fig.to_image(format="png", width=900, height=500, scale=2)
        img_path = "/tmp/_headcount_uen.png"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        pdf.image(img_path, x=10, w=190)
        pdf.ln(4)
    except Exception:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "(No fue posible renderizar el gráfico de headcount por UEN)", ln=True)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Top 10 UEN por headcount activo", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for _, row in tablas["Headcount_UEN"].head(10).iterrows():
        pdf.cell(0, 7, f"- {row.iloc[0]}: {row.iloc[1]:,}", ln=True)

    return bytes(pdf.output(dest="S"))


def render(df: pd.DataFrame):
    st.subheader("⬇️ Exportar resultados")
    st.caption("Genera un Excel con todas las tablas calculadas, o un resumen ejecutivo en PDF listo para Gerencia.")

    tablas = _build_summary_tables(df)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Excel completo (una hoja por análisis)**")
        if st.button("Generar Excel"):
            excel_bytes = _to_excel_bytes(tablas)
            st.download_button(
                "⬇️ Descargar Excel",
                data=excel_bytes,
                file_name=f"dashboard_gh_corbeta_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with col2:
        st.markdown("**Resumen ejecutivo en PDF**")
        if st.button("Generar PDF"):
            try:
                pdf_bytes = _build_pdf_bytes(df, tablas)
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"resumen_ejecutivo_corbeta_{date.today().isoformat()}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"No fue posible generar el PDF: {e}. "
                         f"Verifica que 'kaleido' y 'fpdf2' estén instalados (ver requirements.txt).")

    with st.expander("Vista previa de las tablas que se exportarán"):
        for nombre, tabla in tablas.items():
            st.markdown(f"**{nombre}**")
            st.dataframe(tabla.head(20), use_container_width=True)
