/* =============================================================================
   Sistema de Gestión para Carpintería
   03 - Datos iniciales
   -----------------------------------------------------------------------------
   Catálogos y valores que el sistema necesita para funcionar desde el primer
   uso. Se cargan dentro de una transacción: si algo falla, no queda nada a
   medias.
   ============================================================================= */

USE Carpinteria;
GO

SET XACT_ABORT ON;   -- ante cualquier error se revierte toda la transacción
BEGIN TRANSACTION;

/* ---------- Usuario inicial ----------
   Contraseña provisoria: Cambiar.123  (hash bcrypt, costo 12).
   debe_cambiar_contrasena_usu = 1 -> el sistema obliga a cambiarla al ingresar. */
INSERT INTO dbo.Usuario (nombre_usuario_usu, hash_contrasena_usu, debe_cambiar_contrasena_usu, nombre_completo_usu)
VALUES (N'admin', '$2b$12$x5sQjw8cM3/NzwmRyNf0hOutyGWaR9aO8j7INOoonCo5MlV9AQ3D2', 1, N'Administrador');

/* ---------- Parámetros fijos ---------- */
INSERT INTO dbo.Parametro (clave_par, valor_par, unidad_par, descripcion_par) VALUES
    ('luz_lateral_frente',        0.3, N'cm', N'Luz a cada costado de puertas y frentes de cajón'),
    ('luz_entre_puertas',         0.3, N'cm', N'Luz entre puertas contiguas'),
    ('tolerancia_sobresale_guia', 0.5, N'cm', N'Cuánto puede sobresalir la guía al elegir su largo'),
    ('retiro_zocalo',             1.5, N'cm', N'Retiro del zócalo respecto del frente del mueble'),
    ('porcentaje_sena',          60.0, N'%',  N'Seña sugerida sobre el monto total'),
    -- Seguridad del ingreso
    ('max_intentos_login',        5,   N'intentos',   N'Contraseñas incorrectas seguidas antes de bloquear al usuario'),
    ('minutos_bloqueo',          15,   N'min',        N'Duración del bloqueo por intentos fallidos'),
    ('minutos_inactividad',      15,   N'min',        N'Tiempo sin uso tras el cual se cierra la sesión'),
    ('largo_minimo_contrasena',  10,   N'caracteres', N'Largo mínimo de una contraseña nueva');

/* ---------- Tipos de evento de auditoría ---------- */
INSERT INTO dbo.Tipo_Evento (codigo_tev, descripcion_tev, es_critico_tev) VALUES
    ('LOGIN_OK',              N'Ingreso correcto',                          0),
    ('LOGIN_FALLIDO',         N'Contraseña o usuario incorrecto',           0),
    ('USUARIO_BLOQUEADO',     N'Usuario bloqueado por intentos fallidos',   1),
    ('LOGOUT',                N'Cierre de sesión',                          0),
    ('CIERRE_INACTIVIDAD',    N'Sesión cerrada por inactividad',            0),
    ('CAMBIO_CONTRASENA',     N'Cambio de la propia contraseña',            0),
    ('BLANQUEO_CONTRASENA',   N'Contraseña blanqueada por otro usuario',    1),
    ('ALTA_USUARIO',          N'Alta de usuario',                           1),
    ('BAJA_USUARIO',          N'Baja de usuario',                           1),
    ('REACTIVACION_USUARIO',  N'Reactivación de usuario',                   1),
    ('ELIMINACION_TRABAJO',   N'Eliminación de un trabajo completo',        1),
    ('CAMBIO_MONTO',          N'Cambio del monto total o de la seña',       1),
    ('CAMBIO_ESTADO_TRABAJO', N'Cambio de estado de un trabajo',            0),
    ('CAMBIO_PARAMETRO',      N'Cambio de un parámetro del sistema',        1),
    ('BACKUP_OK',             N'Copia de seguridad realizada',              0),
    ('BACKUP_ERROR',          N'Falló la copia de seguridad',               1);

