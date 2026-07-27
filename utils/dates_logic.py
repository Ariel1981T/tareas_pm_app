"""
Lógica de fechas y semáforo para el Sistema de Tareas PM → Gerentes.

Basado en las reglas de negocio del archivo de parámetros del usuario:

- Tarea ABIERTA y con atraso:
    días_atraso = HOY - fecha_vencimiento

- Tarea CERRADA en tiempo:
    fecha_real_termino <= fecha_vencimiento

- Tarea CERRADA fuera de tiempo:
    días_excedente = fecha_real_termino - fecha_vencimiento

Nota clave del usuario: la fecha real de término NO siempre coincide con la
fecha de cierre en el sistema (a veces el gerente o el PM cierran después).
Por eso fecha_real_termino se captura y edita de forma independiente.
"""

from datetime import date
from dataclasses import dataclass
from typing import Optional


# Umbrales del semáforo (confirmados por el usuario)
DIAS_ALERTA_AMARILLA = 3


@dataclass
class EstadoSemaforo:
    color: str          # "verde" | "amarillo" | "rojo"
    etiqueta: str        # texto para mostrar en UI
    dias: Optional[int]  # días de atraso o excedente (positivo), o días restantes


def calcular_estado_tarea(
    estado: str,
    fecha_vencimiento: date,
    fecha_real_termino: Optional[date],
    hoy: Optional[date] = None,
) -> EstadoSemaforo:
    """
    Calcula el semáforo y los días de atraso/excedente/restantes de una tarea.

    estado: 'Abierta', 'Solicitud de cierre', 'Cerrada', 'Cancelada'
    """
    if hoy is None:
        hoy = date.today()

    # --- Tarea cerrada -------------------------------------------------
    if estado == "Cerrada" and fecha_real_termino is not None:
        dias_excedente = (fecha_real_termino - fecha_vencimiento).days
        if dias_excedente <= 0:
            # Se finalizó en tiempo
            return EstadoSemaforo(
                color="verde",
                etiqueta="Cerrada en tiempo",
                dias=dias_excedente,  # negativo o cero = días de margen
            )
        else:
            # Se finalizó fuera de tiempo
            return EstadoSemaforo(
                color="rojo",
                etiqueta=f"Cerrada con {dias_excedente} día(s) de exceso",
                dias=dias_excedente,
            )

    # --- Tarea abierta o en solicitud de cierre -------------------------
    dias_restantes = (fecha_vencimiento - hoy).days

    if dias_restantes < 0:
        # Vencida y sigue abierta -> atraso
        dias_atraso = -dias_restantes
        return EstadoSemaforo(
            color="rojo",
            etiqueta=f"Vencida, {dias_atraso} día(s) de atraso",
            dias=dias_atraso,
        )
    elif dias_restantes <= DIAS_ALERTA_AMARILLA:
        return EstadoSemaforo(
            color="amarillo",
            etiqueta=f"Vence en {dias_restantes} día(s)",
            dias=dias_restantes,
        )
    else:
        return EstadoSemaforo(
            color="verde",
            etiqueta=f"En tiempo ({dias_restantes} días restantes)",
            dias=dias_restantes,
        )


def semaforo_emoji(color: str) -> str:
    return {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}.get(color, "⚪")
