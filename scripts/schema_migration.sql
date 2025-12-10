-- Migration from SQLite to PostgreSQL
-- Generated automatically from existing schema


-- Table: backups_log
CREATE TABLE backups_log (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    comentario TEXT
);

-- Table: bnb_evaluaciones
CREATE TABLE bnb_evaluaciones (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER,
    criterio_id INTEGER,
    puntaje INTEGER NOT NULL,
    FOREIGN KEY (criterio_id) REFERENCES criterios_bnb (id) ON DELETE CASCADE,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);

-- Table: categorias
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL
);

-- Table: competidores_maestros
CREATE TABLE competidores_maestros (
    nombre TEXT,
    rnc TEXT,
    rpe TEXT,
    representante TEXT,
    total_participaciones INTEGER DEFAULT FALSE,
    total_ganadas INTEGER DEFAULT FALSE,
    ultima_adjudicacion TEXT
);

-- Table: config_app
CREATE TABLE config_app (
    clave TEXT,
    valor TEXT
);

-- Table: criterios_bnb
CREATE TABLE criterios_bnb (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    peso REAL NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- Table: cuentas
CREATE TABLE cuentas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL
);

-- Table: descalificaciones_fase_a
CREATE TABLE descalificaciones_fase_a (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    participante_nombre TEXT NOT NULL,
    documento_id INTEGER NOT NULL,
    comentario TEXT,
    es_nuestro BOOLEAN NOT NULL,
    FOREIGN KEY (documento_id) REFERENCES documentos (id) ON DELETE CASCADE,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);

-- Table: documentos
CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER,
    codigo TEXT,
    nombre TEXT,
    categoria TEXT,
    comentario TEXT,
    presentado BOOLEAN,
    subsanable TEXT,
    ruta_archivo TEXT,
    responsable TEXT,
    revisado BOOLEAN DEFAULT FALSE,
    obligatorio BOOLEAN DEFAULT FALSE,
    orden_pliego INTEGER,
    requiere_subsanacion BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE INDEX idx_documentos_licitacion_id ON documentos (licitacion_id);
CREATE INDEX idx_documentos_licitacion_orden ON documentos (licitacion_id, orden_pliego);

-- Table: documentos_maestros
CREATE TABLE documentos_maestros (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL,
    nombre TEXT,
    categoria TEXT,
    comentario TEXT,
    ruta_archivo TEXT
);

-- Table: empresas_maestras
CREATE TABLE empresas_maestras (
    nombre TEXT,
    rnc TEXT,
    telefono TEXT,
    correo TEXT,
    direccion TEXT,
    rpe TEXT,
    representante TEXT,
    cargo_representante TEXT
);

-- Table: expediente_items
CREATE TABLE expediente_items (
    id SERIAL PRIMARY KEY,
    expediente_id INTEGER NOT NULL,
    orden INTEGER NOT NULL,
    doc_version_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    FOREIGN KEY (doc_version_id) REFERENCES documentos (id) ON DELETE CASCADE,
    FOREIGN KEY (expediente_id) REFERENCES expedientes (id) ON DELETE CASCADE
);

-- Table: expedientes
CREATE TABLE expedientes (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    creado_en TEXT DEFAULT 'strftime('%Y-%m-%d %H:%M:%f','now')',
    creado_por TEXT,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);

-- Table: ganadores_canonicos
CREATE TABLE ganadores_canonicos (
    numero_proceso TEXT,
    lote_numero TEXT,
    ganador_nombre TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT 'datetime('now')'
);
CREATE INDEX idx_gcanonico_numproc ON ganadores_canonicos (numero_proceso);

