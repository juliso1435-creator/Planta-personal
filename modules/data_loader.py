"""
Carga de archivos de colaboradores (CSV, XLSX, XLS).
"""
import io
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def list_excel_sheets(file_bytes: bytes) -> list:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    return xls.sheet_names


@st.cache_data(show_spinner="Cargando archivo...")
def load_dataframe(file_bytes: bytes, filename: str, sheet_name=None) -> pd.DataFrame:
    """
    Carga el archivo en un DataFrame. Soporta CSV, XLSX y XLS.
    Todas las columnas se cargan como texto en primera instancia; el tipado
    (fechas, números) se hace después del mapeo de columnas.
    """
    name = filename.lower()
    if name.endswith(".csv"):
        # Intenta detectar separador y encoding de forma tolerante
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python", dtype=str)
        except Exception:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=";", encoding="latin-1", dtype=str)
    elif name.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, engine="xlrd", dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, engine="openpyxl", dtype=str)

    df.columns = [str(c).strip() for c in df.columns]
    # elimina filas y columnas completamente vacías
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return df
