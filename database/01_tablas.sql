/* =============================================================================
   Sistema de Gestión para Carpintería
   01 - Tablas, claves y restricciones
   Motor: SQL Server 2025 Express  ·  Modelo de datos v1.3  ·  3FN
   -----------------------------------------------------------------------------
   CONVENCIONES
   - Tablas en singular, Inicial_Mayuscula. Atributos con el sufijo de su tabla.
   - PK: id_<tabla>, INT IDENTITY. FK: mismo nombre que la PK referenciada
     (o con el rol: id_placa_fondo, id_trabajo_origen...).
   - Nombres de restricciones: PK_Tabla, FK_Hija_Padre[_rol], UQ_Tabla_..,
     CK_Tabla_.., DF_Tabla_..  -> los errores de la base dicen qué regla falló.
   - Textos en NVARCHAR (Unicode: ñ, tildes). Booleanos en BIT.
   - Medidas en cm DECIMAL(6,1); luces y descuentos DECIMAL(5,2); importes
     DECIMAL(12,2).

   ORDEN: se crean primero las tablas sin dependencias y después las que las
   referencian. El script es re-ejecutable: borra las tablas en orden inverso.

   REGLAS DE BORRADO (ver sección 8.2 del modelo)
   SQL Server no permite dos caminos de borrado en cascada hacia una misma tabla
   (error 1785). Como Pieza depende de Mueble, Modulo, Cajon y Zocalo (que a su
   vez dependen de Mueble), las FK de Pieza son NO ACTION y el borrado de un
   trabajo completo se hace con el procedimiento sp_eliminar_trabajo (04).
   ============================================================================= */

USE Carpinteria;
GO

/* ---------- Borrado previo (orden inverso a las dependencias) ---------- */
DROP TABLE IF EXISTS dbo.Retazo;
DROP TABLE IF EXISTS dbo.Pieza;
DROP TABLE IF EXISTS dbo.Cajon;
DROP TABLE IF EXISTS dbo.Modulo_Veta_Rotada;
DROP TABLE IF EXISTS dbo.Modulo;
DROP TABLE IF EXISTS dbo.Zocalo;
DROP TABLE IF EXISTS dbo.Pieza_Guia;
DROP TABLE IF EXISTS dbo.Largo_Guia;
DROP TABLE IF EXISTS dbo.Tipo_Guia;
DROP TABLE IF EXISTS dbo.Tipo_Pieza;
DROP TABLE IF EXISTS dbo.Estilo_Frente;
DROP TABLE IF EXISTS dbo.Tipo_Armado;
DROP TABLE IF EXISTS dbo.Tipo_Filo;
DROP TABLE IF EXISTS dbo.Liston;
DROP TABLE IF EXISTS dbo.Placa;
DROP TABLE IF EXISTS dbo.Material;
DROP TABLE IF EXISTS dbo.Terminacion_Laca;
DROP TABLE IF EXISTS dbo.Color_Laca;
DROP TABLE IF EXISTS dbo.Marca_Pintura;
DROP TABLE IF EXISTS dbo.Color_Placa;
DROP TABLE IF EXISTS dbo.Marca_Placa;
DROP TABLE IF EXISTS dbo.Mueble;
DROP TABLE IF EXISTS dbo.Trabajo;
DROP TABLE IF EXISTS dbo.Estado_Trabajo;
DROP TABLE IF EXISTS dbo.Obra;
DROP TABLE IF EXISTS dbo.Cliente;
DROP TABLE IF EXISTS dbo.Parametro;
DROP TABLE IF EXISTS dbo.Auditoria;
DROP TABLE IF EXISTS dbo.Tipo_Evento;
DROP TABLE IF EXISTS dbo.Usuario;
GO

/* =============================================================================
   1. SEGURIDAD Y CONFIGURACIÓN
   ============================================================================= */

CREATE TABLE dbo.Usuario (
    id_usuario                  INT IDENTITY(1,1) NOT NULL,
    nombre_usuario_usu          NVARCHAR(50)  NOT NULL,
    hash_contrasena_usu         VARCHAR(255)  NOT NULL,   -- hash bcrypt, nunca la contraseña
    debe_cambiar_contrasena_usu BIT           NOT NULL CONSTRAINT DF_Usuario_debe_cambiar DEFAULT (0),
    nombre_completo_usu         NVARCHAR(100) NOT NULL,
    es_activo_usu               BIT           NOT NULL CONSTRAINT DF_Usuario_es_activo DEFAULT (1),
    fecha_alta_usu              DATETIME2(0)  NOT NULL CONSTRAINT DF_Usuario_fecha_alta DEFAULT (SYSDATETIME()),
    -- Seguridad del ingreso (RF-03.1 a RF-03.6)
    intentos_fallidos_usu       INT           NOT NULL CONSTRAINT DF_Usuario_intentos DEFAULT (0),  -- consecutivos; vuelve a 0 al ingresar bien
    bloqueado_hasta_usu         DATETIME2(0)  NULL,     -- NULL o fecha pasada = no bloqueado
    ultimo_ingreso_usu          DATETIME2(0)  NULL,
    fecha_cambio_contrasena_usu DATETIME2(0)  NULL,
    CONSTRAINT PK_Usuario PRIMARY KEY (id_usuario),
    CONSTRAINT UQ_Usuario_nombre_usuario UNIQUE (nombre_usuario_usu),
    CONSTRAINT CK_Usuario_intentos CHECK (intentos_fallidos_usu >= 0)
);

/* Catálogo de eventos que se registran en la auditoría. es_critico_tev marca
   los que la pantalla de auditoría resalta (posible incidente). */
