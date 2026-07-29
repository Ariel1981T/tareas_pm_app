"""
Reporte de Tareas · IMEMSA

App de una sola pantalla: lee TODAS las listas de Google Tasks de la
cuenta del Project Manager (una lista = un gerente) y genera un Excel
descargable con el detalle completo.

Es de SOLO LECTURA — nunca escribe ni modifica nada en Tasks.

Requiere en .streamlit/secrets.toml:

[google_oauth]
client_id = "..."
client_secret = "..."
refresh_token = "..."
"""

import io
from datetime import datetime, date

import streamlit as st
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

NAVY = "0D2B6E"
RED = "C41E2E"

st.set_page_config(page_title="IMEMSA · Reporte de Tareas", page_icon="📊", layout="centered")

st.markdown("""
<style>
    h1, h2, h3 { color: #0D2B6E; }
    div.stButton > button:first-child, div.stDownloadButton > button:first-child {
        background-color: #0D2B6E; color: white; border-radius: 6px; border: none;
    }
    div.stButton > button:first-child:hover, div.stDownloadButton > button:first-child:hover {
        background-color: #C41E2E;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Reporte de Tareas · IMEMSA")
st.caption("Extrae todas las tareas de Google Tasks (una lista por gerente) y genera un Excel.")


# --------------------------------------------------------------
# Conexión de solo lectura a Google Tasks
# --------------------------------------------------------------
@st.cache_resource
def obtener_servicio():
    cfg = st.secrets["google_oauth"]
    creds = Credentials(
        token=None,
        refresh_token=cfg["refresh_token"],
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/tasks.readonly"],
    )
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


def parsear_fecha(valor_rfc3339):
    if not valor_rfc3339:
        return None
    return datetime.fromisoformat(valor_rfc3339.replace("Z", "+00:00")).date()


def calcular_semaforo(estado, fecha_vencimiento, fecha_completado, hoy=None):
    hoy = hoy or date.today()
    if estado == "completed":
        if fecha_completado and fecha_vencimiento:
            return "Cerrada en tiempo" if fecha_completado <= fecha_vencimiento else "Cerrada con atraso"
        return "Cerrada"
    if fecha_vencimiento:
        dias = (fecha_vencimiento - hoy).days
        if dias < 0:
            return f"Vencida ({-dias} días de atraso)"
        elif dias <= 3:
            return f"Por vencer ({dias} días)"
        return "En tiempo"
    return "Sin fecha"


@st.cache_data(ttl=120, show_spinner=False)
def extraer_todas_las_tareas():
    servicio = obtener_servicio()
    listas = servicio.tasklists().list(maxResults=100).execute().get("items", [])

    filas = []
    for lista in listas:
        gerente = lista["title"]
        pagina = None
        while True:
            resp = servicio.tasks().list(
                tasklist=lista["id"], showCompleted=True, showHidden=True,
                maxResults=100, pageToken=pagina,
            ).execute()
            for t in resp.get("items", []):
                fecha_venc = parsear_fecha(t.get("due"))
                fecha_completado = parsear_fecha(t.get("completed"))
                filas.append({
                    "Gerente": gerente,
                    "Tarea": t.get("title", "(sin título)"),
                    "Notas": t.get("notes", ""),
                    "Fecha de vencimiento": fecha_venc,
                    "Estado Google Tasks": "Completada" if t.get("status") == "completed" else "Pendiente",
                    "Fecha de completado": fecha_completado,
                    "Semáforo": calcular_semaforo(t.get("status"), fecha_venc, fecha_completado),
                })
            pagina = resp.get("nextPageToken")
            if not pagina:
                break
    return pd.DataFrame(filas)


def generar_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Tareas", index=False)
        hoja = writer.sheets["Tareas"]

        # Encabezado con estilo IMEMSA
        for col_idx, col_name in enumerate(df.columns, start=1):
            celda = hoja.cell(row=1, column=col_idx)
            celda.font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
            celda.fill = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
            celda.alignment = Alignment(horizontal="center", vertical="center")

        # Fuente Arial en todo el cuerpo + ancho de columna automático
        for col_idx, col_name in enumerate(df.columns, start=1):
            letra = get_column_letter(col_idx)
            max_len = max([len(str(col_name))] + [len(str(v)) for v in df[col_name].fillna("")])
            hoja.column_dimensions[letra].width = min(max_len + 3, 45)
            for row_idx in range(2, len(df) + 2):
                hoja.cell(row=row_idx, column=col_idx).font = Font(name="Arial", size=10.5)

        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions

    return buffer.getvalue()


# --------------------------------------------------------------
# UI
# --------------------------------------------------------------
if st.button("🔄 Generar reporte"):
    with st.spinner("Leyendo listas de Google Tasks..."):
        try:
            df = extraer_todas_las_tareas()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Tasks: {e}")
            st.stop()

    if df.empty:
        st.warning("No se encontraron tareas en ninguna lista.")
    else:
        st.success(f"Se encontraron {len(df)} tareas en {df['Gerente'].nunique()} lista(s)/gerente(s).")
        st.dataframe(df, use_container_width=True, hide_index=True)

        excel_bytes = generar_excel(df)
        st.download_button(
            "⬇️ Descargar Excel",
            data=excel_bytes,
            file_name=f"reporte_tareas_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