/* ---------- Estados del trabajo ---------- */
INSERT INTO dbo.Estado_Trabajo (orden_etr, nombre_etr) VALUES
    (1, N'Presupuestado'),
    (2, N'Confirmado'),
    (3, N'En producción'),
    (4, N'Terminado'),
    (5, N'Instalado'),
    (6, N'Cobrado'),
    (7, N'Cancelado');

/* ---------- Tipos de armado ---------- */
INSERT INTO dbo.Tipo_Armado (nombre_tar, es_cajonera_tar, descripcion_tar) VALUES
    (N'Módulo',                        0, N'Piso y techo enteros, laterales de luz (se agujerean pisos y techos)'),
    (N'Cajonera con fajas de luz',     1, N'Laterales enteros, 4 fajas entre ellos (se agujerean los laterales)'),
    (N'Cajonera con laterales de luz', 1, N'4 fajas enteras, laterales entre ellas');

/* ---------- Estilos de frente ---------- */
INSERT INTO dbo.Estilo_Frente (nombre_efr, luz_superior_efr, luz_inferior_efr, luz_entre_frentes_efr, descripcion_efr) VALUES
    (N'Con tirador',               0.4,  0.4, 0.3, NULL),
    (N'Cajonera con tirador',      0.6,  0.6, 0.3, NULL),
    (N'Alacena (sobresale abajo)', 0.0, -1.3, 0.3, N'Puertas parejas arriba; sobresalen 1,3 cm abajo para abrirlas'),
    (N'Bajo mesada con gola',      3.0,  0.0, 3.0, N'Rebajes en los laterales hechos en el taller: 5 x 3,6 cm arriba y 7 x 3,6 cm entre frentes de cajón');

/* ---------- Tipos de filo ---------- */
INSERT INTO dbo.Tipo_Filo (nombre_tfi, espesor_mm_tfi, descuento_por_canto_tfi) VALUES
    (N'Sin filo', 0.00, 0.00),
    (N'0,45 mm',  0.45, 0.00),
    (N'2 mm',     2.00, 0.20);

/* ---------- Terminaciones de laca ---------- */
INSERT INTO dbo.Terminacion_Laca (nombre_tla) VALUES (N'Mate'), (N'Semimate'), (N'Brillante');

/* ---------- Tipos de pieza (es_frente, veta_vertical) ---------- */
INSERT INTO dbo.Tipo_Pieza (nombre_tpi, es_frente_tpi, veta_vertical_tpi) VALUES
    (N'Piso',                    0, 0),
    (N'Techo',                   0, 0),
    (N'Lateral',                 0, 1),
    (N'Estante',                 0, 0),
    (N'Faja',                    0, 0),
    (N'Fondo',                   0, 1),
    (N'Puerta',                  1, 1),
    (N'Frente de cajón',         1, 0),
    (N'Pino',                    0, 0),
    (N'Lateral de cajón',        0, 0),
    (N'Contrafrente de cajón',   0, 0),
    (N'Frente interno de cajón', 0, 0),
    (N'Piso de cajón',           0, 0),
    (N'Frente de zócalo',        0, 0),
    (N'Trasera de zócalo',       0, 0),
    (N'Lateral de zócalo',       0, 0),
    (N'Refuerzo de zócalo',      0, 0),
    (N'Ajuste',                  0, 1),
    (N'Otra',                    0, 0);

/* ---------- Tipos de guía ---------- */
INSERT INTO dbo.Tipo_Guia (nombre_tgu, marca_tgu, espacio_adicional_tgu) VALUES
    (N'Telescópica cierre suave',          NULL,                 0.2),
    (N'Lateral oculto Rincón del Herraje', N'Rincón del Herraje', 1.1),
    (N'Lateral oculto Eurohard',           N'Eurohard',           0.8),
    (N'Lateral oculto Häfele',             N'Häfele',             0.8);

/* ---------- Piezas por tipo de guía ----------
   Medida = referencia - descuento. Referencias: ancho interior del módulo,
   largo de la guía y alto del cajón. NULL = la pieza no usa esa medida. */