CREATE TABLE dbo.Tipo_Evento (
    id_tipo_evento  INT IDENTITY(1,1) NOT NULL,
    codigo_tev      VARCHAR(30)    NOT NULL,
    descripcion_tev NVARCHAR(100)  NOT NULL,
    es_critico_tev  BIT            NOT NULL CONSTRAINT DF_Tipo_Evento_es_critico DEFAULT (0),
    CONSTRAINT PK_Tipo_Evento PRIMARY KEY (id_tipo_evento),
    CONSTRAINT UQ_Tipo_Evento_codigo UNIQUE (codigo_tev)
);

/* Registro de auditoría: quién hizo qué y cuándo. Solo se agregan filas
   (con sp_registrar_evento): el usuario de la aplicación no puede modificarlas
   ni borrarlas (DENY en 05_seguridad.sql). */
CREATE TABLE dbo.Auditoria (
    id_auditoria          BIGINT IDENTITY(1,1) NOT NULL,
    fecha_hora_aud        DATETIME2(0)   NOT NULL CONSTRAINT DF_Auditoria_fecha_hora DEFAULT (SYSDATETIME()),
    id_tipo_evento        INT            NOT NULL,
    id_usuario            INT            NULL,     -- NULL si el usuario ingresado no existe
    usuario_ingresado_aud NVARCHAR(50)   NULL,     -- nombre tipeado en un ingreso fallido
    entidad_aud           VARCHAR(30)    NULL,     -- tabla afectada (ej.: 'Trabajo')
    id_entidad_aud        INT            NULL,
    detalle_aud           NVARCHAR(500)  NULL,     -- ej.: 'monto_total_tra: 500000.00 -> 550000.00'
    equipo_aud            NVARCHAR(100)  NULL,     -- nombre de la PC
    CONSTRAINT PK_Auditoria PRIMARY KEY (id_auditoria),
    CONSTRAINT FK_Auditoria_Tipo_Evento FOREIGN KEY (id_tipo_evento) REFERENCES dbo.Tipo_Evento (id_tipo_evento),
    CONSTRAINT FK_Auditoria_Usuario     FOREIGN KEY (id_usuario)     REFERENCES dbo.Usuario (id_usuario),
    CONSTRAINT CK_Auditoria_entidad     CHECK (id_entidad_aud IS NULL OR entidad_aud IS NOT NULL)
);

CREATE TABLE dbo.Parametro (
    id_parametro    INT IDENTITY(1,1) NOT NULL,
    clave_par       VARCHAR(50)    NOT NULL,
    valor_par       DECIMAL(8,2)   NOT NULL,
    unidad_par      NVARCHAR(10)   NOT NULL,
    descripcion_par NVARCHAR(200)  NULL,
    CONSTRAINT PK_Parametro PRIMARY KEY (id_parametro),
    CONSTRAINT UQ_Parametro_clave UNIQUE (clave_par)
);
GO

/* =============================================================================
   2. CLIENTES Y TRABAJOS
   ============================================================================= */

CREATE TABLE dbo.Cliente (
    id_cliente        INT IDENTITY(1,1) NOT NULL,
    nombre_cli        NVARCHAR(50)  NOT NULL,
    apellido_cli      NVARCHAR(50)  NOT NULL,
    telefono_cli      VARCHAR(25)   NOT NULL,
    email_cli         NVARCHAR(100) NULL,
    observaciones_cli NVARCHAR(500) NULL,
    es_activo_cli     BIT           NOT NULL CONSTRAINT DF_Cliente_es_activo DEFAULT (1),
    fecha_alta_cli    DATETIME2(0)  NOT NULL CONSTRAINT DF_Cliente_fecha_alta DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_Cliente PRIMARY KEY (id_cliente)
);

CREATE TABLE dbo.Obra (
    id_obra           INT IDENTITY(1,1) NOT NULL,
    id_cliente        INT           NOT NULL,
    nombre_obr        NVARCHAR(100) NULL,           -- alias, ej.: "Casa Nordelta"
    direccion_obr     NVARCHAR(150) NOT NULL,
    localidad_obr     NVARCHAR(80)  NOT NULL,
    observaciones_obr NVARCHAR(500) NULL,
    fecha_alta_obr    DATETIME2(0)  NOT NULL CONSTRAINT DF_Obra_fecha_alta DEFAULT (SYSDATETIME()),
    CONSTRAINT PK_Obra PRIMARY KEY (id_obra),
    -- No se borra un cliente con obras: se da de baja lógica (RESTRICT = NO ACTION)
    CONSTRAINT FK_Obra_Cliente FOREIGN KEY (id_cliente) REFERENCES dbo.Cliente (id_cliente),
    CONSTRAINT UQ_Obra_cliente_direccion UNIQUE (id_cliente, direccion_obr, localidad_obr)
);

CREATE TABLE dbo.Estado_Trabajo (
    id_estado_trabajo INT IDENTITY(1,1) NOT NULL,
    nombre_etr        NVARCHAR(30) NOT NULL,
    orden_etr         INT          NOT NULL,
    CONSTRAINT PK_Estado_Trabajo PRIMARY KEY (id_estado_trabajo),
    CONSTRAINT UQ_Estado_Trabajo_nombre UNIQUE (nombre_etr),
    CONSTRAINT UQ_Estado_Trabajo_orden  UNIQUE (orden_etr)
);

