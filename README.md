# Sistema de Gestión para Carpintería

Aplicación de escritorio para una carpintería que fabrica muebles a medida en melamina y MDF. Reemplaza el cálculo manual de piezas con papel y calculadora por un **despiece automático**, y suma la gestión de clientes, trabajos, pagos e inventario de retazos.

> **Estado:** en desarrollo. Análisis, diseño y base de datos terminados; en curso la implementación en Python.

---

## El problema
En el taller, las medidas de cada pieza se calculan a mano a partir de las medidas exteriores de cada módulo, descontando espesores, luces y filos. Es la tarea más repetitiva y la que más errores costosos genera. Además, no había registro de clientes, trabajos, pagos ni retazos.

## Funcionalidades (versión 1)
- **Despiece automático:** a partir de las medidas de un módulo calcula todas sus piezas (medidas finales y de corte, material, color, sentido de la veta y filos), incluidos cajones según el tipo de guía, frentes según el estilo y zócalos.
- **Listado de corte en PDF** para la maderera.
- **Clientes y obras**, con historial de trabajos por obra.
- **Trabajos:** estados, fechas, seña y saldo.
- **Catálogo de materiales:** placas, colores, listones, lacas y filos.
- **Inventario de retazos.**
- **Seguridad:** inicio de sesión con bloqueo por intentos fallidos, cierre por inactividad y registro de auditoría.

## Tecnologías
| Capa | Tecnología |
|------|------------|
| Interfaz gráfica | Python + [Flet](https://flet.dev) |
| Lógica de negocio | Python |
| Acceso a datos | pyodbc (ODBC Driver 18) |
| Listados PDF | fpdf2 |
| Base de datos | SQL Server Express |
| Pruebas | pytest |

## Arquitectura
Arquitectura en **tres capas**, con principios **SOLID** y patrones **GRASP**:

```
presentacion/  →  negocio/  →  datos/  →  SQL Server
 (pantallas)      (servicios y       (repositorios con
                   motor de despiece)  consultas parametrizadas)
```

Cada capa solo conoce a la inmediata inferior. El motor de despiece se arma con componentes que tienen su propia regla de cálculo, así que agregar un tipo de pieza nuevo no requiere modificar los existentes (principio abierto/cerrado).

## Base de datos
- Modelo relacional en **3FN**, con **30 tablas** ([modelo de datos](docs/modelo_datos.md), [DER](docs/DER_carpinteria.png)).
- Restricciones con nombre (PK, FK, CHECK, UNIQUE), índices filtrados y procedimientos almacenados transaccionales.
- Scripts de creación en [`database/`](database/).

## Seguridad
Diseñada a partir de una evaluación de riesgos proporcional al uso real (ver la [sección 6.1 de los requerimientos](docs/requerimientos.md)):
- Contraseñas con **hash bcrypt**; bloqueo tras intentos fallidos; cierre de sesión por inactividad.
- **Mínimo privilegio:** la aplicación se conecta con un usuario de base de datos que no puede modificar la estructura ni borrar la auditoría.
- **Registro de auditoría** de los eventos relevantes, que solo admite agregar filas.
- **Consultas parametrizadas** contra la inyección SQL; en las búsquedas, además, se neutralizan los comodines de `LIKE` y se limita la cantidad y el largo de las palabras buscadas.
- **Validación de datos de entrada** en la capa de negocio (formatos, largos máximos, duplicados), independiente de la pantalla.
- **Secretos fuera del código:** credenciales guardadas en el Administrador de credenciales de Windows.
- **Copias de seguridad cifradas** (AES) y verificadas con hash SHA-256.
- [Plan de respuesta a incidentes](docs/plan_respuesta_incidentes.md) basado en NIST SP 800-61.

## Estructura del repositorio
```
├── database/        Scripts SQL de creación de la base (ejecutar en orden 00 → 05)
├── docs/            Requerimientos, modelo de datos, DER y plan de incidentes
├── src/carpinteria/
│   ├── presentacion/   Interfaz gráfica (Flet)
│   ├── negocio/        Servicios y motor de despiece
│   └── datos/          Repositorios y conexión a la base
└── tests/           Pruebas automatizadas
```

## Cómo ejecutarlo (Windows)
Requisitos: SQL Server Express con la base creada (ver [`database/README.md`](database/README.md)), ODBC Driver 18 y Python 3.12 o superior.

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python scripts/configurar_credenciales.py   # una sola vez: guarda la contraseña de la base en Windows
python -m carpinteria                       # inicia el sistema
```

Pruebas: `pytest`. Revisión de vulnerabilidades en dependencias: `pip-audit`.

## Documentación
- [Requerimientos](docs/requerimientos.md)
- [Modelo de datos](docs/modelo_datos.md)
- [Diagrama entidad-relación](docs/DER_carpinteria.png)
- [Instalación de la base de datos](database/README.md)
- [Plan de respuesta a incidentes](docs/plan_respuesta_incidentes.md)

## Créditos
Tipografías Cormorant Garamond e Inter, bajo licencia SIL Open Font License 1.1 (ver `src/carpinteria/presentacion/assets/fonts`).

## Autor
**Lautaro Zanino** — Técnico Universitario en Programación (UTN) · Estudiante de la Licenciatura en Gestión de TI (UADE)
