"""Identidad visual del sistema: colores, tipografías y modo claro/oscuro.

Todas las pantallas toman sus colores de acá (nunca escriben un color suelto),
así un cambio de estilo se hace en un solo lugar. Los colores salen del
diseño aprobado y de la web de la carpintería; los pares texto/fondo cumplen
el contraste mínimo de accesibilidad (WCAG AA, 4,5:1).
"""
from dataclasses import dataclass
from pathlib import Path

import flet as ft

CARPETA_RECURSOS = Path(__file__).parent / "assets"

# Familias tipográficas (archivos estáticos en assets/fonts, licencia OFL).
SERIF = "CormorantMedium"
SERIF_SEMI = "CormorantSemiBold"
SERIF_ITALICA = "CormorantItalic"
SANS = "Inter"
SANS_MEDIA = "InterMedium"
SANS_SEMI = "InterSemiBold"

FUENTES = {
    SERIF: "fonts/CormorantGaramond-Medium.ttf",
    SERIF_SEMI: "fonts/CormorantGaramond-SemiBold.ttf",
    SERIF_ITALICA: "fonts/CormorantGaramond-MediumItalic.ttf",
    SANS: "fonts/Inter-Regular.ttf",
    SANS_MEDIA: "fonts/Inter-Medium.ttf",
    SANS_SEMI: "fonts/Inter-SemiBold.ttf",
}


@dataclass(frozen=True)
class Paleta:
    oscura: bool
    fondo: str
    panel: str            # menú lateral y encabezados
    superficie: str       # tarjetas y campos
    superficie_alta: str  # elementos seleccionados
    borde: str
    borde_fuerte: str
    texto: str
    texto_secundario: str
    texto_tenue: str
    acento: str           # dorado: botones principales y detalles
    acento_texto: str     # dorado legible como texto sobre el fondo
    sobre_acento: str     # texto encima de un botón dorado
    error_fondo: str
    error_borde: str
    error_texto: str
    exito: str


OSCURA = Paleta(
    oscura=True,
    fondo="#12100D", panel="#181511", superficie="#1B1814", superficie_alta="#2A241B",
    borde="#2E2A24", borde_fuerte="#4A4339",
    texto="#F2EDE4", texto_secundario="#CFC7BA", texto_tenue="#A39B8E",
    acento="#C9A04A", acento_texto="#C9A04A", sobre_acento="#1A1508",
    error_fondo="#2E1A16", error_borde="#6B3329", error_texto="#F3C2B6",
    exito="#8FD3B0",
)

CLARA = Paleta(
    oscura=False,
    fondo="#F6F2EA", panel="#EFE8DC", superficie="#FFFFFF", superficie_alta="#E5D7BB",
    borde="#E2D9C8", borde_fuerte="#CDBFA8",
    texto="#1C1914", texto_secundario="#4A443B", texto_tenue="#6B6256",
    acento="#C9A04A", acento_texto="#8A6420", sobre_acento="#1A1508",
    error_fondo="#FBE9E5", error_borde="#E3A99C", error_texto="#8C2F1F",
    exito="#2E8A5E",
)


def tema_flet(p: Paleta) -> ft.Theme:
    """Tema de Material para los controles que no estilamos a mano."""
    return ft.Theme(
        font_family=SANS,
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=p.acento, on_primary=p.sobre_acento,
            secondary=p.acento_texto, on_secondary=p.sobre_acento,
            surface=p.superficie, on_surface=p.texto, on_surface_variant=p.texto_secundario,
            outline=p.borde_fuerte, outline_variant=p.borde,
            error=p.error_texto, on_error=p.error_fondo,
        ),
        scaffold_bgcolor=p.fondo,
    )


# ---------- piezas reutilizables ----------
RADIO = 10


def titulo(texto: str, p: Paleta, tamano: int = 44) -> ft.Text:
    return ft.Text(texto, font_family=SERIF, size=tamano, color=p.texto)


def etiqueta_superior(texto: str, p: Paleta) -> ft.Text:
    """Texto chico en mayúsculas espaciadas, en dorado (como en la web)."""
    return ft.Text(texto.upper(), font_family=SANS_MEDIA, size=12, color=p.acento_texto,
                   style=ft.TextStyle(letter_spacing=2.6))


def campo(etiqueta: str, p: Paleta, **opciones) -> ft.TextField:
    return ft.TextField(
        label=etiqueta,
        label_style=ft.TextStyle(color=p.texto_secundario, font_family=SANS_MEDIA),
        text_style=ft.TextStyle(color=p.texto, size=16),
        bgcolor=p.superficie, filled=True, fill_color=p.superficie,
        border_color=p.borde_fuerte, focused_border_color=p.acento, focused_border_width=2,
        border_radius=RADIO, cursor_color=p.acento,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=16),
        **opciones,
    )


def boton_principal(texto: str, p: Paleta, al_tocar, **opciones) -> ft.FilledButton:
    return ft.FilledButton(
        content=ft.Text(texto, font_family=SANS_SEMI, size=16, color=p.sobre_acento),
        on_click=al_tocar, height=52,
        style=ft.ButtonStyle(bgcolor=p.acento, shape=ft.RoundedRectangleBorder(radius=RADIO)),
        **opciones,
    )


def boton_secundario(texto: str, p: Paleta, al_tocar, **opciones) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=ft.Text(texto, font_family=SANS_MEDIA, size=15, color=p.texto),
        on_click=al_tocar, height=48,
        style=ft.ButtonStyle(side=ft.BorderSide(1, p.borde_fuerte),
                             shape=ft.RoundedRectangleBorder(radius=RADIO)),
        **opciones,
    )


def boton_modo(p: Paleta, al_tocar) -> ft.IconButton:
    """Botón sol/luna para alternar entre modo claro y oscuro."""
    return ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_OUTLINED if p.oscura else ft.Icons.DARK_MODE_OUTLINED,
        icon_color=p.texto_secundario,
        tooltip="Cambiar a modo claro" if p.oscura else "Cambiar a modo oscuro",
        on_click=al_tocar,
        style=ft.ButtonStyle(side=ft.BorderSide(1, p.borde), shape=ft.RoundedRectangleBorder(radius=RADIO)),
        width=44, height=44,
    )


def aviso(texto: str, p: Paleta, tipo: str = "error") -> ft.Container:
    """Recuadro de mensaje. tipo: 'error' o 'info'."""
    es_error = tipo == "error"
    return ft.Container(
        content=ft.Row(
            [ft.Icon(ft.Icons.ERROR_OUTLINE if es_error else ft.Icons.VERIFIED_USER_OUTLINED,
                     color=p.error_texto if es_error else p.acento_texto, size=20),
             ft.Text(texto, color=p.error_texto if es_error else p.texto_secundario, size=14,
                     expand=True)],
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=p.error_fondo if es_error else p.superficie,
        border=ft.Border.all(1, p.error_borde if es_error else p.borde),
        border_radius=RADIO, padding=ft.Padding.symmetric(horizontal=14, vertical=12),
    )