CREATE TABLE dbo.Trabajo (
    id_trabajo             INT IDENTITY(1,1) NOT NULL,
    id_obra                INT            NOT NULL,   -- el cliente se obtiene por la obra (3FN)
    id_estado_trabajo      INT            NOT NULL,
    descripcion_tra        NVARCHAR(200)  NOT NULL,
    monto_total_tra        DECIMAL(12,2)  NULL,
    monto_sena_tra         DECIMAL(12,2)  NULL,       -- el saldo NO se guarda: total - seña
    fecha_alta_tra         DATETIME2(0)   NOT NULL CONSTRAINT DF_Trabajo_fecha_alta DEFAULT (SYSDATETIME()),  -- cuándo se cargó (no se edita)
    fecha_presupuesto_tra  DATE           NOT NULL CONSTRAINT DF_Trabajo_fecha_presupuesto DEFAULT (CAST(SYSDATETIME() AS DATE)),  -- se puede cargar con fecha pasada
    fecha_cobro_sena_tra   DATE           NULL,
    fecha_comienzo_tra     DATE           NULL,
    fecha_finalizacion_tra DATE           NULL,
    fecha_entrega_tra      DATE           NULL,       -- pactada (antes de instalar) o real (instalado)
    entrega_aproximada_tra BIT            NOT NULL CONSTRAINT DF_Trabajo_entrega_aproximada DEFAULT (0),  -- 1 = solo se pactó la semana
    fecha_cobro_saldo_tra  DATE           NULL,
    observaciones_tra      NVARCHAR(500)  NULL,
    CONSTRAINT PK_Trabajo PRIMARY KEY (id_trabajo),
    CONSTRAINT FK_Trabajo_Obra           FOREIGN KEY (id_obra)           REFERENCES dbo.Obra (id_obra),
    CONSTRAINT FK_Trabajo_Estado_Trabajo FOREIGN KEY (id_estado_trabajo) REFERENCES dbo.Estado_Trabajo (id_estado_trabajo),
    CONSTRAINT CK_Trabajo_montos_positivos CHECK (monto_total_tra >= 0 AND monto_sena_tra >= 0),
    CONSTRAINT CK_Trabajo_sena_menor_total CHECK (monto_sena_tra <= monto_total_tra),
    -- Con NULL la comparación da "desconocido" y el CHECK se cumple: solo se
    -- valida cuando las dos fechas están cargadas.
    CONSTRAINT CK_Trabajo_fecha_finalizacion CHECK (fecha_finalizacion_tra >= fecha_comienzo_tra),
    CONSTRAINT CK_Trabajo_fecha_entrega      CHECK (fecha_entrega_tra >= fecha_finalizacion_tra),
    -- Nada ocurre antes del presupuesto (con NULL, esa comparación no hace fallar el CHECK).
    CONSTRAINT CK_Trabajo_fechas_desde_presupuesto CHECK (
        fecha_cobro_sena_tra   >= fecha_presupuesto_tra AND fecha_comienzo_tra    >= fecha_presupuesto_tra AND
        fecha_finalizacion_tra >= fecha_presupuesto_tra AND fecha_entrega_tra     >= fecha_presupuesto_tra AND
        fecha_cobro_saldo_tra  >= fecha_presupuesto_tra)
);

CREATE TABLE dbo.Mueble (
    id_mueble         INT IDENTITY(1,1) NOT NULL,
    id_trabajo        INT           NOT NULL,
    nombre_mue        NVARCHAR(100) NOT NULL,
    observaciones_mue NVARCHAR(500) NULL,
    CONSTRAINT PK_Mueble PRIMARY KEY (id_mueble),
    CONSTRAINT FK_Mueble_Trabajo FOREIGN KEY (id_trabajo) REFERENCES dbo.Trabajo (id_trabajo) ON DELETE CASCADE
);
GO

/* =============================================================================
   3. MATERIALES
   ============================================================================= */

CREATE TABLE dbo.Marca_Placa (
    id_marca_placa INT IDENTITY(1,1) NOT NULL,
    nombre_mpl     NVARCHAR(50) NOT NULL,
    es_activo_mpl  BIT          NOT NULL CONSTRAINT DF_Marca_Placa_es_activo DEFAULT (1),
    CONSTRAINT PK_Marca_Placa PRIMARY KEY (id_marca_placa),
    CONSTRAINT UQ_Marca_Placa_nombre UNIQUE (nombre_mpl)
);

CREATE TABLE dbo.Color_Placa (
    id_color_placa INT IDENTITY(1,1) NOT NULL,
    id_marca_placa INT          NOT NULL,
    nombre_cpl     NVARCHAR(60) NULL,
    codigo_cpl     NVARCHAR(30) NULL,
    tiene_veta_cpl BIT          NOT NULL CONSTRAINT DF_Color_Placa_tiene_veta DEFAULT (0),
    es_activo_cpl  BIT          NOT NULL CONSTRAINT DF_Color_Placa_es_activo DEFAULT (1),
    CONSTRAINT PK_Color_Placa PRIMARY KEY (id_color_placa),
    CONSTRAINT FK_Color_Placa_Marca_Placa FOREIGN KEY (id_marca_placa) REFERENCES dbo.Marca_Placa (id_marca_placa),
    CONSTRAINT CK_Color_Placa_nombre_o_codigo CHECK (nombre_cpl IS NOT NULL OR codigo_cpl IS NOT NULL)
    -- UQ (marca, código) se implementa como índice único filtrado en 02_indices.sql:
    -- un UNIQUE común admitiría un solo color sin código por marca.
);

CREATE TABLE dbo.Marca_Pintura (
    id_marca_pintura INT IDENTITY(1,1) NOT NULL,
    nombre_mpi       NVARCHAR(50) NOT NULL,
    es_activo_mpi    BIT          NOT NULL CONSTRAINT DF_Marca_Pintura_es_activo DEFAULT (1),
    CONSTRAINT PK_Marca_Pintura PRIMARY KEY (id_marca_pintura),
    CONSTRAINT UQ_Marca_Pintura_nombre UNIQUE (nombre_mpi)
);

