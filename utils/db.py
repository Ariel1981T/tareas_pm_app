"""
Capa de acceso a datos: Supabase.

Requiere en .streamlit/secrets.toml:

[supabase]
url = "https://xxxx.supabase.co"
key = "xxxx"
"""

import streamlit as st
from supabase import create_client, Client
from datetime import date

from utils import google_tasks


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# --------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------
def obtener_usuarios(rol: str = None):
    sb = get_client()
    q = sb.table("usuarios").select("*").eq("activo", True)
    if rol:
        q = q.eq("rol", rol)
    return q.execute().data


def obtener_usuario_por_correo(correo: str):
    sb = get_client()
    res = sb.table("usuarios").select("*").eq("correo", correo).execute().data
    return res[0] if res else None


# --------------------------------------------------------------
# Tareas
# --------------------------------------------------------------
def crear_tarea(datos: dict, gerente_correo: str = None):
    """
    Crea la tarea en Supabase (fuente de verdad) y, si se indica el correo
    del gerente, intenta crear la tarea espejo en su Google Tasks.
    Un fallo en Google Tasks NUNCA bloquea la creación en Supabase.
    """
    sb = get_client()
    creada = sb.table("tareas").insert(datos).execute().data
    if not creada:
        return creada

    tarea = creada[0]

    if gerente_correo:
        resultado = google_tasks.crear_tarea_google(
            gerente_correo=gerente_correo,
            titulo=tarea["titulo"],
            descripcion=tarea.get("descripcion"),
            fecha_vencimiento=date.fromisoformat(tarea["fecha_vencimiento"]),
            folio=tarea["folio"],
        )
        cambios_sync = {}
        if resultado["ok"]:
            cambios_sync = {
                "google_task_id": resultado["task_id"],
                "google_tasklist_id": resultado["tasklist_id"],
                "google_sync_error": None,
            }
        else:
            cambios_sync = {"google_sync_error": resultado["error"]}
        sb.table("tareas").update(cambios_sync).eq("id", tarea["id"]).execute()
        tarea.update(cambios_sync)

    return [tarea]


def obtener_tareas(gerente_id: str = None, estado: str = None):
    sb = get_client()
    q = sb.table("tareas").select("*, gerente:gerente_id(nombre, correo), pm:project_manager_id(nombre)")
    if gerente_id:
        q = q.eq("gerente_id", gerente_id)
    if estado:
        q = q.eq("estado", estado)
    return q.order("fecha_vencimiento").execute().data


def obtener_tarea(tarea_id: str):
    sb = get_client()
    res = sb.table("tareas").select("*").eq("id", tarea_id).execute().data
    return res[0] if res else None


def actualizar_tarea(tarea_id: str, cambios: dict, usuario_id: str = None, nota: str = None):
    sb = get_client()
    tarea_actual = obtener_tarea(tarea_id)
    cambios["actualizado_en"] = "now()"
    sb.table("tareas").update(cambios).eq("id", tarea_id).execute()

    if "estado" in cambios and tarea_actual:
        sb.table("tareas_historial").insert({
            "tarea_id": tarea_id,
            "estado_anterior": tarea_actual.get("estado"),
            "estado_nuevo": cambios["estado"],
            "cambiado_por": usuario_id,
            "nota": nota,
        }).execute()


def clasificar_prioridad(tarea_id: str, prioridad: str):
    return actualizar_tarea(tarea_id, {"prioridad": prioridad})


def solicitar_cierre(tarea_id: str, fecha_real_termino: date, usuario_id: str):
    return actualizar_tarea(
        tarea_id,
        {"estado": "Solicitud de cierre", "fecha_real_termino": str(fecha_real_termino)},
        usuario_id=usuario_id,
        nota="Gerente solicita cierre",
    )


def cerrar_tarea(tarea_id: str, usuario_id: str, fecha_real_termino: date = None,
                  gerente_correo: str = None):
    tarea = obtener_tarea(tarea_id)
    cambios = {"estado": "Cerrada"}
    if fecha_real_termino:
        cambios["fecha_real_termino"] = str(fecha_real_termino)
    actualizar_tarea(tarea_id, cambios, usuario_id=usuario_id, nota="PM cierra la tarea")

    if gerente_correo and tarea and tarea.get("google_task_id"):
        google_tasks.marcar_completada_google(
            gerente_correo, tarea["google_tasklist_id"], tarea["google_task_id"]
        )


# --------------------------------------------------------------
# Aplazamientos
# --------------------------------------------------------------
def solicitar_aplazamiento(tarea_id: str, fecha_actual: date, fecha_solicitada: date,
                             motivo: str, usuario_id: str):
    sb = get_client()
    return sb.table("aplazamientos").insert({
        "tarea_id": tarea_id,
        "fecha_vencimiento_anterior": str(fecha_actual),
        "fecha_vencimiento_solicitada": str(fecha_solicitada),
        "motivo": motivo,
        "solicitado_por": usuario_id,
    }).execute().data


def obtener_aplazamientos_pendientes():
    sb = get_client()
    return (
        sb.table("aplazamientos")
        .select("*, tarea:tarea_id(folio, titulo), solicitante:solicitado_por(nombre)")
        .eq("estado", "Pendiente")
        .execute()
        .data
    )


def resolver_aplazamiento(aplazamiento_id: str, aprobado: bool, usuario_id: str, comentario: str = None):
    sb = get_client()
    aplazamiento = sb.table("aplazamientos").select("*").eq("id", aplazamiento_id).execute().data[0]

    nuevo_estado = "Aprobado" if aprobado else "Rechazado"
    sb.table("aplazamientos").update({
        "estado": nuevo_estado,
        "resuelto_por": usuario_id,
        "resuelto_en": "now()",
        "comentario_resolucion": comentario,
    }).eq("id", aplazamiento_id).execute()

    if aprobado:
        actualizar_tarea(
            aplazamiento["tarea_id"],
            {"fecha_vencimiento": aplazamiento["fecha_vencimiento_solicitada"]},
            usuario_id=usuario_id,
            nota=f"Aplazamiento aprobado: {aplazamiento['motivo']}",
        )
        tarea = obtener_tarea(aplazamiento["tarea_id"])
        if tarea and tarea.get("google_task_id"):
            gerente = sb.table("usuarios").select("correo").eq("id", tarea["gerente_id"]).execute().data
            if gerente:
                google_tasks.actualizar_fecha_google(
                    gerente[0]["correo"], tarea["google_tasklist_id"], tarea["google_task_id"],
                    date.fromisoformat(aplazamiento["fecha_vencimiento_solicitada"]),
                )