-- Table: historial_ganadores
CREATE TABLE historial_ganadores (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    lote_numero TEXT NOT NULL,
    oferente_nombre TEXT NOT NULL,
    fecha TEXT DEFAULT 'strftime('%Y-%m-%d %H:%M:%f','now')',
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE INDEX idx_hist_ganadores_oferente ON historial_ganadores (oferente_nombre);
CREATE INDEX idx_hist_ganadores_licitacion ON historial_ganadores (licitacion_id);

-- Table: instituciones_maestras
CREATE TABLE instituciones_maestras (
    nombre TEXT,
    rnc TEXT,
    telefono TEXT,
    correo TEXT,
    direccion TEXT
);

-- Table: kit_items
CREATE TABLE kit_items (
    kit_id SERIAL PRIMARY KEY,
    documento_maestro_id SERIAL PRIMARY KEY,
    FOREIGN KEY (documento_maestro_id) REFERENCES documentos_maestros_old (id) ON DELETE CASCADE,
    FOREIGN KEY (kit_id) REFERENCES kits_de_requisitos (id) ON DELETE CASCADE
);

-- Table: kits_de_requisitos
CREATE TABLE kits_de_requisitos (
    id SERIAL PRIMARY KEY,
    nombre_kit TEXT NOT NULL,
    institucion_nombre TEXT NOT NULL,
    FOREIGN KEY (institucion_nombre) REFERENCES instituciones_maestras (nombre) ON DELETE CASCADE
);

-- Table: licitacion_empresas_nuestras
CREATE TABLE licitacion_empresas_nuestras (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    empresa_nombre TEXT NOT NULL,
    FOREIGN KEY (empresa_nombre) REFERENCES empresas_maestras (nombre) ON DELETE CASCADE,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);

-- Table: licitacion_ganadores_lote
CREATE TABLE licitacion_ganadores_lote (
    licitacion_id SERIAL PRIMARY KEY,
    lote_numero TEXT,
    ganador_nombre TEXT NOT NULL,
    es_nuestro INTEGER NOT NULL DEFAULT FALSE,
    empresa_nuestra TEXT,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uniq_ganador_por_lote ON licitacion_ganadores_lote (licitacion_id, lote_numero);
CREATE INDEX idx_ganadores_nombre ON licitacion_ganadores_lote (ganador_nombre);
CREATE INDEX idx_ganadores_licitacion ON licitacion_ganadores_lote (licitacion_id);

-- Table: licitaciones
CREATE TABLE licitaciones (
    id SERIAL PRIMARY KEY,
    nombre_proceso TEXT NOT NULL,
    numero_proceso TEXT NOT NULL,
    institucion TEXT,
    empresa_nuestra TEXT,
    estado TEXT,
    fase_A_superada BOOLEAN,
    fase_B_superada BOOLEAN,
    adjudicada BOOLEAN,
    adjudicada_a TEXT,
    motivo_descalificacion TEXT,
    fecha_creacion TEXT,
    cronograma TEXT,
    docs_completos_manual BOOLEAN DEFAULT FALSE,
    bnb_score REAL DEFAULT -1.0,
    last_modified TEXT,
    parametros_evaluacion TEXT
);

-- Table: lotes
CREATE TABLE lotes (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER,
    numero TEXT,
    nombre TEXT,
    monto_base REAL,
    monto_base_personal REAL,
    monto_ofertado REAL,
    participamos BOOLEAN,
    fase_A_superada BOOLEAN,
    ganador_oferente TEXT,
    empresa_nuestra TEXT,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE INDEX idx_lotes_licitacion_id ON lotes (licitacion_id);

-- Table: oferentes
CREATE TABLE oferentes (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER,
    nombre TEXT,
    comentario TEXT,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE INDEX idx_oferentes_licitacion_id ON oferentes (licitacion_id);

-- Table: ofertas_lote_oferentes
CREATE TABLE ofertas_lote_oferentes (
    id SERIAL PRIMARY KEY,
    oferente_id INTEGER,
    lote_numero TEXT,
    monto REAL,
    paso_fase_A BOOLEAN,
    plazo_entrega INTEGER DEFAULT FALSE,
    garantia_meses INTEGER DEFAULT FALSE,
    FOREIGN KEY (oferente_id) REFERENCES oferentes (id) ON DELETE CASCADE
);
CREATE INDEX idx_ofertas_oferente_id ON ofertas_lote_oferentes (oferente_id);

-- Table: presupuestos
CREATE TABLE presupuestos (
    id SERIAL PRIMARY KEY,
    proyecto_id INTEGER NOT NULL,
    subcategoria_id INTEGER NOT NULL,
    monto REAL NOT NULL,
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id) ON DELETE CASCADE,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos (id) ON DELETE CASCADE
);

-- Table: proyecto_cuentas
CREATE TABLE proyecto_cuentas (
    proyecto_id SERIAL PRIMARY KEY,
    cuenta_id SERIAL PRIMARY KEY,
    is_principal INTEGER NOT NULL DEFAULT FALSE,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas (id) ON DELETE CASCADE,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos (id) ON DELETE CASCADE
);

-- Table: proyectos
CREATE TABLE proyectos (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    moneda TEXT NOT NULL,
    cuenta_principal TEXT
);

-- Table: responsables_maestros
CREATE TABLE responsables_maestros (
    nombre TEXT
);

-- Table: riesgos
CREATE TABLE riesgos (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    categoria TEXT,
    impacto INTEGER DEFAULT TRUE,
    probabilidad INTEGER DEFAULT TRUE,
    mitigacion TEXT,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE INDEX idx_riesgos_licitacion_id ON riesgos (licitacion_id);

-- Table: schema_migrations
CREATE TABLE schema_migrations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT 'strftime('%Y-%m-%d %H:%M:%f','now')',
    checksum TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_schema_migrations_id ON schema_migrations (id);

-- Table: subcategorias
CREATE TABLE subcategorias (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria_id INTEGER NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categorias (id) ON DELETE CASCADE
);

-- Table: subsanacion_historial
CREATE TABLE subsanacion_historial (
    id SERIAL PRIMARY KEY,
    licitacion_id INTEGER NOT NULL,
    documento_id INTEGER NOT NULL,
    fecha_solicitud TEXT NOT NULL,
    fecha_limite_entrega TEXT,
    fecha_entrega_real TEXT,
    comentario TEXT,
    estado TEXT DEFAULT ''Pendiente'',
    FOREIGN KEY (documento_id) REFERENCES documentos (id) ON DELETE CASCADE,
    FOREIGN KEY (licitacion_id) REFERENCES licitaciones (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uniq_subsanacion_pendiente ON subsanacion_historial (licitacion_id, documento_id);

-- Table: transacciones
CREATE TABLE transacciones (
    id TEXT,
    proyecto_id INTEGER NOT NULL,
    cuenta_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    subcategoria_id INTEGER,
    tipo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    comentario TEXT,
    monto REAL NOT NULL,
    fecha TEXT NOT NULL,
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias (id),
    FOREIGN KEY (categoria_id) REFERENCES categorias (id),
    FOREIGN KEY (cuenta_id) REFERENCES cuentas (id),
    FOREIGN KEY (proyecto_id) REFERENCES proyectos (id) ON DELETE CASCADE
);