CREATE TABLE dbo.Color_Laca (
    id_color_laca    INT IDENTITY(1,1) NOT NULL,
    id_marca_pintura INT          NOT NULL,
    nombre_cla       NVARCHAR(60) NULL,
    codigo_cla       NVARCHAR(30) NULL,
    es_activo_cla    BIT          NOT NULL CONSTRAINT DF_Color_Laca_es_activo DEFAULT (1),
    CONSTRAINT PK_Color_Laca PRIMARY KEY (id_color_laca),
    CONSTRAINT FK_Color_Laca_Marca_Pintura FOREIGN KEY (id_marca_pintura) REFERENCES dbo.Marca_Pintura (id_marca_pintura),
    CONSTRAINT CK_Color_Laca_nombre_o_codigo CHECK (nombre_cla IS NOT NULL OR codigo_cla IS NOT NULL)
);

CREATE TABLE dbo.Terminacion_Laca (
    id_terminacion_laca INT IDENTITY(1,1) NOT NULL,
    nombre_tla          NVARCHAR(30) NOT NULL,
    es_activo_tla       BIT          NOT NULL CONSTRAINT DF_Terminacion_Laca_es_activo DEFAULT (1),
    CONSTRAINT PK_Terminacion_Laca PRIMARY KEY (id_terminacion_laca),
    CONSTRAINT UQ_Terminacion_Laca_nombre UNIQUE (nombre_tla)
);

/* --- Generalización Material -> Placa / Liston --------------------------------
   La FK compuesta (id, tipo_mat) garantiza en la base que una Placa solo pueda
   colgar de un Material de tipo 'PLACA' y un Liston de uno de tipo 'LISTON'.
   ---------------------------------------------------------------------------- */
CREATE TABLE dbo.Material (
    id_material INT IDENTITY(1,1) NOT NULL,
    tipo_mat    VARCHAR(10) NOT NULL,
    CONSTRAINT PK_Material PRIMARY KEY (id_material),
    CONSTRAINT CK_Material_tipo CHECK (tipo_mat IN ('PLACA', 'LISTON')),
    CONSTRAINT UQ_Material_id_tipo UNIQUE (id_material, tipo_mat)   -- destino de la FK compuesta
);

CREATE TABLE dbo.Placa (
    id_placa       INT          NOT NULL,   -- mismo valor que Material.id_material (no es IDENTITY)
    tipo_mat       VARCHAR(10)  NOT NULL CONSTRAINT DF_Placa_tipo_mat DEFAULT ('PLACA'),
    id_color_placa INT          NOT NULL,
    espesor_pla    DECIMAL(4,2) NOT NULL,   -- cm: 1,8 · 1,5 · 0,9 · 0,55
    largo_pla      DECIMAL(6,1) NOT NULL,   -- placa entera, sentido de la veta
    ancho_pla      DECIMAL(6,1) NOT NULL,
    es_activo_pla  BIT          NOT NULL CONSTRAINT DF_Placa_es_activo DEFAULT (1),
    CONSTRAINT PK_Placa PRIMARY KEY (id_placa),
    CONSTRAINT CK_Placa_tipo CHECK (tipo_mat = 'PLACA'),
    CONSTRAINT FK_Placa_Material FOREIGN KEY (id_placa, tipo_mat) REFERENCES dbo.Material (id_material, tipo_mat),
    CONSTRAINT FK_Placa_Color_Placa FOREIGN KEY (id_color_placa) REFERENCES dbo.Color_Placa (id_color_placa),
    CONSTRAINT CK_Placa_medidas CHECK (espesor_pla > 0 AND largo_pla > 0 AND ancho_pla > 0),
    CONSTRAINT UQ_Placa_color_espesor_medidas UNIQUE (id_color_placa, espesor_pla, largo_pla, ancho_pla)
);

CREATE TABLE dbo.Liston (
    id_liston              INT          NOT NULL,
    tipo_mat               VARCHAR(10)  NOT NULL CONSTRAINT DF_Liston_tipo_mat DEFAULT ('LISTON'),
    nombre_lis             NVARCHAR(50) NOT NULL,
    seccion_ancho_pulg_lis DECIMAL(4,2) NOT NULL,
    seccion_alto_pulg_lis  DECIMAL(4,2) NOT NULL,
    es_activo_lis          BIT          NOT NULL CONSTRAINT DF_Liston_es_activo DEFAULT (1),
    CONSTRAINT PK_Liston PRIMARY KEY (id_liston),
    CONSTRAINT CK_Liston_tipo CHECK (tipo_mat = 'LISTON'),
    CONSTRAINT FK_Liston_Material FOREIGN KEY (id_liston, tipo_mat) REFERENCES dbo.Material (id_material, tipo_mat),
    CONSTRAINT CK_Liston_seccion CHECK (seccion_ancho_pulg_lis > 0 AND seccion_alto_pulg_lis > 0)
);

CREATE TABLE dbo.Tipo_Filo (
    id_tipo_filo            INT IDENTITY(1,1) NOT NULL,
    nombre_tfi              NVARCHAR(30) NOT NULL,
    espesor_mm_tfi          DECIMAL(4,2) NOT NULL,
    descuento_por_canto_tfi DECIMAL(5,2) NOT NULL,   -- cm que se restan en la medida de corte
    CONSTRAINT PK_Tipo_Filo PRIMARY KEY (id_tipo_filo),
    CONSTRAINT UQ_Tipo_Filo_nombre UNIQUE (nombre_tfi),
    CONSTRAINT CK_Tipo_Filo_valores CHECK (espesor_mm_tfi >= 0 AND descuento_por_canto_tfi >= 0)
);
GO

