/* =============================================================================
   Sistema de Gestión para Carpintería
   02 - Índices
   -----------------------------------------------------------------------------
   SQL Server crea índices automáticamente para PK y UNIQUE, pero NO para las
   claves foráneas. Indexar las FK acelera los JOIN y evita bloqueos al borrar
   o actualizar la tabla padre. Además se agregan índices para las búsquedas
   frecuentes (RF-06) y dos índices únicos filtrados.
   ============================================================================= */

USE Carpinteria;
GO

/* ---------- Índices únicos filtrados ----------
   "Código único por marca", pero solo entre los colores que tienen código.
   Un UNIQUE común trata los NULL como iguales y no permitiría dos colores sin
   código en la misma marca. */
CREATE UNIQUE INDEX UX_Color_Placa_marca_codigo ON dbo.Color_Placa (id_marca_placa, codigo_cpl)
    WHERE codigo_cpl IS NOT NULL;
CREATE UNIQUE INDEX UX_Color_Laca_marca_codigo ON dbo.Color_Laca (id_marca_pintura, codigo_cla)
    WHERE codigo_cla IS NOT NULL;
GO

/* ---------- Claves foráneas ---------- */
CREATE INDEX IX_Obra_cliente          ON dbo.Obra (id_cliente);
CREATE INDEX IX_Trabajo_obra          ON dbo.Trabajo (id_obra);
CREATE INDEX IX_Trabajo_estado        ON dbo.Trabajo (id_estado_trabajo);
CREATE INDEX IX_Mueble_trabajo        ON dbo.Mueble (id_trabajo);
CREATE INDEX IX_Zocalo_mueble         ON dbo.Zocalo (id_mueble);
CREATE INDEX IX_Modulo_mueble         ON dbo.Modulo (id_mueble);
CREATE INDEX IX_Cajon_modulo          ON dbo.Cajon (id_modulo);
CREATE INDEX IX_Pieza_mueble          ON dbo.Pieza (id_mueble)  WHERE id_mueble IS NOT NULL;
CREATE INDEX IX_Pieza_modulo          ON dbo.Pieza (id_modulo)  WHERE id_modulo IS NOT NULL;
CREATE INDEX IX_Pieza_cajon           ON dbo.Pieza (id_cajon)   WHERE id_cajon  IS NOT NULL;
CREATE INDEX IX_Pieza_zocalo          ON dbo.Pieza (id_zocalo)  WHERE id_zocalo IS NOT NULL;
CREATE INDEX IX_Pieza_material        ON dbo.Pieza (id_material);
CREATE INDEX IX_Color_Placa_marca     ON dbo.Color_Placa (id_marca_placa);
CREATE INDEX IX_Color_Laca_marca      ON dbo.Color_Laca (id_marca_pintura);
CREATE INDEX IX_Placa_color           ON dbo.Placa (id_color_placa);
CREATE INDEX IX_Retazo_trabajo        ON dbo.Retazo (id_trabajo_origen) WHERE id_trabajo_origen IS NOT NULL;
CREATE INDEX IX_Auditoria_usuario     ON dbo.Auditoria (id_usuario) WHERE id_usuario IS NOT NULL;
CREATE INDEX IX_Auditoria_tipo_evento ON dbo.Auditoria (id_tipo_evento, fecha_hora_aud DESC);
GO

/* ---------- Búsquedas frecuentes (RF-06) ---------- */
CREATE INDEX IX_Cliente_apellido_nombre ON dbo.Cliente (apellido_cli, nombre_cli);
CREATE INDEX IX_Cliente_telefono        ON dbo.Cliente (telefono_cli);
CREATE INDEX IX_Obra_direccion          ON dbo.Obra (direccion_obr, localidad_obr);
CREATE INDEX IX_Obra_alias              ON dbo.Obra (nombre_obr) WHERE nombre_obr IS NOT NULL;
CREATE INDEX IX_Trabajo_fecha_alta      ON dbo.Trabajo (fecha_alta_tra);
CREATE INDEX IX_Color_Placa_nombre      ON dbo.Color_Placa (nombre_cpl);
CREATE INDEX IX_Color_Laca_nombre       ON dbo.Color_Laca (nombre_cla);

/* Retazos disponibles de una placa: el filtro deja en el índice solo los que
   no tienen fecha de baja, así la búsqueda recorre únicamente el stock real. */
CREATE INDEX IX_Retazo_disponibles ON dbo.Retazo (id_placa)
    INCLUDE (medida_1_ret, medida_2_ret, ubicacion_ret)
    WHERE fecha_baja_ret IS NULL;

/* Auditoría: la consulta habitual es "lo último que pasó", filtrando por fecha. */
CREATE INDEX IX_Auditoria_fecha_hora ON dbo.Auditoria (fecha_hora_aud DESC);
GO
