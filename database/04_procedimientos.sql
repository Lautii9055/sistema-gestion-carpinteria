/* =============================================================================
   Sistema de Gestión para Carpintería
   04 - Procedimientos almacenados
   -----------------------------------------------------------------------------
   Operaciones que tocan varias tablas y deben hacerse completas o no hacerse:
   se ejecutan dentro de una transacción con XACT_ABORT ON.
   ============================================================================= */

USE Carpinteria;
GO

/* ---------- sp_alta_placa ----------
   Crea una placa respetando la generalización Material -> Placa: inserta el
   Material y usa el id generado como id de la Placa. Devuelve el id nuevo. */
CREATE OR ALTER PROCEDURE dbo.sp_alta_placa
    @id_color_placa INT,
    @espesor_pla    DECIMAL(4,2),
    @largo_pla      DECIMAL(6,1),
    @ancho_pla      DECIMAL(6,1),
    @id_placa       INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
        INSERT INTO dbo.Material (tipo_mat) VALUES ('PLACA');
        SET @id_placa = SCOPE_IDENTITY();
        INSERT INTO dbo.Placa (id_placa, id_color_placa, espesor_pla, largo_pla, ancho_pla)
        VALUES (@id_placa, @id_color_placa, @espesor_pla, @largo_pla, @ancho_pla);
    COMMIT TRANSACTION;
END
GO

/* ---------- sp_alta_liston ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_alta_liston
    @nombre_lis             NVARCHAR(50),
    @seccion_ancho_pulg_lis DECIMAL(4,2),
    @seccion_alto_pulg_lis  DECIMAL(4,2),
    @id_liston              INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
        INSERT INTO dbo.Material (tipo_mat) VALUES ('LISTON');
        SET @id_liston = SCOPE_IDENTITY();
        INSERT INTO dbo.Liston (id_liston, nombre_lis, seccion_ancho_pulg_lis, seccion_alto_pulg_lis)
        VALUES (@id_liston, @nombre_lis, @seccion_ancho_pulg_lis, @seccion_alto_pulg_lis);
    COMMIT TRANSACTION;
END
GO

/* ---------- sp_eliminar_trabajo ----------
   SQL Server no permite varios caminos de borrado en cascada hacia Pieza, por
   eso sus FK son NO ACTION. Este procedimiento borra primero todas las piezas
   del trabajo (de sus muebles, módulos, cajones y zócalos) y después el
   trabajo; el resto (muebles, zócalos, módulos, cajones) cae en cascada y los
   retazos que se originaron en él quedan con id_trabajo_origen = NULL. */
CREATE OR ALTER PROCEDURE dbo.sp_eliminar_trabajo
    @id_trabajo INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;

        DELETE p
        FROM dbo.Pieza p
        WHERE p.id_mueble IN (SELECT id_mueble FROM dbo.Mueble WHERE id_trabajo = @id_trabajo)
           OR p.id_zocalo IN (SELECT z.id_zocalo FROM dbo.Zocalo z
                              JOIN dbo.Mueble m ON m.id_mueble = z.id_mueble
                              WHERE m.id_trabajo = @id_trabajo)
           OR p.id_modulo IN (SELECT mo.id_modulo FROM dbo.Modulo mo
                              JOIN dbo.Mueble m ON m.id_mueble = mo.id_mueble
                              WHERE m.id_trabajo = @id_trabajo)
           OR p.id_cajon  IN (SELECT c.id_cajon FROM dbo.Cajon c
                              JOIN dbo.Modulo mo ON mo.id_modulo = c.id_modulo
                              JOIN dbo.Mueble m  ON m.id_mueble  = mo.id_mueble
                              WHERE m.id_trabajo = @id_trabajo);

        DELETE FROM dbo.Trabajo WHERE id_trabajo = @id_trabajo;

        IF @@ROWCOUNT = 0
            THROW 50001, N'No existe el trabajo indicado.', 1;

    COMMIT TRANSACTION;
END
GO

/* ---------- sp_registrar_evento ----------
   Única forma en que la aplicación escribe en la auditoría. Recibe el código
   del evento (ej.: 'LOGIN_FALLIDO') y resuelve su id; si el código no existe,
   falla en vez de registrar algo incorrecto. */
CREATE OR ALTER PROCEDURE dbo.sp_registrar_evento
    @codigo_tev            VARCHAR(30),
    @id_usuario            INT           = NULL,
    @usuario_ingresado_aud NVARCHAR(50)  = NULL,
    @entidad_aud           VARCHAR(30)   = NULL,
    @id_entidad_aud        INT           = NULL,
    @detalle_aud           NVARCHAR(500) = NULL,
    @equipo_aud            NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @id_tipo_evento INT =
        (SELECT id_tipo_evento FROM dbo.Tipo_Evento WHERE codigo_tev = @codigo_tev);

    IF @id_tipo_evento IS NULL
        THROW 50002, N'Tipo de evento de auditoría inexistente.', 1;

    INSERT INTO dbo.Auditoria (id_tipo_evento, id_usuario, usuario_ingresado_aud,
                               entidad_aud, id_entidad_aud, detalle_aud, equipo_aud)
    VALUES (@id_tipo_evento, @id_usuario, @usuario_ingresado_aud,
            @entidad_aud, @id_entidad_aud, @detalle_aud, @equipo_aud);
END
GO
