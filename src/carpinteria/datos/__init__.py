"""Capa de acceso a datos: conexión a SQL Server y repositorios.

Toda consulta es parametrizada (marcadores ? de pyodbc); nunca se arma SQL
concatenando datos ingresados por el usuario.
"""