/* =============================================================================
   4. CATÁLOGOS DEL DESPIECE
   ============================================================================= */

CREATE TABLE dbo.Tipo_Armado (
    id_tipo_armado  INT IDENTITY(1,1) NOT NULL,
    nombre_tar      NVARCHAR(50)  NOT NULL,
    es_cajonera_tar BIT           NOT NULL,
    descripcion_tar NVARCHAR(200) NULL,
    CONSTRAINT PK_Tipo_Armado PRIMARY KEY (id_tipo_armado),
    CONSTRAINT UQ_Tipo_Armado_nombre UNIQUE (nombre_tar)
);

CREATE TABLE dbo.Estilo_Frente (
    id_estilo_frente      INT IDENTITY(1,1) NOT NULL,
    nombre_efr            NVARCHAR(50)  NOT NULL,
    luz_superior_efr      DECIMAL(5,2)  NOT NULL,   -- negativa = el frente sobresale
    luz_inferior_efr      DECIMAL(5,2)  NOT NULL,
    luz_entre_frentes_efr DECIMAL(5,2)  NOT NULL,
    descripcion_efr       NVARCHAR(200) NULL,
    es_activo_efr         BIT           NOT NULL CONSTRAINT DF_Estilo_Frente_es_activo DEFAULT (1),
    CONSTRAINT PK_Estilo_Frente PRIMARY KEY (id_estilo_frente),
    CONSTRAINT UQ_Estilo_Frente_nombre UNIQUE (nombre_efr),
    CONSTRAINT CK_Estilo_Frente_luz_entre CHECK (luz_entre_frentes_efr >= 0)
);

CREATE TABLE dbo.Tipo_Pieza (
    id_tipo_pieza     INT IDENTITY(1,1) NOT NULL,
    nombre_tpi        NVARCHAR(50) NOT NULL,
    es_frente_tpi     BIT          NOT NULL,   -- usa la placa y la laca de frentes del módulo
    veta_vertical_tpi BIT          NOT NULL,   -- sentido de la veta por defecto
    CONSTRAINT PK_Tipo_Pieza PRIMARY KEY (id_tipo_pieza),
    CONSTRAINT UQ_Tipo_Pieza_nombre UNIQUE (nombre_tpi)
);

CREATE TABLE dbo.Tipo_Guia (
    id_tipo_guia          INT IDENTITY(1,1) NOT NULL,
    nombre_tgu            NVARCHAR(50) NOT NULL,
    marca_tgu             NVARCHAR(50) NULL,
    espacio_adicional_tgu DECIMAL(5,2) NOT NULL CONSTRAINT DF_Tipo_Guia_espacio DEFAULT (0),
    es_activo_tgu         BIT          NOT NULL CONSTRAINT DF_Tipo_Guia_es_activo DEFAULT (1),
    CONSTRAINT PK_Tipo_Guia PRIMARY KEY (id_tipo_guia),
    CONSTRAINT UQ_Tipo_Guia_nombre UNIQUE (nombre_tgu),
    CONSTRAINT CK_Tipo_Guia_espacio CHECK (espacio_adicional_tgu >= 0)
);

CREATE TABLE dbo.Largo_Guia (
    id_largo_guia INT IDENTITY(1,1) NOT NULL,
    id_tipo_guia  INT          NOT NULL,
    largo_lgu     DECIMAL(6,1) NOT NULL,
    CONSTRAINT PK_Largo_Guia PRIMARY KEY (id_largo_guia),
    CONSTRAINT FK_Largo_Guia_Tipo_Guia FOREIGN KEY (id_tipo_guia) REFERENCES dbo.Tipo_Guia (id_tipo_guia) ON DELETE CASCADE,
    CONSTRAINT UQ_Largo_Guia_tipo_largo UNIQUE (id_tipo_guia, largo_lgu),
    CONSTRAINT CK_Largo_Guia_largo CHECK (largo_lgu > 0)
);

CREATE TABLE dbo.Pieza_Guia (
    id_pieza_guia       INT IDENTITY(1,1) NOT NULL,
    id_tipo_guia        INT          NOT NULL,
    id_tipo_pieza       INT          NOT NULL,
    cantidad_pgu        INT          NOT NULL,
    descuento_ancho_pgu DECIMAL(5,2) NULL,   -- NULL = la pieza no usa esa medida
    descuento_largo_pgu DECIMAL(5,2) NULL,
    descuento_alto_pgu  DECIMAL(5,2) NULL,
    alto_fijo_pgu       DECIMAL(6,1) NULL,   -- alto definido por la marca (contrafrente de guía oculta)
    CONSTRAINT PK_Pieza_Guia PRIMARY KEY (id_pieza_guia),
    CONSTRAINT FK_Pieza_Guia_Tipo_Guia  FOREIGN KEY (id_tipo_guia)  REFERENCES dbo.Tipo_Guia (id_tipo_guia) ON DELETE CASCADE,
    CONSTRAINT FK_Pieza_Guia_Tipo_Pieza FOREIGN KEY (id_tipo_pieza) REFERENCES dbo.Tipo_Pieza (id_tipo_pieza),
    CONSTRAINT UQ_Pieza_Guia_guia_pieza UNIQUE (id_tipo_guia, id_tipo_pieza),
    CONSTRAINT CK_Pieza_Guia_cantidad CHECK (cantidad_pgu > 0),
    CONSTRAINT CK_Pieza_Guia_valores CHECK (descuento_ancho_pgu >= 0 AND descuento_largo_pgu >= 0
                                            AND descuento_alto_pgu >= 0 AND alto_fijo_pgu > 0),
    CONSTRAINT CK_Pieza_Guia_alto_unico CHECK (NOT (descuento_alto_pgu IS NOT NULL AND alto_fijo_pgu IS NOT NULL)),
    -- Toda pieza es un rectángulo: usa exactamente dos de las tres medidas.
    CONSTRAINT CK_Pieza_Guia_dos_medidas CHECK (
          CASE WHEN descuento_ancho_pgu IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN descuento_largo_pgu IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN descuento_alto_pgu IS NOT NULL OR alto_fijo_pgu IS NOT NULL THEN 1 ELSE 0 END = 2)
);
GO

