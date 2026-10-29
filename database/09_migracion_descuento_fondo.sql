/* =============================================================================
   Sistema de Gestión para Carpintería
   09 - Migración: parámetro descuento_fondo (requerimientos v3.0)
   -----------------------------------------------------------------------------
   El fondo del módulo mide 0,3 cm menos que el módulo en ancho y en alto
   (ej.: módulo de 30 x 30 -> fondo de 29,7 x 29,7). El valor queda como
   parámetro para poder ajustarlo sin tocar el código.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Parametro WHERE clave_par = 'descuento_fondo')
    INSERT INTO dbo.Parametro (clave_par, valor_par, unidad_par, descripcion_par)
    VALUES ('descuento_fondo', 0.3, N'cm', N'El fondo mide esto menos que el módulo, en ancho y en alto');
GO

-- Verificación: debe devolver una fila con 0.3
SELECT clave_par, valor_par, unidad_par FROM dbo.Parametro WHERE clave_par = 'descuento_fondo';
GO
