"""
Pestaña 0 (parte 2): panel de calidad de datos.
Cada chequeo devuelve un dict: {nombre, descripcion, conteo, df_afectados}
"""
import pandas as pd
import numpy as np
import streamlit as st

from modules.utils import is_sentinel, is_activo


def check_duplicados(df: pd.DataFrame) -> dict:
    dup_mask = df["codigo_empleado"].duplicated(keep=False) & df["codigo_empleado"].notna()
    afectados = df[dup_mask].sort_values("codigo_empleado")
    return {
        "nombre": "Códigos de empleado duplicados",
        "descripcion": "Registros que comparten el mismo Código de empleado.",
        "conteo": int(df.loc[dup_mask, "codigo_empleado"].nunique()),
        "filas_afectadas": len(afectados),
        "df": afectados,
    }


def check_fechas_centinela(df: pd.DataFrame) -> dict:
    campos = ["fecha_ingreso", "fecha_fin_contrato", "fecha_terminacion", "fecha_nacimiento"]
    mask = pd.Series(False, index=df.index)
    for c in campos:
        if c in df.columns:
            mask = mask | df[c].apply(is_sentinel)
    afectados = df[mask]
    return {
        "nombre": "Fechas centinela (1900-01-01 / 9999-12-31)",
        "descripcion": "Registros con al menos una fecha claramente inválida usada como marcador.",
        "conteo": int(mask.sum()),
        "filas_afectadas": len(afectados),
        "df": afectados,
    }


def check_estado_vs_fechas(df: pd.DataFrame) -> dict:
    activo = is_activo(df["estado_empleado"])
    tiene_terminacion = df["fecha_terminacion"].notna() & ~df["fecha_terminacion"].apply(is_sentinel)
    # activo con fecha de terminación diligenciada, o retirado sin fecha de terminación
    inconsistente = (activo & tiene_terminacion) | (~activo & ~tiene_terminacion & df["estado_empleado"].notna())
    afectados = df[inconsistente]
    return {
        "nombre": "Estado de empleado inconsistente con fechas",
        "descripcion": "Activos con fecha de terminación diligenciada, o retirados sin fecha de terminación.",
        "conteo": int(inconsistente.sum()),
        "filas_afectadas": len(afectados),
        "df": afectados,
    }


def check_edades_fuera_rango(df: pd.DataFrame, edad_min=16, edad_max=80) -> dict:
    from modules.utils import compute_age
    edad = compute_age(df["fecha_nacimiento"])
    mask = edad.notna() & ((edad < edad_min) | (edad > edad_max))
    afectados = df[mask].assign(edad_calculada=edad[mask].round(1))
    return {
        "nombre": f"Edades fuera de rango lógico (<{edad_min} o >{edad_max} años)",
        "descripcion": "Calculadas a partir de Fecha de nacimiento, excluyendo fechas centinela.",
        "conteo": int(mask.sum()),
        "filas_afectadas": len(afectados),
        "df": afectados,
    }


def check_campos_clave_vacios(df: pd.DataFrame) -> dict:
    campos = ["codigo_empleado", "estado_empleado", "fecha_ingreso", "uen"]
    campos = [c for c in campos if c in df.columns]
    mask = pd.Series(False, index=df.index)
    for c in campos:
        mask = mask | df[c].isna()
    afectados = df[mask]
    return {
        "nombre": "Campos clave vacíos",
        "descripcion": "Faltan Código de empleado, Estado, Fecha de ingreso o UEN.",
        "conteo": int(mask.sum()),
        "filas_afectadas": len(afectados),
        "df": afectados,
    }


def run_all_checks(df: pd.DataFrame) -> list:
    return [
        check_duplicados(df),
        check_fechas_centinela(df),
        check_estado_vs_fechas(df),
        check_edades_fuera_rango(df),
        check_campos_clave_vacios(df),
    ]


def render(df: pd.DataFrame):
    st.subheader("🔍 Panel de calidad de datos")
    st.caption("Revisa estos hallazgos antes de continuar con el análisis. No bloquean la app, pero pueden afectar la exactitud de los resultados.")

    resultados = run_all_checks(df)
    total_filas = len(df)

    cols = st.columns(len(resultados))
    for c, r in zip(cols, resultados):
        c.metric(r["nombre"], r["conteo"])

    for r in resultados:
        with st.expander(f"{r['nombre']} — {r['conteo']} hallazgos ({r['filas_afectadas']} filas, {r['filas_afectadas']/total_filas*100:.1f}% del total)"):
            st.caption(r["descripcion"])
            if r["filas_afectadas"] > 0:
                cols_mostrar = [c for c in ["codigo_empleado", "nombre_completo", "estado_empleado",
                                             "fecha_ingreso", "fecha_terminacion", "fecha_nacimiento", "uen"]
                                 if c in r["df"].columns]
                st.dataframe(r["df"][cols_mostrar].head(500), use_container_width=True)
                csv = r["df"].to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"⬇️ Exportar filas afectadas ({r['nombre']})",
                    data=csv,
                    file_name=f"calidad_{r['nombre'][:30].lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"dl_{r['nombre']}",
                )
            else:
                st.success("Sin hallazgos para este chequeo.")
