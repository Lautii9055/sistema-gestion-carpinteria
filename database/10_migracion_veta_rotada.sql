/* =============================================================================
   Sistema de Gestión para Carpintería
   10 - Migración: tipos de pieza con la veta rotada en cada módulo (req. v3.0)
   -----------------------------------------------------------------------------
   Al cargar un módulo se puede rotar el sentido de la veta por tipo de pieza
   (ej.: el fondo o las puertas). Se guarda acá para que un recálculo del
   módulo respete la elección. Una fila = ese tipo de pieza va rotado.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF OBJECT_ID(N'dbo.Modulo_Veta_Rotada', N'U') IS NULL
CREATE TABLE dbo.Modulo_Veta_Rotada (
    id_modulo     INT NOT NULL,
    id_tipo_pieza INT NOT NULL,
    CONSTRAINT PK_Modulo_Veta_Rotada PRIMARY KEY (id_modulo, id_tipo_pieza),
    CONSTRAINT FK_Modulo_Veta_Rotada_Modulo     FOREIGN KEY (id_modulo)     REFERENCES dbo.Modulo (id_modulo) ON DELETE CASCADE,
    CONSTRAINT FK_Modulo_Veta_Rotada_Tipo_Pieza FOREIGN KEY (id_tipo_pieza) REFERENCES dbo.Tipo_Pieza (id_tipo_pieza)
);
GO

-- Verificación: debe devolver 1
SELECT COUNT(*) AS tabla_ok FROM sys.tables WHERE name = N'Modulo_Veta_Rotada';
GO
