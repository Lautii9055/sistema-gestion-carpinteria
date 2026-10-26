/* =============================================================================
   Sistema de Gestión para Carpintería
   00 - Creación de la base de datos
   Motor: SQL Server 2025 Express
   -----------------------------------------------------------------------------
   Collation Modern_Spanish_CI_AI:
     CI = Case Insensitive   -> "perez" encuentra "Pérez" / "PEREZ"
     AI = Accent Insensitive -> "Perez" encuentra "Pérez"
   Así las búsquedas por texto (RF-06) ignoran mayúsculas y tildes sin
   necesidad de funciones extra en cada consulta.
   ============================================================================= */

USE master;
GO

IF DB_ID(N'Carpinteria') IS NULL
BEGIN
    CREATE DATABASE Carpinteria COLLATE Modern_Spanish_CI_AI;
END
GO

USE Carpinteria;
GO
