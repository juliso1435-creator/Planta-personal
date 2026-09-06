# Dashboard de Gestión Humana – Corbeta

Aplicación Streamlit para análisis integral de headcount, rotación, demografía y
estructura organizacional, a partir del archivo de colaboradores (CSV/XLSX/XLS).

## Instalación

```bash
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Se abrirá en el navegador (por defecto `http://localhost:8501`).

## Uso

1. **Pestaña 0️⃣ Carga y calidad**: sube el archivo, selecciona la hoja (si es Excel),
   confirma el mapeo de columnas y revisa el panel de calidad de datos.
2. Usa los **filtros globales** en la barra lateral (fecha de ingreso, UEN, Estado,
   Ciudad) — se aplican automáticamente a las pestañas 1 a 9.
3. Navega por las pestañas 1️⃣ a 8️⃣ para el análisis detallado.
4. En **9️⃣ Exportar** descarga el Excel consolidado o el resumen ejecutivo en PDF.

## Estructura del proyecto

```
app.py                  # Orquestador principal (pestañas, sidebar, sesión)
modules/
  utils.py              # Mapeo de columnas, fechas, antigüedad, filtros
  data_loader.py         # Carga de CSV/XLSX/XLS
  quality_checks.py      # Panel de calidad de datos (pestaña 0)
  headcount.py           # Pestaña 1
  rotacion.py             # Pestaña 2
  geografia.py            # Pestaña 3
  vinculacion.py          # Pestaña 4
  demografia.py           # Pestaña 5
  reclutamiento.py        # Pestaña 6
  estructura.py           # Pestaña 7
  pesv.py                 # Pestaña 8
  exportar.py             # Pestaña 9
requirements.txt
```

## Notas

- Si los nombres de columnas de tu archivo no coinciden exactamente con los
  esperados, la app intenta emparejarlos automáticamente y siempre te deja
  corregir el mapeo manualmente antes de continuar.
- Las fechas centinela (`1900-01-01`, `9999-12-31`) se excluyen automáticamente
  de los cálculos de edad y antigüedad, y se reportan en el panel de calidad.
- El export a PDF usa `kaleido` para renderizar gráficos de Plotly como imagen;
  si no está instalado, el botón mostrará un mensaje de error indicando cómo
  resolverlo.
- Con ~14.500 filas la app debería responder con fluidez gracias al cacheo
  (`st.cache_data`) de la carga y el procesamiento pesado.