/* =============================================================================
   5. ESTRUCTURA DEL MUEBLE
   ============================================================================= */

CREATE TABLE dbo.Zocalo (
    id_zocalo              INT IDENTITY(1,1) NOT NULL,
    id_mueble              INT           NOT NULL,
    id_placa               INT           NOT NULL,   -- partes visibles
    id_placa_oculta        INT           NULL,       -- NULL = misma placa
    descripcion_zoc        NVARCHAR(100) NULL,
    largo_zoc              DECIMAL(6,1)  NOT NULL,
    alto_zoc               DECIMAL(6,1)  NOT NULL,
    profundidad_zoc        DECIMAL(6,1)  NOT NULL,
    cantidad_refuerzos_zoc INT           NOT NULL CONSTRAINT DF_Zocalo_refuerzos DEFAULT (0),
    CONSTRAINT PK_Zocalo PRIMARY KEY (id_zocalo),
    CONSTRAINT FK_Zocalo_Mueble        FOREIGN KEY (id_mueble)       REFERENCES dbo.Mueble (id_mueble) ON DELETE CASCADE,
    CONSTRAINT FK_Zocalo_Placa         FOREIGN KEY (id_placa)        REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Zocalo_Placa_oculta  FOREIGN KEY (id_placa_oculta) REFERENCES dbo.Placa (id_placa),
    CONSTRAINT CK_Zocalo_medidas   CHECK (largo_zoc > 0 AND alto_zoc > 0 AND profundidad_zoc > 0),
    CONSTRAINT CK_Zocalo_refuerzos CHECK (cantidad_refuerzos_zoc >= 0)
);

CREATE TABLE dbo.Modulo (
    id_modulo                   INT IDENTITY(1,1) NOT NULL,
    id_mueble                   INT           NOT NULL,
    id_tipo_armado              INT           NOT NULL,
    id_estilo_frente            INT           NULL,     -- NULL = luces personalizadas
    id_placa                    INT           NOT NULL, -- estructura
    id_placa_frentes            INT           NULL,     -- NULL = misma que la estructura
    id_placa_cajones            INT           NULL,     -- NULL = misma que la estructura
    id_placa_fondo              INT           NULL,     -- NULL = no lleva fondo
    id_liston                   INT           NULL,     -- NULL = no lleva pinos
    id_color_laca_frentes       INT           NULL,     -- NULL = frentes sin laquear
    id_terminacion_laca_frentes INT           NULL,
    nombre_mod                  NVARCHAR(100) NULL,
    ancho_mod                   DECIMAL(6,1)  NOT NULL,
    alto_mod                    DECIMAL(6,1)  NOT NULL, -- sin zócalo
    profundidad_mod             DECIMAL(6,1)  NOT NULL,
    lleva_techo_mod             BIT           NOT NULL,
    ancho_faja_mod              DECIMAL(6,1)  NULL,     -- solo cajoneras
    cantidad_estantes_mod       INT           NOT NULL CONSTRAINT DF_Modulo_estantes DEFAULT (0),
    cantidad_puertas_mod        INT           NOT NULL CONSTRAINT DF_Modulo_puertas DEFAULT (0),
    luz_superior_mod            DECIMAL(5,2)  NOT NULL, -- negativa = el frente sobresale
    luz_inferior_mod            DECIMAL(5,2)  NOT NULL,
    luz_entre_frentes_mod       DECIMAL(5,2)  NOT NULL,
    -- Costados de puertas y frentes: 0,3; junto a otro módulo 0,15 (entre los dos suman 0,3).
    luz_izquierda_mod           DECIMAL(5,2)  NOT NULL CONSTRAINT DF_Modulo_luz_izquierda DEFAULT (0.3),
    luz_derecha_mod             DECIMAL(5,2)  NOT NULL CONSTRAINT DF_Modulo_luz_derecha DEFAULT (0.3),
    -- Módulos iguales: se cargan una vez; el listado multiplica sus piezas.
    cantidad_mod                INT           NOT NULL CONSTRAINT DF_Modulo_cantidad DEFAULT (1),
    CONSTRAINT PK_Modulo PRIMARY KEY (id_modulo),
    CONSTRAINT FK_Modulo_Mueble           FOREIGN KEY (id_mueble)        REFERENCES dbo.Mueble (id_mueble) ON DELETE CASCADE,
    CONSTRAINT FK_Modulo_Tipo_Armado      FOREIGN KEY (id_tipo_armado)   REFERENCES dbo.Tipo_Armado (id_tipo_armado),
    CONSTRAINT FK_Modulo_Estilo_Frente    FOREIGN KEY (id_estilo_frente) REFERENCES dbo.Estilo_Frente (id_estilo_frente),
    CONSTRAINT FK_Modulo_Placa            FOREIGN KEY (id_placa)         REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Modulo_Placa_frentes    FOREIGN KEY (id_placa_frentes) REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Modulo_Placa_cajones    FOREIGN KEY (id_placa_cajones) REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Modulo_Placa_fondo      FOREIGN KEY (id_placa_fondo)   REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Modulo_Liston           FOREIGN KEY (id_liston)        REFERENCES dbo.Liston (id_liston),
    CONSTRAINT FK_Modulo_Color_Laca       FOREIGN KEY (id_color_laca_frentes)       REFERENCES dbo.Color_Laca (id_color_laca),
    CONSTRAINT FK_Modulo_Terminacion_Laca FOREIGN KEY (id_terminacion_laca_frentes) REFERENCES dbo.Terminacion_Laca (id_terminacion_laca),
    CONSTRAINT CK_Modulo_medidas    CHECK (ancho_mod > 0 AND alto_mod > 0 AND profundidad_mod > 0),
    CONSTRAINT CK_Modulo_faja       CHECK (ancho_faja_mod > 0),
    CONSTRAINT CK_Modulo_cantidades CHECK (cantidad_estantes_mod >= 0 AND cantidad_puertas_mod >= 0),
    CONSTRAINT CK_Modulo_luz_entre  CHECK (luz_entre_frentes_mod >= 0),
    CONSTRAINT CK_Modulo_luz_costados CHECK (luz_izquierda_mod >= 0 AND luz_derecha_mod >= 0),
    CONSTRAINT CK_Modulo_cantidad   CHECK (cantidad_mod BETWEEN 1 AND 50),
    -- Laca y terminación van juntas: las dos cargadas o las dos vacías.
    CONSTRAINT CK_Modulo_laca_terminacion CHECK (
        (id_color_laca_frentes IS NULL AND id_terminacion_laca_frentes IS NULL)
     OR (id_color_laca_frentes IS NOT NULL AND id_terminacion_laca_frentes IS NOT NULL))
    -- Reglas que dependen de otra tabla (ancho de faja solo en cajoneras; una
    -- cajonera no lleva techo, estantes, puertas ni pinos) se validan en la
    -- capa de negocio.
);

