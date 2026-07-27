-- ============================================================
-- IMEMSA · Sistema de Tareas PM → Gerentes
-- Esquema de base de datos (Supabase / PostgreSQL)
-- ============================================================

-- Extensión para UUID
create extension if not exists "uuid-ossp";

-- --------------------------------------------------------------
-- Tabla de usuarios (PM, Gerentes, Admin)
-- --------------------------------------------------------------
create table if not exists usuarios (
    id uuid primary key default uuid_generate_v4(),
    nombre text not null,
    correo text unique not null,
    rol text not null check (rol in ('Admin', 'PM', 'Gerente')),
    activo boolean default true,
    creado_en timestamptz default now()
);

-- --------------------------------------------------------------
-- Tabla principal de tareas
-- --------------------------------------------------------------
create table if not exists tareas (
    id uuid primary key default uuid_generate_v4(),
    folio text unique not null,                        -- ej. TAR-2026-001

    titulo text not null,
    descripcion text,

    project_manager_id uuid references usuarios(id),
    gerente_id uuid references usuarios(id),

    prioridad text check (prioridad in ('Alta', 'Media', 'Baja')) default null,
    -- NULL hasta que el gerente clasifica (paso 2 del proceso)

    -- Fechas clave (independientes, siempre visibles - a diferencia de Google Tasks)
    fecha_elaboracion date not null default current_date,   -- cuándo se asignó
    fecha_objetivo date,                                     -- meta interna del gerente
    fecha_vencimiento date not null,                         -- límite formal comprometido
    fecha_real_termino date,                                 -- editable independiente del cierre

    estado text not null check (
        estado in ('Abierta', 'Solicitud de cierre', 'Cerrada', 'Cancelada')
    ) default 'Abierta',

    creado_en timestamptz default now(),
    actualizado_en timestamptz default now()
);

-- --------------------------------------------------------------
-- Historial de solicitudes de aplazamiento
-- --------------------------------------------------------------
create table if not exists aplazamientos (
    id uuid primary key default uuid_generate_v4(),
    tarea_id uuid references tareas(id) on delete cascade,

    fecha_vencimiento_anterior date not null,
    fecha_vencimiento_solicitada date not null,
    motivo text not null,

    solicitado_por uuid references usuarios(id),
    solicitado_en timestamptz default now(),

    estado text not null check (estado in ('Pendiente', 'Aprobado', 'Rechazado')) default 'Pendiente',
    resuelto_por uuid references usuarios(id),
    resuelto_en timestamptz,
    comentario_resolucion text
);

-- --------------------------------------------------------------
-- Bitácora de cambios de estado (trazabilidad)
-- --------------------------------------------------------------
create table if not exists tareas_historial (
    id uuid primary key default uuid_generate_v4(),
    tarea_id uuid references tareas(id) on delete cascade,
    estado_anterior text,
    estado_nuevo text,
    cambiado_por uuid references usuarios(id),
    cambiado_en timestamptz default now(),
    nota text
);

-- --------------------------------------------------------------
-- Índices para reportes por gerente y semáforo
-- --------------------------------------------------------------
create index if not exists idx_tareas_gerente on tareas(gerente_id);
create index if not exists idx_tareas_estado on tareas(estado);
create index if not exists idx_tareas_vencimiento on tareas(fecha_vencimiento);
create index if not exists idx_aplazamientos_tarea on aplazamientos(tarea_id);

-- --------------------------------------------------------------
-- Folio automático: TAR-AAAA-NNN
-- --------------------------------------------------------------
create sequence if not exists folio_tareas_seq;

create or replace function generar_folio_tarea()
returns trigger as $$
begin
    if new.folio is null then
        new.folio := 'TAR-' || to_char(current_date, 'YYYY') || '-' ||
                      lpad(nextval('folio_tareas_seq')::text, 3, '0');
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_folio_tarea on tareas;
create trigger trg_folio_tarea
before insert on tareas
for each row execute function generar_folio_tarea();