-- Telescópica: 6,3 = 2 x 1,35 (guías) + 2 x 1,8 (laterales); 2,7 = 2 x 1,35 (guías)
INSERT INTO dbo.Pieza_Guia (id_tipo_guia, id_tipo_pieza, cantidad_pgu, descuento_ancho_pgu, descuento_largo_pgu, descuento_alto_pgu, alto_fijo_pgu)
SELECT g.id_tipo_guia, p.id_tipo_pieza, v.cantidad, v.d_ancho, v.d_largo, v.d_alto, NULL
FROM (VALUES
        (N'Lateral de cajón',        2, NULL, 0.0,  0.0),
        (N'Contrafrente de cajón',   1, 6.3,  NULL, 0.0),
        (N'Frente interno de cajón', 1, 6.3,  NULL, 3.0),
        (N'Piso de cajón',           1, 2.7,  0.0,  NULL)
     ) AS v (pieza, cantidad, d_ancho, d_largo, d_alto)
JOIN dbo.Tipo_Pieza p ON p.nombre_tpi = v.pieza
CROSS JOIN dbo.Tipo_Guia g
WHERE g.nombre_tgu = N'Telescópica cierre suave';

-- Laterales ocultos (las tres marcas): piso = (ancho interior - 7,5) x (largo guía - 1)
INSERT INTO dbo.Pieza_Guia (id_tipo_guia, id_tipo_pieza, cantidad_pgu, descuento_ancho_pgu, descuento_largo_pgu, descuento_alto_pgu, alto_fijo_pgu)
SELECT g.id_tipo_guia, p.id_tipo_pieza, 1, 7.5, 1.0, NULL, NULL
FROM dbo.Tipo_Guia g
JOIN dbo.Tipo_Pieza p ON p.nombre_tpi = N'Piso de cajón'
WHERE g.nombre_tgu LIKE N'Lateral oculto%';

/* PENDIENTE (datos de cada marca): contrafrente de guía oculta =
   (ancho interior - 8,7) x alto fijo de la marca. Cuando se conozca el alto:

INSERT INTO dbo.Pieza_Guia (id_tipo_guia, id_tipo_pieza, cantidad_pgu, descuento_ancho_pgu, descuento_largo_pgu, descuento_alto_pgu, alto_fijo_pgu)
SELECT g.id_tipo_guia, p.id_tipo_pieza, 1, 8.7, NULL, NULL, <alto de la marca>
FROM dbo.Tipo_Guia g JOIN dbo.Tipo_Pieza p ON p.nombre_tpi = N'Contrafrente de cajón'
WHERE g.nombre_tgu = N'Lateral oculto <marca>';
*/

/* PENDIENTE (datos): largos disponibles de cada guía. Ejemplo:
INSERT INTO dbo.Largo_Guia (id_tipo_guia, largo_lgu)
SELECT g.id_tipo_guia, v.largo
FROM dbo.Tipo_Guia g
CROSS JOIN (VALUES (30.0), (35.0), (40.0), (45.0), (50.0)) AS v (largo)
WHERE g.nombre_tgu = N'Telescópica cierre suave';
*/

/* ---------- Listón: pino 2 x 1" ----------
   Material y Liston comparten id: se inserta el Material y se toma el id
   generado con SCOPE_IDENTITY(). */
DECLARE @id_material INT;
INSERT INTO dbo.Material (tipo_mat) VALUES ('LISTON');
SET @id_material = SCOPE_IDENTITY();
INSERT INTO dbo.Liston (id_liston, nombre_lis, seccion_ancho_pulg_lis, seccion_alto_pulg_lis)
VALUES (@id_material, N'Pino', 2, 1);

/* ---------- Marcas de pintura ---------- */
INSERT INTO dbo.Marca_Pintura (nombre_mpi) VALUES (N'Alba'), (N'Sherwin Williams');

COMMIT TRANSACTION;
GO