/* Tipos de pieza con la veta rotada al cargar el módulo (se respeta al recalcular). */
CREATE TABLE dbo.Modulo_Veta_Rotada (
    id_modulo     INT NOT NULL,
    id_tipo_pieza INT NOT NULL,
    CONSTRAINT PK_Modulo_Veta_Rotada PRIMARY KEY (id_modulo, id_tipo_pieza),
    CONSTRAINT FK_Modulo_Veta_Rotada_Modulo     FOREIGN KEY (id_modulo)     REFERENCES dbo.Modulo (id_modulo) ON DELETE CASCADE,
    CONSTRAINT FK_Modulo_Veta_Rotada_Tipo_Pieza FOREIGN KEY (id_tipo_pieza) REFERENCES dbo.Tipo_Pieza (id_tipo_pieza)
);

CREATE TABLE dbo.Cajon (
    id_cajon        INT IDENTITY(1,1) NOT NULL,
    id_modulo       INT          NOT NULL,
    id_tipo_guia    INT          NOT NULL,
    id_placa_piso   INT          NOT NULL,   -- telescópica: 5,5 mm; oculta: 18 o 15 mm
    orden_caj       INT          NOT NULL,   -- de arriba hacia abajo
    alto_caj        DECIMAL(6,1) NOT NULL,   -- alto estimado de la caja
    alto_frente_caj DECIMAL(6,1) NULL,       -- NULL = reparto en partes iguales
    largo_guia_caj  DECIMAL(6,1) NOT NULL,   -- propuesto según Largo_Guia, editable
    CONSTRAINT PK_Cajon PRIMARY KEY (id_cajon),
    CONSTRAINT FK_Cajon_Modulo     FOREIGN KEY (id_modulo)     REFERENCES dbo.Modulo (id_modulo) ON DELETE CASCADE,
    CONSTRAINT FK_Cajon_Tipo_Guia  FOREIGN KEY (id_tipo_guia)  REFERENCES dbo.Tipo_Guia (id_tipo_guia),
    CONSTRAINT FK_Cajon_Placa_piso FOREIGN KEY (id_placa_piso) REFERENCES dbo.Placa (id_placa),
    CONSTRAINT UQ_Cajon_modulo_orden UNIQUE (id_modulo, orden_caj),
    CONSTRAINT CK_Cajon_medidas CHECK (alto_caj > 0 AND alto_frente_caj > 0 AND largo_guia_caj > 0),
    CONSTRAINT CK_Cajon_alto_caja_frente CHECK (alto_caj <= alto_frente_caj)
);
GO

/* =============================================================================
   6. DESPIECE
   ============================================================================= */

