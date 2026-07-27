import streamlit as st
from datetime import date
import pandas as pd

from utils import db, notifications
from utils.dates_logic import calcular_estado_tarea, semaforo_emoji

st.set_page_config(page_title="IMEMSA · Tareas PM", page_icon="📋", layout="wide")

# ----------------------------------------------------------------
# Estilo IMEMSA (navy #0D2B6E / rojo #C41E2E)
# ----------------------------------------------------------------
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
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# Login simple (por correo registrado en tabla usuarios)
# ----------------------------------------------------------------
if "usuario" not in st.session_state:
    st.title("📋 Sistema de Tareas · IMEMSA")
    st.subheader("Iniciar sesión")
    correo = st.text_input("Correo institucional")
    if st.button("Entrar"):
        usuario = db.obtener_usuario_por_correo(correo.strip().lower())
        if usuario:
            st.session_state["usuario"] = usuario
            st.rerun()
        else:
            st.error("Correo no encontrado o usuario inactivo.")
    st.stop()

usuario = st.session_state["usuario"]

# ----------------------------------------------------------------
# Barra lateral / navegación por rol
# ----------------------------------------------------------------
st.sidebar.markdown(f"**{usuario['nombre']}**")
st.sidebar.caption(usuario["rol"])
if st.sidebar.button("Cerrar sesión"):
    del st.session_state["usuario"]
    st.rerun()

if usuario["rol"] == "PM" or usuario["rol"] == "Admin":
    opciones = ["Asignar tarea", "Aplazamientos pendientes", "Reporte por gerente", "Todas las tareas"]
else:
    opciones = ["Mis tareas", "Solicitar aplazamiento"]

seccion = st.sidebar.radio("Menú", opciones)

st.title("📋 Sistema de Tareas · IMEMSA")


# ==================================================================
# PM/Admin: Asignar tarea
# ==================================================================
if seccion == "Asignar tarea":
    st.subheader("Asignar nueva tarea")
    gerentes = db.obtener_usuarios(rol="Gerente")
    if not gerentes:
        st.warning("No hay gerentes registrados en la tabla `usuarios`.")
    else:
        with st.form("nueva_tarea"):
            titulo = st.text_input("Título de la tarea")
            descripcion = st.text_area("Descripción")
            gerente_sel = st.selectbox(
                "Gerente responsable",
                gerentes, format_func=lambda g: g["nombre"]
            )
            col1, col2 = st.columns(2)
            fecha_objetivo = col1.date_input("Fecha objetivo (interna)", value=None)
            fecha_vencimiento = col2.date_input("Fecha de vencimiento (compromiso formal)")
            enviar = st.form_submit_button("Asignar y notificar en Chat")

        if enviar:
            if not titulo or not fecha_vencimiento:
                st.error("Título y fecha de vencimiento son obligatorios.")
            else:
                nueva = db.crear_tarea(
                    {
                        "titulo": titulo,
                        "descripcion": descripcion,
                        "project_manager_id": usuario["id"],
                        "gerente_id": gerente_sel["id"],
                        "fecha_objetivo": str(fecha_objetivo) if fecha_objetivo else None,
                        "fecha_vencimiento": str(fecha_vencimiento),
                    },
                    gerente_correo=gerente_sel["correo"],
                )
                if nueva:
                    tarea_creada = nueva[0]
                    folio = tarea_creada["folio"]
                    notifications.notificar_nueva_tarea(
                        folio, titulo, gerente_sel["nombre"], str(fecha_vencimiento)
                    )
                    if tarea_creada.get("google_sync_error"):
                        st.warning(
                            f"Tarea {folio} creada y notificada en Chat, pero no se pudo "
                            f"reflejar en Google Tasks del gerente: {tarea_creada['google_sync_error']}"
                        )
                    else:
                        st.success(f"Tarea {folio} creada, notificada en Chat y reflejada en Google Tasks.")


# ==================================================================
# PM/Admin: Aplazamientos pendientes
# ==================================================================
elif seccion == "Aplazamientos pendientes":
    st.subheader("Solicitudes de aplazamiento pendientes")
    pendientes = db.obtener_aplazamientos_pendientes()
    if not pendientes:
        st.info("No hay solicitudes pendientes.")
    for ap in pendientes:
        with st.container(border=True):
            st.markdown(f"**{ap['tarea']['folio']} · {ap['tarea']['titulo']}**")
            st.write(f"Solicitante: {ap['solicitante']['nombre']}")
            st.write(f"Fecha actual: {ap['fecha_vencimiento_anterior']} → Solicitada: {ap['fecha_vencimiento_solicitada']}")
            st.write(f"Motivo: {ap['motivo']}")
            comentario = st.text_input("Comentario de resolución", key=f"c_{ap['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Aprobar", key=f"ap_{ap['id']}"):
                db.resolver_aplazamiento(ap["id"], True, usuario["id"], comentario)
                st.rerun()
            if c2.button("Rechazar", key=f"rc_{ap['id']}"):
                db.resolver_aplazamiento(ap["id"], False, usuario["id"], comentario)
                st.rerun()


