"""
Notificaciones salientes:
- Google Chat: vía webhook entrante de un espacio (Space).
- Gmail SMTP: como respaldo / notificación formal por correo.

Requiere en .streamlit/secrets.toml:

[google_chat]
webhook_url = "https://chat.googleapis.com/v1/spaces/XXX/messages?key=...&token=..."

[gmail]
usuario = "notificaciones@imemsa.com"
password = "app-password-de-16-digitos"
"""

import requests
import smtplib
from email.mime.text import MIMEText
import streamlit as st


def enviar_a_chat(mensaje: str):
    """Envía un mensaje de texto simple al espacio de Google Chat configurado."""
    webhook_url = st.secrets.get("google_chat", {}).get("webhook_url")
    if not webhook_url:
        return False
    try:
        requests.post(webhook_url, json={"text": mensaje}, timeout=10)
        return True
    except requests.RequestException:
        return False


def notificar_nueva_tarea(folio: str, titulo: str, gerente_nombre: str, fecha_vencimiento: str):
    mensaje = (
        f"📋 *Nueva tarea asignada* ({folio})\n"
        f"*{titulo}*\n"
        f"Gerente: {gerente_nombre}\n"
        f"Vence: {fecha_vencimiento}"
    )
    enviar_a_chat(mensaje)


def notificar_solicitud_cierre(folio: str, titulo: str, gerente_nombre: str):
    mensaje = (
        f"✅ *Solicitud de cierre* ({folio})\n"
        f"*{titulo}*\n"
        f"Solicitada por: {gerente_nombre}"
    )
    enviar_a_chat(mensaje)


def notificar_solicitud_aplazamiento(folio: str, titulo: str, gerente_nombre: str,
                                       fecha_actual: str, fecha_solicitada: str, motivo: str):
    mensaje = (
        f"🕒 *Solicitud de aplazamiento* ({folio})\n"
        f"*{titulo}*\n"
        f"Solicitada por: {gerente_nombre}\n"
        f"Fecha actual: {fecha_actual} → Fecha solicitada: {fecha_solicitada}\n"
        f"Motivo: {motivo}"
    )
    enviar_a_chat(mensaje)


def notificar_tarea_vencida(folio: str, titulo: str, gerente_nombre: str, dias_atraso: int):
    mensaje = (
        f"🔴 *Tarea vencida* ({folio})\n"
        f"*{titulo}*\n"
        f"Gerente: {gerente_nombre}\n"
        f"Días de atraso: {dias_atraso}"
    )
    enviar_a_chat(mensaje)


def enviar_correo(destinatario: str, asunto: str, cuerpo: str):
    """Envía un correo simple vía Gmail SMTP."""
    cfg = st.secrets.get("gmail", {})
    usuario = cfg.get("usuario")
    password = cfg.get("password")
    if not usuario or not password:
        return False

    msg = MIMEText(cuerpo, "plain", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = usuario
    msg["To"] = destinatario

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(usuario, password)
            server.sendmail(usuario, [destinatario], msg.as_string())
        return True
    except Exception:
        return False
