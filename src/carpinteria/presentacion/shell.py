"""Estructura común de las pantallas con sesión iniciada: menú lateral + barra
superior + contenido (diseño 2 · Inicio)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS, SANS_MEDIA, SERIF

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

# (clave, texto, icono, disponible)
SECCIONES_PRINCIPALES = [
    ("inicio", "Inicio", ft.Icons.HOME_OUTLINED, True),
    ("trabajos", "Trabajos", ft.Icons.TABLE_CHART_OUTLINED, True),
    ("clientes", "Clientes", ft.Icons.PEOPLE_OUTLINE, True),
    ("materiales", "Materiales", ft.Icons.LAYERS_OUTLINED, False),
    ("retazos", "Retazos", ft.Icons.VIEW_QUILT_OUTLINED, False),
]
SECCIONES_CONFIGURACION = [
    ("auditoria", "Auditoría", ft.Icons.SHIELD_OUTLINED, True),
    ("usuarios", "Usuarios", ft.Icons.MANAGE_ACCOUNTS_OUTLINED, True),
    ("contrasena", "Mi contraseña", ft.Icons.KEY_OUTLINED, True),
]


def _item_menu(app: Aplicacion, clave: str, texto: str, icono, disponible: bool,
               activa: bool) -> ft.Container:
    p = app.paleta
    if not disponible:
        color = p.texto_tenue
    elif activa:
        color = p.texto
    else:
        color = p.texto_secundario
    fila = [
        ft.Icon(icono, size=20, color=p.acento_texto if activa else color),
        ft.Text(texto, size=15, color=color, font_family=SANS_MEDIA if activa else SANS, expand=True),
    ]
    if not disponible:
        fila.append(ft.Text("Pronto", size=11, color=p.texto_tenue))
    return ft.Container(
        content=ft.Row(fila, spacing=12),
        height=44, padding=ft.Padding.symmetric(horizontal=12), border_radius=10,
        bgcolor=p.superficie_alta if activa else None,
        on_click=(lambda _: app.ir_a(clave)) if disponible else None,
        ink=disponible,
        tooltip=None if disponible else "Disponible en una próxima versión",
    )


def construir(app: Aplicacion, seccion: str, contenido: ft.Control) -> ft.Control:
    p = app.paleta
    usuario = app.sesion.usuario

    menu = ft.Container(
        width=248, bgcolor=p.panel, border=ft.Border.only(right=ft.BorderSide(1, p.borde)),
        padding=ft.Padding.only(left=16, right=16, top=28, bottom=20),
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.only(left=12, bottom=24),
                    content=ft.Column([
                        ft.Text("ZANINO", font_family=SERIF, size=28, color=p.texto,
                                style=ft.TextStyle(letter_spacing=5)),
                        tema.etiqueta_superior("Gestión del taller", p),
                    ], spacing=0),
                ),
                *[_item_menu(app, c, t, i, d, c == seccion) for c, t, i, d in SECCIONES_PRINCIPALES],
                ft.Container(expand=True),
                ft.Container(padding=ft.Padding.only(left=12, bottom=6),
                             content=ft.Text("CONFIGURACIÓN", size=11, color=p.texto_tenue,
                                             style=ft.TextStyle(letter_spacing=2))),
                *[_item_menu(app, c, t, i, d, c == seccion) for c, t, i, d in SECCIONES_CONFIGURACION],
            ],
            spacing=4,
        ),
    )

    barra = ft.Row(
        [
            ft.Container(expand=True),
            tema.boton_modo(p, lambda _: app.alternar_modo()),
            ft.Container(
                border=ft.Border.all(1, p.borde), border_radius=10,
                padding=ft.Padding.only(left=6, right=14, top=4, bottom=4),
                content=ft.Row([componentes.avatar(usuario.nombre_completo, p, 32),
                                ft.Text(usuario.nombre_completo.split()[0], color=p.texto, size=15)],
                               spacing=10),
            ),
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=18, color=p.texto_secundario),
                                ft.Text("Cerrar sesión", color=p.texto_secundario, size=14)], spacing=6),
                on_click=lambda _: app.cerrar_sesion(), height=44,
            ),
        ],
        spacing=12,
    )

    principal = ft.Container(
        expand=True,
        padding=ft.Padding.only(left=48, right=48, top=20, bottom=32),
        content=ft.Column([barra, contenido], spacing=24, expand=True, scroll=ft.ScrollMode.AUTO),
    )
    return ft.Row([menu, principal], spacing=0, expand=True,
                  vertical_alignment=ft.CrossAxisAlignment.STRETCH)
