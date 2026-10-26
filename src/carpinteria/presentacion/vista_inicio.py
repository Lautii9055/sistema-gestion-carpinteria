"""Inicio (versión provisoria).

Por ahora muestra el saludo y el aviso de último ingreso (RF-03.7). Las tarjetas
de resumen y la tabla de trabajos del diseño aprobado se suman cuando estén los
módulos de trabajos y clientes.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Sesion
from carpinteria.presentacion import tema
from carpinteria.presentacion.tema import SERIF, SANS_MEDIA

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def saludo(ahora: datetime) -> str:
    if ahora.hour < 12:
        return "Buen día"
    if ahora.hour < 20:
        return "Buenas tardes"
    return "Buenas noches"


def fecha_larga(fecha: datetime) -> str:
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def texto_ultimo_ingreso(sesion: Sesion) -> str:
    anterior = sesion.ultimo_ingreso_anterior
    if anterior is None:
        return "Es tu primer ingreso al sistema."
    else:
        texto = f"Tu último ingreso fue el {fecha_larga(anterior)} a las {anterior:%H:%M}."
    fallidos = sesion.intentos_fallidos_desde_entonces
    if fallidos == 0:
        return texto + " Sin intentos fallidos desde entonces."
    plural = "intento fallido" if fallidos == 1 else "intentos fallidos"
    return texto + f" Hubo {fallidos} {plural} de ingreso con tu usuario desde entonces."


def construir(app: Aplicacion, sesion: Sesion) -> ft.Control:
    p = app.paleta
    ahora = datetime.now()
    nombre = sesion.usuario.nombre_completo.split()[0]
    hubo_fallidos = sesion.intentos_fallidos_desde_entonces > 0

    aviso_ingreso = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.GPP_MAYBE_OUTLINED if hubo_fallidos else ft.Icons.VERIFIED_USER_OUTLINED,
                        color=p.error_texto if hubo_fallidos else p.acento_texto, size=20),
                ft.Text(texto_ultimo_ingreso(sesion), size=14, expand=True,
                        color=p.error_texto if hubo_fallidos else p.texto_secundario),
            ],
            spacing=10,
        ),
        bgcolor=p.error_fondo if hubo_fallidos else p.superficie,
        border=ft.Border.all(1, p.error_borde if hubo_fallidos else p.borde),
        border_radius=12, padding=ft.Padding.symmetric(horizontal=16, vertical=12),
    )

    encabezado = ft.Row(
        [
            ft.Column([
                ft.Text("ZANINO", font_family=SERIF, size=26, color=p.texto,
                        style=ft.TextStyle(letter_spacing=4)),
                tema.etiqueta_superior("Gestión del taller", p),
            ], spacing=0),
            ft.Container(expand=True),
            tema.boton_modo(p, lambda _: app.alternar_modo()),
            tema.boton_secundario("Cerrar sesión", p, lambda _: app.cerrar_sesion()),
        ],
        spacing=12,
    )

    proximamente = ft.Container(
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=14,
        padding=ft.Padding.all(24),
        content=ft.Column([
            ft.Text("Próximamente", font_family=SANS_MEDIA, size=13, color=p.texto_tenue),
            ft.Text("Trabajos, clientes, materiales, despiece y retazos.",
                    font_family=SERIF, size=26, color=p.texto),
        ], spacing=4),
    )

    return ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(horizontal=48, vertical=28),
        content=ft.Column(
            [
                encabezado,
                aviso_ingreso,
                ft.Column([
                    tema.etiqueta_superior(fecha_larga(ahora), p),
                    tema.titulo(f"{saludo(ahora)}, {nombre}.", p, 48),
                ], spacing=4),
                proximamente,
            ],
            spacing=28, scroll=ft.ScrollMode.AUTO,
        ),
    )
