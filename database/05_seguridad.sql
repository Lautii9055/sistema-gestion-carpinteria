/* =============================================================================
   Sistema de Gestión para Carpintería
   05 - Seguridad: usuario de la aplicación y mínimo privilegio
   -----------------------------------------------------------------------------
   La aplicación NO se conecta con la cuenta de administrador. Usa un login
   propio (app_carpinteria) con solo los permisos que necesita:
     - leer, agregar, modificar y borrar datos, y ejecutar procedimientos;
     - hacer copias de seguridad;
     - SIN permisos para crear, modificar o borrar tablas;
     - SIN permisos para modificar o borrar la auditoría;
     - SIN permisos para modificar el catálogo de tipos de evento.
   Si alguien obtuviera la contraseña de la aplicación, no podría borrar la
   estructura de la base ni ocultar lo que hizo.

   ANTES DE EJECUTAR
   1. Habilitar la autenticación de SQL Server (modo mixto):
      SSMS > clic derecho en el servidor > Properties > Security >
      "SQL Server and Windows Authentication mode" > OK.
      Después reiniciar el servicio: clic derecho en el servidor > Restart.
   2. Reemplazar la contraseña en la línea marcada abajo por una contraseña
      larga y aleatoria (16 caracteres o más).
   3. Ejecutar con F5 y cerrar el archivo SIN GUARDAR: la contraseña no debe
      quedar escrita en ningún archivo ni subirse a GitHub. La aplicación la
      va a guardar en el Administrador de credenciales de Windows.

   Es re-ejecutable: si el login o el rol ya existen, no los vuelve a crear.
   ============================================================================= */

/* ---------- 1. Login del servidor ---------- */
USE master;
GO

DECLARE @contrasena NVARCHAR(128) = N'REEMPLAZAR_ANTES_DE_EJECUTAR';   -- <<< CAMBIAR

IF @contrasena = N'REEMPLAZAR_ANTES_DE_EJECUTAR'
BEGIN
    RAISERROR (N'Reemplazá la contraseña de app_carpinteria antes de ejecutar el script.', 16, 1);
    SET NOEXEC ON;   -- el resto del script no se ejecuta
END

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_carpinteria')
BEGIN
    -- CREATE LOGIN no acepta variables: se arma la sentencia escapando la contraseña.
    DECLARE @sql NVARCHAR(MAX) =
        N'CREATE LOGIN app_carpinteria WITH PASSWORD = ' + QUOTENAME(@contrasena, '''') +
        N', DEFAULT_DATABASE = Carpinteria, CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;';
    EXEC sys.sp_executesql @sql;
END
GO

/* La cuenta "sa" (administrador de SQL Server) es el primer blanco de un
   ataque de fuerza bruta. No se usa: se deshabilita. */
IF EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = N'sa' AND is_disabled = 0)
    ALTER LOGIN sa DISABLE;
GO

/* ---------- 2. Usuario y rol en la base ---------- */
USE Carpinteria;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'rol_app' AND type = 'R')
    CREATE ROLE rol_app;
GO

-- Permisos sobre los datos del esquema dbo (no incluyen ALTER, CREATE ni DROP)
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO rol_app;

-- La auditoría solo crece: no se puede modificar ni borrar desde la aplicación
DENY UPDATE, DELETE ON dbo.Auditoria TO rol_app;

-- El catálogo de eventos es fijo
DENY INSERT, UPDATE, DELETE ON dbo.Tipo_Evento TO rol_app;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'app_carpinteria')
    CREATE USER app_carpinteria FOR LOGIN app_carpinteria;
GO

ALTER ROLE rol_app            ADD MEMBER app_carpinteria;
ALTER ROLE db_backupoperator  ADD MEMBER app_carpinteria;   -- copias de seguridad (RNF-08)
GO

/* ---------- 3. Verificación ----------
   Debe mostrar a app_carpinteria en rol_app y db_backupoperator. */
SELECT r.name AS rol, m.name AS miembro
FROM sys.database_role_members rm
JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id
WHERE m.name = N'app_carpinteria';

-- Permisos explícitos del rol (GRANT y DENY)
SELECT dp.state_desc AS estado, dp.permission_name AS permiso,
       ISNULL(OBJECT_NAME(dp.major_id), 'esquema dbo') AS sobre
FROM sys.database_permissions dp
WHERE dp.grantee_principal_id = DATABASE_PRINCIPAL_ID(N'rol_app')
ORDER BY sobre, estado;
GO

/* ---------- 4. Prueba de mínimo privilegio (opcional) ----------
   Conectarse en SSMS con "SQL Server Authentication", usuario app_carpinteria,
   y probar:

   SELECT TOP 5 * FROM dbo.Estado_Trabajo;     -- funciona
   EXEC dbo.sp_registrar_evento 'LOGIN_OK';    -- funciona
   DELETE FROM dbo.Auditoria;                  -- error: permiso denegado
   DROP TABLE dbo.Retazo;                      -- error: permiso denegado
*/

SET NOEXEC OFF;
GO
