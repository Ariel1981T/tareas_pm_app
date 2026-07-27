"""
VERSIÓN DEMO — Sistema de Tareas PM · IMEMSA

No requiere Supabase, Google Chat ni Google Tasks configurados.
Todos los datos viven en memoria (st.session_state) solo para poder
ver y navegar la interfaz. Al recargar la página se reinicia el demo.

Cuando tengan las credenciales reales listas, el archivo a usar en
Streamlit Cloud es `app.py` (la versión conectada a Supabase),
no este.
"""

import streamlit as st
from datetime import date, timedelta
import pandas as pd

from utils.dates_logic import calcular_estado_tarea, semaforo_emoji

st.set_page_config(page_title="IMEMSA · Tareas (DEMO)", page_icon="📋", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f4f6fb; }
    h1, h2, h3 { color: #0D2B6E; }
    .semaforo-verde { color: #1a8f3c; font-weight: 600; }
    .semaforo-amarillo { color: #b8860b; font-weight: 600; }
    .semaforo-rojo { color: #C41E2E; font-weight: 600; }
    div.stButton > button:first-child {
        background-color: #0D2B6E; color: white; border-radius: 6px; border: none;
    }
    div.stButton > button:first-child:hover { background-color: #C41E2E; }
    .banner-demo {
        background-color: #C41E2E; color: white; padding: 8px 16px;
        border-radius: 6px; font-weight: 600; text-align: center; margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="banner-demo">🧪 MODO DEMO — datos de ejemplo, no conectado a Supabase/Chat/Tasks</div>',
            unsafe_allow_html=True)

# ----------------------------------------------------------------
# Datos de ejemplo (en memoria)
# ----------------------------------------------------------------
HOY = date.today()

if "usuarios_demo" not in st.session_state:
    st.session_state["usuarios_demo"] = [
        {"id": "u1", "nombre": "Ariel Teodocio", "correo": "ariel@imemsa.com", "rol": "PM"},
        {"id": "u2", "nombre": "Rodrigo Herrera", "correo": "rodrigo@imemsa.com", "rol": "Gerente"},
        {"id": "u3", "nombre": "Florentino Pérez", "correo": "florentino@imemsa.com", "rol": "Gerente"},
    ]

if "tareas_demo" not in st.session_state:
    st.session_state["tareas_demo"] = [
        {
            "id": "t1", "folio": "TAR-2026-001", "titulo": "Actualizar layout de línea de laminado",
            "descripcion": "Ajustar distribución del área de vacuum infusion.",
            "gerente_id": "u2", "gerente_nombre": "Rodrigo Herrera",
            "prioridad": "Alta", "estado": "Abierta",
            "fecha_objetivo": HOY - timedelta(days=1), "fecha_vencimiento": HOY - timedelta(days=2),
            "fecha_real_termino": None,
        },
        {
            "id": "t2", "folio": "TAR-2026-002", "titulo": "Revisión de índice IIFC lote 45",
            "descripcion": "Validar resultados de control de calidad del lote 45.",
            "gerente_id": "u3", "gerente_nombre": "Florentino Pérez",
            "prioridad": "Media", "estado": "Abierta",
            "fecha_objetivo": HOY + timedelta(days=1), "fecha_vencimiento": HOY + timedelta(days=2),
            "fecha_real_termino": None,
        },
        {
            "id": "t3", "folio": "TAR-2026-003", "titulo": "Capacitación NOM-STPS área de gelcoat",
            "descripcion": "Sesión de seguridad ocupacional para el equipo de gelcoat.",
            "gerente_id": "u2", "gerente_nombre": "Rodrigo Herrera",
            "prioridad": None, "estado": "Abierta",
            "fecha_objetivo": HOY + timedelta(days=10), "fecha_vencimiento": HOY + timedelta(days=12),
            "fecha_real_termino": None,
        },
        {
            "id": "t4", "folio": "TAR-2026-004", "titulo": "Cierre de mantenimiento de molde M-12",
            "descripcion": "Confirmar cierre de mantenimiento preventivo.",
            "gerente_id": "u3", "gerente_nombre": "Florentino Pérez",
            "prioridad": "Baja", "estado": "Cerrada",
            "fecha_objetivo": HOY - timedelta(days=8), "fecha_vencimiento": HOY - timedelta(days=7),
            "fecha_real_termino": HOY - timedelta(days=9),
        },
        {
            "id": "t5", "folio": "TAR-2026-005", "titulo": "Reporte de exothermy semana 30",
            "descripcion": "Consolidar mediciones de exotermia de la semana.",
            "gerente_id": "u2", "gerente_nombre": "Rodrigo Herrera",
            "prioridad": "Media", "estado": "Cerrada",
            "fecha_objetivo": HOY - timedelta(days=4), "fecha_vencimiento": HOY - timedelta(days=3),
            "fecha_real_termino": HOY - timedelta(days=1),
        },
    ]

if "aplazamientos_demo" not in st.session_state:
    st.session_state["aplazamientos_demo"] = [
        {
            "id": "a1", "tarea_folio": "TAR-2026-002", "tarea_titulo": "Revisión de índice IIFC lote 45",
            "solicitante_nombre": "Florentino Pérez",
            "fecha_anterior": HOY + timedelta(days=2), "fecha_solicitada": HOY + timedelta(days=6),
            "motivo": "Se requiere reproceso de dos probetas antes de validar.",
        }
    ]

usuarios = st.session_state["usuarios_demo"]
tareas = st.session_state["tareas_demo"]
aplazamientos = st.session_state["aplazamientos_demo"]

# ----------------------------------------------------------------
# Login demo (elige un usuario de la lista, no valida contraseña)
# ----------------------------------------------------------------
if "usuario_demo" not in st.session_state:
    st.title("📋 Sistema de Tareas · IMEMSA (DEMO)")
    st.subheader("Selecciona con qué usuario quieres entrar")
    opciones = {f"{u['nombre']} ({u['rol']})": u for u in usuarios}
    seleccion = st.selectbox("Usuario de ejemplo", list(opciones.keys()))
    if st.button("Entrar"):
        st.session_state["usuario_demo"] = opciones[seleccion]
        st.rerun()
    st.stop()

usuario = st.session_state["usuario_demo"]

st.sidebar.markdown(f"**{usuario['nombre']}**")
st.sidebar.caption(usuario["rol"])
if st.sidebar.button("Cambiar de usuario"):
    del st.session_state["usuario_demo"]
    st.rerun()

if usuario["rol"] in ("PM", "Admin"):
    opciones_menu = ["Asignar tarea", "Aplazamientos pendientes", "Reporte por gerente", "Todas las tareas"]
else:
    opciones_menu = ["Mis tareas", "Solicitar aplazamiento"]

seccion = st.sidebar.radio("Menú", opciones_menu)

st.title("📋 Sistema de Tareas · IMEMSA (DEMO)")


def fila_tarea(t):
    est = calcular_estado_tarea(t["estado"], t["fecha_vencimiento"], t["fecha_real_termino"], HOY)
    return est


# ==================================================================
if seccion == "Asignar tarea":
    st.subheader("Asignar nueva tarea")
    gerentes = [u for u in usuarios if u["rol"] == "Gerente"]
    with st.form("nueva_tarea_demo"):
        titulo = st.text_input("Título de la tarea")
        descripcion = st.text_area("Descripción")
        gerente_sel = st.selectbox("Gerente responsable", gerentes, format_func=lambda g: g["nombre"])
        col1, col2 = st.columns(2)
        fecha_objetivo = col1.date_input("Fecha objetivo (interna)", value=None)
        fecha_vencimiento = col2.date_input("Fecha de vencimiento (compromiso formal)")
        enviar = st.form_submit_button("Asignar (demo)")
    if enviar:
        if not titulo or not fecha_vencimiento:
            st.error("Título y fecha de vencimiento son obligatorios.")
        else:
            folio = f"TAR-2026-{len(tareas) + 1:03d}"
            tareas.append({
                "id": f"t{len(tareas)+1}", "folio": folio, "titulo": titulo, "descripcion": descripcion,
                "gerente_id": gerente_sel["id"], "gerente_nombre": gerente_sel["nombre"],
                "prioridad": None, "estado": "Abierta",
                "fecha_objetivo": fecha_objetivo, "fecha_vencimiento": fecha_vencimiento,
                "fecha_real_termino": None,
            })
            st.success(f"Tarea {folio} creada (demo — en la versión real también se notifica en Chat "
                       f"y se refleja en Google Tasks del gerente).")


# ==================================================================
elif seccion == "Aplazamientos pendientes":
    st.subheader("Solicitudes de aplazamiento pendientes")
    if not aplazamientos:
        st.info("No hay solicitudes pendientes.")
    for ap in list(aplazamientos):
        with st.container(border=True):
            st.markdown(f"**{ap['tarea_folio']} · {ap['tarea_titulo']}**")
            st.write(f"Solicitante: {ap['solicitante_nombre']}")
            st.write(f"Fecha actual: {ap['fecha_anterior']} → Solicitada: {ap['fecha_solicitada']}")
            st.write(f"Motivo: {ap['motivo']}")
            c1, c2 = st.columns(2)
            if c1.button("Aprobar", key=f"ap_{ap['id']}"):
                for t in tareas:
                    if t["folio"] == ap["tarea_folio"]:
                        t["fecha_vencimiento"] = ap["fecha_solicitada"]
                aplazamientos.remove(ap)
                st.rerun()
            if c2.button("Rechazar", key=f"rc_{ap['id']}"):
                aplazamientos.remove(ap)
                st.rerun()


# ==================================================================
elif seccion == "Reporte por gerente":
    st.subheader("Informe por gerente")
    gerentes = [u for u in usuarios if u["rol"] == "Gerente"]
    gerente_sel = st.selectbox("Selecciona gerente", gerentes, format_func=lambda g: g["nombre"])
    filas = []
    for t in [t for t in tareas if t["gerente_id"] == gerente_sel["id"]]:
        est = fila_tarea(t)
        filas.append({
            "Folio": t["folio"], "Tarea": t["titulo"], "Prioridad": t["prioridad"] or "—",
            "Fecha objetivo": t["fecha_objetivo"] or "—", "Fecha vencimiento": t["fecha_vencimiento"],
            "Fecha real término": t["fecha_real_termino"] or "—", "Estado": t["estado"],
            "Semáforo": f"{semaforo_emoji(est.color)} {est.etiqueta}",
        })
    if filas:
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    else:
        st.info("Este gerente no tiene tareas registradas.")


# ==================================================================
elif seccion == "Todas las tareas":
    st.subheader("Todas las tareas · vista de semáforo")
    for t in tareas:
        est = fila_tarea(t)
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"**{t['folio']} · {t['titulo']}**")
            c1.caption(f"Gerente: {t['gerente_nombre']}")
            c2.write(f"Vence: {t['fecha_vencimiento']}")
            c2.write(f"Estado: {t['estado']}")
            c3.markdown(f"<span class='semaforo-{est.color}'>{semaforo_emoji(est.color)} {est.etiqueta}</span>",
                        unsafe_allow_html=True)
            if t["estado"] == "Solicitud de cierre":
                if c3.button("Cerrar tarea", key=f"cerrar_{t['id']}"):
                    t["estado"] = "Cerrada"
                    st.rerun()


# ==================================================================
elif seccion == "Mis tareas":
    st.subheader("Mis tareas")
    mis_tareas = [t for t in tareas if t["gerente_id"] == usuario["id"]]
    if not mis_tareas:
        st.info("No tienes tareas asignadas.")
    for t in mis_tareas:
        est = fila_tarea(t)
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"**{t['folio']} · {t['titulo']}**")
            c1.write(t["descripcion"])
            c1.caption(f"Vence: {t['fecha_vencimiento']} · Estado: {t['estado']}")
            c2.markdown(f"<span class='semaforo-{est.color}'>{semaforo_emoji(est.color)} {est.etiqueta}</span>",
                        unsafe_allow_html=True)

            if not t["prioridad"]:
                nueva_prioridad = c2.selectbox("Clasificar prioridad", ["Alta", "Media", "Baja"], key=f"prio_{t['id']}")
                if c2.button("Guardar prioridad", key=f"guardar_prio_{t['id']}"):
                    t["prioridad"] = nueva_prioridad
                    st.rerun()
            else:
                c2.write(f"Prioridad: {t['prioridad']}")

            if t["estado"] == "Abierta":
                if c2.button("Solicitar cierre", key=f"cierre_{t['id']}"):
                    st.session_state[f"mostrar_cierre_{t['id']}"] = True
                if st.session_state.get(f"mostrar_cierre_{t['id']}"):
                    fecha_real = st.date_input("Fecha real de término", value=HOY, key=f"fecha_real_{t['id']}")
                    if st.button("Confirmar solicitud de cierre", key=f"conf_cierre_{t['id']}"):
                        t["estado"] = "Solicitud de cierre"
                        t["fecha_real_termino"] = fecha_real
                        st.success("Solicitud de cierre enviada al Project Manager (demo).")
                        st.rerun()


# ==================================================================
elif seccion == "Solicitar aplazamiento":
    st.subheader("Solicitar aplazamiento")
    mis_abiertas = [t for t in tareas if t["gerente_id"] == usuario["id"] and t["estado"] == "Abierta"]
    if not mis_abiertas:
        st.info("No tienes tareas abiertas para aplazar.")
    else:
        tarea_sel = st.selectbox("Tarea", mis_abiertas, format_func=lambda t: f"{t['folio']} · {t['titulo']}")
        nueva_fecha = st.date_input("Nueva fecha de vencimiento solicitada")
        motivo = st.text_area("Motivo del aplazamiento")
        if st.button("Enviar solicitud (demo)"):
            if not motivo:
                st.error("El motivo es obligatorio.")
            else:
                aplazamientos.append({
                    "id": f"a{len(aplazamientos)+1}", "tarea_folio": tarea_sel["folio"],
                    "tarea_titulo": tarea_sel["titulo"], "solicitante_nombre": usuario["nombre"],
                    "fecha_anterior": tarea_sel["fecha_vencimiento"], "fecha_solicitada": nueva_fecha,
                    "motivo": motivo,
                })
                st.success("Solicitud de aplazamiento enviada al Project Manager (demo).")
