"""
Utilidades compartidas por toda la aplicación:
- Definición de columnas esperadas y su auto-mapeo (fuzzy matching).
- Normalización de fechas y detección de fechas centinela.
- Cálculo de edad y antigüedad.
- Aplicación de filtros globales.
"""
import difflib
import unicodedata
from datetime import datetime, date

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Definición de columnas esperadas
# ---------------------------------------------------------------------------
# Cada clave interna tiene una etiqueta legible y una lista de "candidatos"
# (nombres tal como suelen aparecer en las cargas) usados para el auto-mapeo.
EXPECTED_COLUMNS = {
    "codigo_empleado":     {"label": "Código de empleado",
                             "candidates": ["codigo de empleado", "cod empleado", "codigo empleado", "employee id", "codigo"]},
    "nombre_completo":     {"label": "Nombre completo",
                             "candidates": ["nombre completo", "nombre"]},
    "uen":                 {"label": "Unidad Estratégica de Negocio",
                             "candidates": ["unidad estrategica de negocio nombre", "unidad estrategica de negocio", "uen"]},
    "division":            {"label": "División",
                             "candidates": ["division nombre", "division"]},
    "departamento":        {"label": "Departamento",
                             "candidates": ["departamento nombre", "departamento"]},
    "centro_costos":       {"label": "Centro de costos",
                             "candidates": ["centro de costos nombre", "centro de costos"]},
    "jefe_inmediato":      {"label": "Jefe inmediato",
                             "candidates": ["jefe inmediato", "jefe directo"]},
    "id_supervisor":       {"label": "ID sistema supervisor",
                             "candidates": ["id de sistema del usuario supervisor", "id sistema supervisor", "id supervisor"]},
    "cargo":               {"label": "Nombre de cargo",
                             "candidates": ["codigo de cargo nombre de cargo", "nombre de cargo", "cargo"]},
    "tipo_cargo":          {"label": "Tipo de cargo",
                             "candidates": ["tipo de cargo"]},
    "tipo_contrato":       {"label": "Tipo de contrato",
                             "candidates": ["tipo de contrato"]},
    "grupo_personal":      {"label": "Grupo de personal",
                             "candidates": ["grupo de personal"]},
    "areas_personal":      {"label": "Áreas de personal",
                             "candidates": ["areas de personal", "area de personal"]},
    "fecha_ingreso":       {"label": "Fecha de ingreso",
                             "candidates": ["detalles de empleo fecha de ingreso", "fecha de ingreso", "fecha ingreso"]},
    "fecha_fin_contrato":  {"label": "Fecha fin de contrato",
                             "candidates": ["fecha fin de contrato", "fecha fin contrato"]},
    "fecha_terminacion":   {"label": "Fecha de terminación",
                             "candidates": ["detalles de empleo fecha de terminacion", "fecha de terminacion", "fecha terminacion", "fecha de retiro"]},
    "estado_empleado":     {"label": "Estado de empleado",
                             "candidates": ["estado de empleado", "estado"]},
    "agencia_nombre":      {"label": "Agencia / Ubicación física",
                             "candidates": ["agencia-ubicacion fisica nombre", "agencia ubicacion fisica nombre", "agencia"]},
    "ciudad":              {"label": "Ciudad",
                             "candidates": ["agencia-ubicacion fisica ciudad", "agencia ubicacion fisica ciudad", "ciudad"]},
    "sexo":                {"label": "Sexo",
                             "candidates": ["sexo", "genero"]},
    "estado_civil":        {"label": "Estado civil",
                             "candidates": ["estado civil"]},
    "estrato":             {"label": "Estrato",
                             "candidates": ["estrato"]},
    "tipo_sangre":         {"label": "Tipo de sangre",
                             "candidates": ["tipo de sangre", "rh"]},
    "nivel_educativo":     {"label": "Nivel educativo",
                             "candidates": ["nivel educativo maximo aprobado", "nivel educativo"]},
    "fecha_nacimiento":    {"label": "Fecha de nacimiento",
                             "candidates": ["fecha de nacimiento", "fecha nacimiento"]},
    "id_requisicion":      {"label": "ID de requisición",
                             "candidates": ["id de la requisicion", "id requisicion"]},
    "tipo_requisicion":    {"label": "Tipo de requisición",
                             "candidates": ["tipo de requisicion"]},
    "pesv":                {"label": "Información PESV",
                             "candidates": ["informacion pesv", "pesv", "rol conductor"]},
}

DATE_FIELDS = ["fecha_ingreso", "fecha_fin_contrato", "fecha_terminacion", "fecha_nacimiento"]

SENTINEL_DATES = {pd.Timestamp("1900-01-01"), pd.Timestamp("9999-12-31"), pd.Timestamp("1899-12-30")}


def normalize(text) -> str:
    """Minúsculas, sin tildes, sin espacios extra — para comparar nombres de columnas."""
    if text is None:
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = " ".join(text.split())
    return text


