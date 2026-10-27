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
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.componentes import fecha_larga
from carpinteria.presentacion.tema import SANS_MEDIA, SERIF

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def saludo(ahora: datetime) -> str:
    if ahora.hour < 12:
        return "Buen día"
    if ahora.hour < 20:
        return "Buenas tardes"
    return "Buenas noches"


def texto_ultimo_ingreso(sesion: Sesion) -> str:
    anterior = sesion.ultimo_ingreso_anterior
    if anterior is None:
        return "Es tu primer ingreso al sistema."
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

    fila_aviso = [
        ft.Icon(ft.Icons.GPP_MAYBE_OUTLINED if hubo_fallidos else ft.Icons.VERIFIED_USER_OUTLINED,
                color=p.error_texto if hubo_fallidos else p.acento_texto, size=20),
        ft.Text(texto_ultimo_ingreso(sesion), size=14, expand=True,
                color=p.error_texto if hubo_fallidos else p.texto_secundario),
    ]
    if hubo_fallidos:
        fila_aviso.append(ft.TextButton(
            content=ft.Text("Ver en la auditoría", color=p.error_texto, size=14),
            on_click=lambda _: app.ir_a("auditoria")))

    aviso_ingreso = ft.Container(
        content=ft.Row(fila_aviso, spacing=10),
        bgcolor=p.error_fondo if hubo_fallidos else p.superficie,
        border=ft.Border.all(1, p.error_borde if hubo_fallidos else p.borde),
        border_radius=12, padding=ft.Padding.symmetric(horizontal=16, vertical=12),
    )

    proximamente = componentes.tarjeta(ft.Column([
        ft.Text("Próximamente", font_family=SANS_MEDIA, size=13, color=p.texto_tenue),
        ft.Text("Trabajos, clientes, materiales, despiece y retazos.",
                font_family=SERIF, size=26, color=p.texto),
    ], spacing=4), p)

    return ft.Column(
        [
            aviso_ingreso,
            ft.Column([
                tema.etiqueta_superior(fecha_larga(ahora), p),
                tema.titulo(f"{saludo(ahora)}, {nombre}.", p, 48),
            ], spacing=4),
            proximamente,
        ],
        spacing=28,
    )