CREATE TABLE dbo.Pieza (
    id_pieza                   INT IDENTITY(1,1) NOT NULL,
    -- Dueño de la pieza: exactamente uno de los cuatro (CK_Pieza_un_dueno)
    id_mueble                  INT           NULL,   -- pieza suelta
    id_modulo                  INT           NULL,   -- estructura / frentes del módulo
    id_cajon                   INT           NULL,   -- caja o frente de un cajón
    id_zocalo                  INT           NULL,   -- pieza del zócalo
    id_tipo_pieza              INT           NOT NULL,
    id_material                INT           NOT NULL,
    id_tipo_filo               INT           NULL,   -- NULL = filo SIN DEFINIR (bloquea el listado)
    id_color_placa_filo        INT           NULL,   -- NULL = mismo color que la pieza
    id_color_laca              INT           NULL,   -- NULL = no se laquea
    id_terminacion_laca        INT           NULL,
    descripcion_pie            NVARCHAR(100) NULL,
    cantidad_pie               INT           NOT NULL,
    medida_1_pie               DECIMAL(6,1)  NOT NULL,  -- medida FINAL, sentido de la veta
    medida_2_pie               DECIMAL(6,1)  NULL,      -- NULL solo en listones
    lleva_filo_superior_pie    BIT           NOT NULL CONSTRAINT DF_Pieza_filo_superior  DEFAULT (0),
    lleva_filo_inferior_pie    BIT           NOT NULL CONSTRAINT DF_Pieza_filo_inferior  DEFAULT (0),
    lleva_filo_izquierdo_pie   BIT           NOT NULL CONSTRAINT DF_Pieza_filo_izquierdo DEFAULT (0),
    lleva_filo_derecho_pie     BIT           NOT NULL CONSTRAINT DF_Pieza_filo_derecho   DEFAULT (0),
    es_editada_manualmente_pie BIT           NOT NULL CONSTRAINT DF_Pieza_editada        DEFAULT (0),
    CONSTRAINT PK_Pieza PRIMARY KEY (id_pieza),
    -- NO ACTION en los dueños: ver nota de reglas de borrado al inicio del script.
    CONSTRAINT FK_Pieza_Mueble           FOREIGN KEY (id_mueble)           REFERENCES dbo.Mueble (id_mueble),
    CONSTRAINT FK_Pieza_Modulo           FOREIGN KEY (id_modulo)           REFERENCES dbo.Modulo (id_modulo),
    CONSTRAINT FK_Pieza_Cajon            FOREIGN KEY (id_cajon)            REFERENCES dbo.Cajon (id_cajon),
    CONSTRAINT FK_Pieza_Zocalo           FOREIGN KEY (id_zocalo)           REFERENCES dbo.Zocalo (id_zocalo),
    CONSTRAINT FK_Pieza_Tipo_Pieza       FOREIGN KEY (id_tipo_pieza)       REFERENCES dbo.Tipo_Pieza (id_tipo_pieza),
    CONSTRAINT FK_Pieza_Material         FOREIGN KEY (id_material)         REFERENCES dbo.Material (id_material),
    CONSTRAINT FK_Pieza_Tipo_Filo        FOREIGN KEY (id_tipo_filo)        REFERENCES dbo.Tipo_Filo (id_tipo_filo),
    CONSTRAINT FK_Pieza_Color_Placa_filo FOREIGN KEY (id_color_placa_filo) REFERENCES dbo.Color_Placa (id_color_placa),
    CONSTRAINT FK_Pieza_Color_Laca       FOREIGN KEY (id_color_laca)       REFERENCES dbo.Color_Laca (id_color_laca),
    CONSTRAINT FK_Pieza_Terminacion_Laca FOREIGN KEY (id_terminacion_laca) REFERENCES dbo.Terminacion_Laca (id_terminacion_laca),
    CONSTRAINT CK_Pieza_un_dueno CHECK (
          CASE WHEN id_mueble IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN id_modulo IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN id_cajon  IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN id_zocalo IS NOT NULL THEN 1 ELSE 0 END = 1),
    CONSTRAINT CK_Pieza_cantidad CHECK (cantidad_pie > 0),
    CONSTRAINT CK_Pieza_medidas  CHECK (medida_1_pie > 0 AND medida_2_pie > 0),
    CONSTRAINT CK_Pieza_laca_terminacion CHECK (
        (id_color_laca IS NULL AND id_terminacion_laca IS NULL)
     OR (id_color_laca IS NOT NULL AND id_terminacion_laca IS NOT NULL))
    -- Validado en la capa de negocio: pieza laqueada => "Sin filo"; "Sin filo" =>
    -- ningún canto marcado; medida_2 obligatoria si el material es una placa.
);

/* =============================================================================
   7. INVENTARIO
   ============================================================================= */

CREATE TABLE dbo.Retazo (
    id_retazo         INT IDENTITY(1,1) NOT NULL,
    id_placa          INT           NOT NULL,
    id_trabajo_origen INT           NULL,
    id_retazo_origen  INT           NULL,
    medida_1_ret      DECIMAL(6,1)  NOT NULL,   -- sentido de la veta
    medida_2_ret      DECIMAL(6,1)  NOT NULL,
    ubicacion_ret     NVARCHAR(100) NULL,
    fecha_alta_ret    DATE          NOT NULL CONSTRAINT DF_Retazo_fecha_alta DEFAULT (CAST(SYSDATETIME() AS DATE)),
    fecha_baja_ret    DATE          NULL,       -- NULL = disponible
    CONSTRAINT PK_Retazo PRIMARY KEY (id_retazo),
    CONSTRAINT FK_Retazo_Placa   FOREIGN KEY (id_placa)          REFERENCES dbo.Placa (id_placa),
    CONSTRAINT FK_Retazo_Trabajo FOREIGN KEY (id_trabajo_origen) REFERENCES dbo.Trabajo (id_trabajo) ON DELETE SET NULL,
    -- SQL Server no admite acciones en cascada en una autorrelación: NO ACTION.
    -- Los retazos no se borran, se dan de baja con fecha_baja_ret.
    CONSTRAINT FK_Retazo_Retazo  FOREIGN KEY (id_retazo_origen)  REFERENCES dbo.Retazo (id_retazo),
    CONSTRAINT CK_Retazo_medidas CHECK (medida_1_ret > 0 AND medida_2_ret > 0),
    CONSTRAINT CK_Retazo_fechas  CHECK (fecha_baja_ret >= fecha_alta_ret)
);
GO