# ==================================================================
# PM/Admin: Reporte por gerente
# ==================================================================
elif seccion == "Reporte por gerente":
    st.subheader("Informe por gerente")
    gerentes = db.obtener_usuarios(rol="Gerente")
    gerente_sel = st.selectbox("Selecciona gerente", gerentes, format_func=lambda g: g["nombre"])

    tareas = db.obtener_tareas(gerente_id=gerente_sel["id"])
    filas = []
    for t in tareas:
        est = calcular_estado_tarea(
            t["estado"],
            date.fromisoformat(t["fecha_vencimiento"]),
            date.fromisoformat(t["fecha_real_termino"]) if t.get("fecha_real_termino") else None,
        )
        filas.append({
            "Folio": t["folio"],
            "Tarea": t["titulo"],
            "Prioridad": t.get("prioridad") or "—",
            "Fecha objetivo": t.get("fecha_objetivo") or "—",
            "Fecha vencimiento": t["fecha_vencimiento"],
            "Fecha real término": t.get("fecha_real_termino") or "—",
            "Estado": t["estado"],
            "Semáforo": f"{semaforo_emoji(est.color)} {est.etiqueta}",
        })

    if filas:
        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar CSV", csv, f"reporte_{gerente_sel['nombre']}.csv", "text/csv")
    else:
        st.info("Este gerente no tiene tareas registradas.")


# ==================================================================
# PM/Admin: Todas las tareas (vista general con semáforo)
# ==================================================================
elif seccion == "Todas las tareas":
    st.subheader("Todas las tareas · vista de semáforo")
    tareas = db.obtener_tareas()
    for t in tareas:
        est = calcular_estado_tarea(
            t["estado"],
            date.fromisoformat(t["fecha_vencimiento"]),
            date.fromisoformat(t["fecha_real_termino"]) if t.get("fecha_real_termino") else None,
        )
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"**{t['folio']} · {t['titulo']}**")
            c1.caption(f"Gerente: {t.get('gerente', {}).get('nombre', '—')}")
            c2.write(f"Vence: {t['fecha_vencimiento']}")
            c2.write(f"Estado: {t['estado']}")
            c3.markdown(f"<span class='semaforo-{est.color}'>{semaforo_emoji(est.color)} {est.etiqueta}</span>",
                        unsafe_allow_html=True)
            if t["estado"] == "Solicitud de cierre":
                if c3.button("Cerrar tarea", key=f"cerrar_{t['id']}"):
                    db.cerrar_tarea(
                        t["id"], usuario["id"],
                        gerente_correo=t.get("gerente", {}).get("correo"),
                    )
                    st.rerun()


# ==================================================================
# Gerente: Mis tareas
# ==================================================================
elif seccion == "Mis tareas":
    st.subheader("Mis tareas")
    tareas = db.obtener_tareas(gerente_id=usuario["id"])
    if not tareas:
        st.info("No tienes tareas asignadas.")
    for t in tareas:
        est = calcular_estado_tarea(
            t["estado"],
            date.fromisoformat(t["fecha_vencimiento"]),
            date.fromisoformat(t["fecha_real_termino"]) if t.get("fecha_real_termino") else None,
        )
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"**{t['folio']} · {t['titulo']}**")
            c1.write(t.get("descripcion") or "")
            c1.caption(f"Vence: {t['fecha_vencimiento']} · Estado: {t['estado']}")
            c2.markdown(f"<span class='semaforo-{est.color}'>{semaforo_emoji(est.color)} {est.etiqueta}</span>",
                        unsafe_allow_html=True)

            if not t.get("prioridad"):
                nueva_prioridad = c2.selectbox(
                    "Clasificar prioridad", ["Alta", "Media", "Baja"], key=f"prio_{t['id']}"
                )
                if c2.button("Guardar prioridad", key=f"guardar_prio_{t['id']}"):
                    db.clasificar_prioridad(t["id"], nueva_prioridad)
                    st.rerun()
            else:
                c2.write(f"Prioridad: {t['prioridad']}")

            if t["estado"] == "Abierta":
                if c2.button("Solicitar cierre", key=f"cierre_{t['id']}"):
                    st.session_state[f"mostrar_cierre_{t['id']}"] = True

                if st.session_state.get(f"mostrar_cierre_{t['id']}"):
                    fecha_real = st.date_input(
                        "Fecha real de término", value=date.today(), key=f"fecha_real_{t['id']}"
                    )
                    if st.button("Confirmar solicitud de cierre", key=f"conf_cierre_{t['id']}"):
                        db.solicitar_cierre(t["id"], fecha_real, usuario["id"])
                        notifications.notificar_solicitud_cierre(t["folio"], t["titulo"], usuario["nombre"])
                        st.success("Solicitud de cierre enviada al Project Manager.")
                        st.rerun()


# ==================================================================
# Gerente: Solicitar aplazamiento
# ==================================================================
elif seccion == "Solicitar aplazamiento":
    st.subheader("Solicitar aplazamiento")
    tareas = [t for t in db.obtener_tareas(gerente_id=usuario["id"]) if t["estado"] == "Abierta"]
    if not tareas:
        st.info("No tienes tareas abiertas para aplazar.")
    else:
        tarea_sel = st.selectbox("Tarea", tareas, format_func=lambda t: f"{t['folio']} · {t['titulo']}")
        nueva_fecha = st.date_input("Nueva fecha de vencimiento solicitada")
        motivo = st.text_area("Motivo del aplazamiento")
        if st.button("Enviar solicitud"):
            if not motivo:
                st.error("El motivo es obligatorio.")
            else:
                db.solicitar_aplazamiento(
                    tarea_sel["id"],
                    date.fromisoformat(tarea_sel["fecha_vencimiento"]),
                    nueva_fecha,
                    motivo,
                    usuario["id"],
                )
                notifications.notificar_solicitud_aplazamiento(
                    tarea_sel["folio"], tarea_sel["titulo"], usuario["nombre"],
                    tarea_sel["fecha_vencimiento"], str(nueva_fecha), motivo,
                )
                st.success("Solicitud de aplazamiento enviada al Project Manager.")