def auto_map_columns(actual_columns) -> dict:
    """
    Intenta emparejar automáticamente las columnas del archivo cargado con las
    columnas internas esperadas. Devuelve {clave_interna: nombre_columna_real | None}.
    """
    normalized_actual = {normalize(c): c for c in actual_columns}
    mapping = {}
    for key, meta in EXPECTED_COLUMNS.items():
        found = None
        # 1) coincidencia exacta normalizada
        for cand in meta["candidates"]:
            if cand in normalized_actual:
                found = normalized_actual[cand]
                break
        # 2) coincidencia parcial (contiene / está contenido)
        if not found:
            for norm_col, orig_col in normalized_actual.items():
                if any(cand in norm_col or norm_col in cand for cand in meta["candidates"]):
                    found = orig_col
                    break
        # 3) fuzzy matching con difflib
        if not found:
            best = difflib.get_close_matches(meta["candidates"][0], list(normalized_actual.keys()), n=1, cutoff=0.72)
            if best:
                found = normalized_actual[best[0]]
        mapping[key] = found
    return mapping


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Renombra columnas del df original a las claves internas, según el mapeo confirmado."""
    rename = {v: k for k, v in mapping.items() if v is not None and v in df.columns}
    out = df.rename(columns=rename).copy()
    for key in EXPECTED_COLUMNS:
        if key not in out.columns:
            out[key] = np.nan
    return out


def coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte las columnas de fecha a datetime, tolerando formatos mixtos."""
    out = df.copy()
    for col in DATE_FIELDS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce", dayfirst=True)
    return out


def is_sentinel(ts) -> bool:
    if pd.isna(ts):
        return False
    return pd.Timestamp(ts).normalize() in SENTINEL_DATES


def clean_sentinels(series: pd.Series) -> pd.Series:
    """Devuelve la serie con las fechas centinela reemplazadas por NaT."""
    return series.apply(lambda x: pd.NaT if is_sentinel(x) else x)


def compute_age(fecha_nacimiento: pd.Series, ref_date=None) -> pd.Series:
    if ref_date is None:
        ref_date = pd.Timestamp(date.today())
    fn = clean_sentinels(fecha_nacimiento)
    age = (ref_date - fn).dt.days / 365.25
    return age


def compute_tenure_days(row_fecha_ingreso, row_fecha_terminacion, estado, ref_date=None) -> float:
    if ref_date is None:
        ref_date = pd.Timestamp(date.today())
    if pd.isna(row_fecha_ingreso):
        return np.nan
    end = row_fecha_terminacion if pd.notna(row_fecha_terminacion) else ref_date
    return (end - row_fecha_ingreso).days


def compute_tenure(df: pd.DataFrame, ref_date=None) -> pd.Series:
    """Antigüedad en años: hasta hoy para activos, hasta fecha de terminación para retirados."""
    if ref_date is None:
        ref_date = pd.Timestamp(date.today())
    fi = clean_sentinels(df["fecha_ingreso"])
    ft = clean_sentinels(df["fecha_terminacion"])
    end = ft.where(ft.notna(), ref_date)
    tenure_days = (end - fi).dt.days
    return tenure_days / 365.25


def is_activo(estado_series: pd.Series) -> pd.Series:
    s = estado_series.astype(str).str.strip().str.lower()
    activos_labels = {"activo", "vigente", "active"}
    return s.isin(activos_labels)


# ---------------------------------------------------------------------------
# Filtros globales
# ---------------------------------------------------------------------------
def get_filter_options(df: pd.DataFrame) -> dict:
    opts = {}
    if "fecha_ingreso" in df.columns:
        fi = clean_sentinels(df["fecha_ingreso"]).dropna()
        opts["fecha_min"] = fi.min().date() if not fi.empty else date(2000, 1, 1)
        opts["fecha_max"] = fi.max().date() if not fi.empty else date.today()
    opts["uen"] = sorted([x for x in df.get("uen", pd.Series(dtype=object)).dropna().unique()])
    opts["estado"] = sorted([x for x in df.get("estado_empleado", pd.Series(dtype=object)).dropna().unique()])
    opts["ciudad"] = sorted([x for x in df.get("ciudad", pd.Series(dtype=object)).dropna().unique()])
    opts["agencia"] = sorted([x for x in df.get("agencia_nombre", pd.Series(dtype=object)).dropna().unique()])
    opts["division"] = sorted([x for x in df.get("division", pd.Series(dtype=object)).dropna().unique()])
    return opts


def apply_global_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    if filters.get("fecha_rango") and "fecha_ingreso" in out.columns:
        d0, d1 = filters["fecha_rango"]
        fi = clean_sentinels(out["fecha_ingreso"])
        mask = fi.isna() | ((fi.dt.date >= d0) & (fi.dt.date <= d1))
        out = out[mask]
    if filters.get("uen"):
        out = out[out["uen"].isin(filters["uen"])]
    if filters.get("estado"):
        out = out[out["estado_empleado"].isin(filters["estado"])]
    if filters.get("ciudad"):
        out = out[out["ciudad"].isin(filters["ciudad"])]
    if filters.get("agencia"):
        out = out[out["agencia_nombre"].isin(filters["agencia"])]
    if filters.get("division"):
        out = out[out["division"].isin(filters["division"])]
    return out


def add_pct_column(count_df: pd.DataFrame, value_col: str, pct_col: str = "% del total") -> pd.DataFrame:
    """Agrega una columna de porcentaje sobre el total de la tabla de conteos dada."""
    out = count_df.copy()
    total = out[value_col].sum()
    out[pct_col] = (out[value_col] / total * 100).round(1) if total else 0.0
    return out


def crosstab_pct(index_series: pd.Series, col_series: pd.Series, normalize: str = "index") -> pd.DataFrame:
    """Tabla cruzada en porcentaje (redondeado a 1 decimal), normalizada por fila ('index') o columna ('columns')."""
    tab = pd.crosstab(index_series, col_series, normalize=normalize) * 100
    return tab.round(1)


def kpi_card_row(st, items):
    """items: lista de tuplas (etiqueta, valor, ayuda_opcional)"""
    cols = st.columns(len(items))
    for c, item in zip(cols, items):
        label, value = item[0], item[1]
        help_text = item[2] if len(item) > 2 else None
        c.metric(label, value, help=help_text)


def pct(n, d):
    return 0.0 if not d else round(100 * n / d, 1)
