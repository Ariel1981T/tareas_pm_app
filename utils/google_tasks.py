"""
Integración con Google Tasks API (Fase 1 - un solo sentido: Streamlit -> Tasks).

Usa una cuenta de servicio de Google Cloud con delegación de dominio completo
(domain-wide delegation) para actuar EN NOMBRE de cada gerente y escribir
en SU lista de Google Tasks personal, sin que cada gerente tenga que
autorizar manualmente.

Requiere en .streamlit/secrets.toml, la sección [google_service_account]
con el contenido íntegro del JSON descargado al crear la cuenta de servicio
en Google Cloud Console (ver guía paso a paso).

Importante (por diseño, confirmado con el usuario):
- Esto es de UN SOLO SENTIDO. Lo que el gerente haga directo en la app de
  Google Tasks (ej. marcarla como completada) NO se refleja de vuelta en
  Streamlit. El cierre oficial de una tarea SOLO ocurre dentro de Streamlit.
- Si falla la sincronización con Google, la operación en Supabase (fuente
  de verdad) igual se completa; el error se guarda en `google_sync_error`
  para revisión, sin bloquear al usuario.
"""

from datetime import date
from typing import Optional

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/tasks"]

# Título de la lista de tareas que se crea/usa dentro de la cuenta del gerente
NOMBRE_LISTA = "IMEMSA · Tareas asignadas"


def _credenciales_para(gerente_correo: str):
    """Crea credenciales de la cuenta de servicio, impersonando al gerente."""
    info = dict(st.secrets["google_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES, subject=gerente_correo
    )
    return creds


def _servicio_tasks(gerente_correo: str):
    creds = _credenciales_para(gerente_correo)
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


@st.cache_data(ttl=3600, show_spinner=False)
def _obtener_o_crear_lista(gerente_correo: str) -> str:
    """Devuelve el ID de la lista 'IMEMSA · Tareas asignadas' en la cuenta
    del gerente, creándola la primera vez."""
    servicio = _servicio_tasks(gerente_correo)
    listas = servicio.tasklists().list().execute().get("items", [])
    for lista in listas:
        if lista["title"] == NOMBRE_LISTA:
            return lista["id"]
    nueva = servicio.tasklists().insert(body={"title": NOMBRE_LISTA}).execute()
    return nueva["id"]


def crear_tarea_google(gerente_correo: str, titulo: str, descripcion: str,
                        fecha_vencimiento: date, folio: str) -> dict:
    """
    Crea la tarea espejo en la cuenta de Google Tasks del gerente.
    Devuelve {"ok": bool, "tasklist_id": str, "task_id": str, "error": str}
    """
    try:
        tasklist_id = _obtener_o_crear_lista(gerente_correo)
        servicio = _servicio_tasks(gerente_correo)
        cuerpo = {
            "title": f"[{folio}] {titulo}",
            "notes": (descripcion or "") + "\n\n⚠️ El cierre de esta tarea se confirma en Streamlit, "
                                            "no marcándola aquí como completada.",
            # Google Tasks solo acepta fecha (hora fija a medianoche UTC)
            "due": f"{fecha_vencimiento.isoformat()}T00:00:00.000Z",
        }
        creada = servicio.tasks().insert(tasklist=tasklist_id, body=cuerpo).execute()
        return {"ok": True, "tasklist_id": tasklist_id, "task_id": creada["id"], "error": None}
    except HttpError as e:
        return {"ok": False, "tasklist_id": None, "task_id": None, "error": str(e)}
    except Exception as e:
        return {"ok": False, "tasklist_id": None, "task_id": None, "error": str(e)}


def actualizar_fecha_google(gerente_correo: str, tasklist_id: str, task_id: str,
                             nueva_fecha_vencimiento: date) -> dict:
    """Usado cuando se aprueba un aplazamiento."""
    try:
        servicio = _servicio_tasks(gerente_correo)
        servicio.tasks().patch(
            tasklist=tasklist_id,
            task=task_id,
            body={"due": f"{nueva_fecha_vencimiento.isoformat()}T00:00:00.000Z"},
        ).execute()
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def marcar_completada_google(gerente_correo: str, tasklist_id: str, task_id: str) -> dict:
    """Usado cuando el PM cierra la tarea en Streamlit -> se refleja como
    completada en la app de Tasks del gerente, informativamente."""
    try:
        servicio = _servicio_tasks(gerente_correo)
        servicio.tasks().patch(
            tasklist=tasklist_id, task=task_id, body={"status": "completed"}
        ).execute()
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def eliminar_tarea_google(gerente_correo: str, tasklist_id: str, task_id: str) -> dict:
    """Usado si una tarea se cancela."""
    try:
        servicio = _servicio_tasks(gerente_correo)
        servicio.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
