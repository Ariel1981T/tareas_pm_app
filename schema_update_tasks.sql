-- ============================================================
-- Actualización: vínculo con Google Tasks (Fase 1 - un solo sentido)
-- Correr DESPUÉS de schema.sql
-- ============================================================

alter table tareas
    add column if not exists google_task_id text,
    add column if not exists google_tasklist_id text,
    add column if not exists google_sync_error text;

-- google_task_id / google_tasklist_id: identifican la tarea espejo
-- creada en la cuenta de Google Tasks del gerente.
-- google_sync_error: si falla la creación/actualización en Google,
-- se guarda aquí el motivo para poder revisarlo sin tumbar el flujo
-- principal en Supabase (la fuente de verdad sigue siendo Streamlit).
