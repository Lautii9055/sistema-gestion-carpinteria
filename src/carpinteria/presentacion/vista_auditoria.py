"""Consulta de la auditoría (RF-03.6): quién hizo qué y cuándo. Solo lectura."""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.auditoria import PERIODOS
from carpinteria.negocio.entidades import EventoAuditoria
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

TODOS = "todos"


_desplegable = componentes.desplegable


def _fila(evento: EventoAuditoria, p) -> ft.Container:
    if evento.usuario:
        quien = evento.usuario
    elif evento.usuario_ingresado:
        quien = f"«{evento.usuario_ingresado}» (usuario inexistente)"
    else:
        quien = "—"
    detalle = "  ·  ".join(x for x in (quien, evento.detalle, evento.equipo) if x)
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border.only(bottom=ft.BorderSide(1, p.borde)),
        bgcolor=p.error_fondo if evento.es_critico else None,
        content=ft.Row(
            [
                ft.Text(f"{evento.fecha_hora:%d/%m/%Y  %H:%M:%S}", size=13, color=p.texto_tenue, width=170),
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED if evento.es_critico else ft.Icons.CIRCLE,
                        size=18 if evento.es_critico else 8,
                        color=p.error_texto if evento.es_critico else p.texto_tenue),
                ft.Column([
                    ft.Text(evento.descripcion, size=14,
                            font_family=SANS_SEMI if evento.es_critico else SANS_MEDIA,
                            color=p.error_texto if evento.es_critico else p.texto),
                    ft.Text(detalle, size=13, color=p.texto_secundario),
                ], spacing=2, expand=True),
            ],
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def construir(app: Aplicacion) -> ft.Control:
    p = app.paleta
    usuarios, _ = app.ejecutar(app.usuarios.listar)
    tipos, _ = app.ejecutar(app.auditoria.tipos_de_evento)

    periodo = _desplegable("Período", [(k, k) for k in PERIODOS], "Últimos 7 días", p, 200)
    usuario = _desplegable("Usuario", [(TODOS, "Todos")] + [(str(u.id), u.nombre_completo)
                                                         for u in usuarios or []], TODOS, p, 220)
    tipo = _desplegable("Evento", [(TODOS, "Todos")] + [(t.codigo, t.descripcion) for t in tipos or []],
                        TODOS, p, 300)
    solo_criticos = ft.Checkbox(label="Solo críticos", value=False, active_color=p.acento,
                                check_color=p.sobre_acento,
                                label_style=ft.TextStyle(color=p.texto_secundario, size=14))
    resumen = ft.Text("", size=14, color=p.texto_tenue)
    lista = ft.Column(spacing=0)

    def cargar(_=None) -> None:
        eventos, error = app.ejecutar(
            app.auditoria.consultar, periodo.value,
            None if usuario.value == TODOS else int(usuario.value),
            None if tipo.value == TODOS else tipo.value,
            bool(solo_criticos.value),
        )
        if error:
            lista.controls = [tema.aviso(error, p)]
            resumen.value = ""
        else:
            criticos = sum(1 for e in eventos if e.es_critico)
            resumen.value = (f"{len(eventos)} eventos" + (f", {criticos} críticos" if criticos else "")
                             + (" (se muestran los 500 más recientes)" if len(eventos) == 500 else ""))
            lista.controls = ([_fila(e, p) for e in eventos] if eventos else [
                ft.Container(padding=ft.Padding.all(24),
                             content=ft.Text("No hay eventos con esos filtros.", color=p.texto_tenue))])
        app.page.update()

    for control in (periodo, usuario, tipo):
        control.on_select = cargar
    solo_criticos.on_change = cargar

    contenido = ft.Column([
        componentes.encabezado_seccion(
            "Configuración", "Auditoría",
            "Registro de ingresos, cambios de contraseña, usuarios y otras acciones "
            "importantes. No se puede modificar ni borrar.", p),
        ft.Row([periodo, usuario, tipo, solo_criticos], spacing=12, wrap=True,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
        resumen,
        ft.Container(content=lista, bgcolor=p.superficie, border=ft.Border.all(1, p.borde),
                     border_radius=14, clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
    ], spacing=16)
    app.al_mostrar(cargar)  # carga los datos una vez que la pantalla está visible
    return contenido
