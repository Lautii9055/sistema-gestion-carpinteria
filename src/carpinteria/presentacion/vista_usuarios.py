"""Gestión de usuarios (RF-02 y RF-03.4)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Usuario
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.componentes import fecha_larga
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def _dialogo(app: Aplicacion, titulo: str, contenido: ft.Control, acciones: list[ft.Control]) -> ft.AlertDialog:
    return componentes.dialogo(app.paleta, titulo, contenido, acciones)


def _mostrar_provisoria(app: Aplicacion, nombre: str, provisoria: str, motivo: str) -> None:
    """La contraseña provisoria se muestra una sola vez: no queda guardada en ningún lado."""
    p = app.paleta
    contenido = ft.Column(
        [
            ft.Text(motivo, size=15, color=p.texto_secundario),
            ft.Container(
                bgcolor=p.fondo, border=ft.Border.all(1, p.borde_fuerte), border_radius=12,
                padding=ft.Padding.symmetric(vertical=18), alignment=ft.Alignment.CENTER,
                content=ft.Text(provisoria, selectable=True, font_family=SANS_SEMI, size=30,
                                color=p.acento_texto, style=ft.TextStyle(letter_spacing=3)),
            ),
            tema.aviso("Anotala y entregásela en persona. No se vuelve a mostrar: si se pierde, "
                       "se blanquea de nuevo. Al ingresar, el sistema le va a pedir que la cambie.",
                       p, tipo="info"),
        ],
        spacing=16, tight=True,
    )
    dialogo = _dialogo(app, f"Contraseña de {nombre}", contenido, [])
    dialogo.actions = [tema.boton_principal("Listo, ya la anoté", p, lambda _: app.cerrar_dialogo())]
    app.mostrar_dialogo(dialogo)


def _abrir_alta(app: Aplicacion) -> None:
    p = app.paleta
    nombre_completo = tema.campo("Nombre y apellido", p, autofocus=True)
    nombre_usuario = tema.campo("Usuario para ingresar", p,
                                hint_text="por ejemplo: lautaro",
                                helper="Minúsculas, sin espacios ni tildes.")
    caja_error = ft.Container(visible=False)

    def crear(_=None) -> None:
        provisoria, error = app.ejecutar(app.usuarios.crear, app.sesion,
                                         nombre_usuario.value or "", nombre_completo.value or "")
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()
            return
        app.cerrar_dialogo()
        app.ir_a("usuarios")
        _mostrar_provisoria(app, (nombre_completo.value or "").split()[0], provisoria,
                            "Usuario creado. Esta es su contraseña provisoria:")

    nombre_completo.on_submit = lambda _: nombre_usuario.focus()
    nombre_usuario.on_submit = crear
    app.mostrar_dialogo(_dialogo(
        app, "Nuevo usuario",
        ft.Column([caja_error, nombre_completo, nombre_usuario], spacing=16, tight=True),
        [ft.TextButton(content=ft.Text("Cancelar", color=p.texto_secundario),
                       on_click=lambda _: app.cerrar_dialogo()),
         tema.boton_principal("Crear usuario", p, crear)],
    ))


def _confirmar(app: Aplicacion, titulo: str, texto: str, boton: str, accion) -> None:
    p = app.paleta
    app.mostrar_dialogo(_dialogo(
        app, titulo, ft.Text(texto, size=15, color=p.texto_secundario),
        [ft.TextButton(content=ft.Text("Cancelar", color=p.texto_secundario),
                       on_click=lambda _: app.cerrar_dialogo()),
         tema.boton_principal(boton, p, lambda _: (app.cerrar_dialogo(), accion()))],
    ))


def _blanquear(app: Aplicacion, usuario: Usuario) -> None:
    nombre = usuario.nombre_completo.split()[0]

    def accion() -> None:
        provisoria, error = app.ejecutar(app.usuarios.blanquear_contrasena, app.sesion, usuario.id)
        if error:
            componentes.aviso_flotante(app.page, error, app.paleta)
            return
        app.ir_a("usuarios")
        _mostrar_provisoria(app, nombre, provisoria, "Esta es su nueva contraseña provisoria:")

    _confirmar(app, "Blanquear contraseña",
               f"Se va a generar una contraseña provisoria para {usuario.nombre_completo}. "
               "La actual deja de funcionar y, si estaba bloqueado, se desbloquea.",
               "Blanquear", accion)


def _cambiar_estado(app: Aplicacion, usuario: Usuario) -> None:
    def accion() -> None:
        funcion = app.usuarios.dar_de_baja if usuario.es_activo else app.usuarios.reactivar
        _, error = app.ejecutar(funcion, app.sesion, usuario.id)
        if error:
            componentes.aviso_flotante(app.page, error, app.paleta)
            return
        app.ir_a("usuarios")
        componentes.aviso_flotante(
            app.page, f"{usuario.nombre_completo} quedó {'dado de baja' if usuario.es_activo else 'activo'}.",
            app.paleta)

    if usuario.es_activo:
        _confirmar(app, "Dar de baja",
                   f"{usuario.nombre_completo} no va a poder ingresar. Su historial y la auditoría "
                   "se conservan, y se puede reactivar cuando quieras.", "Dar de baja", accion)
    else:
        accion()


def _fila_usuario(app: Aplicacion, usuario: Usuario) -> ft.Container:
    p = app.paleta
    es_yo = usuario.id == app.sesion.usuario.id

    etiquetas = [componentes.etiqueta_estado("Activo", p.exito, p.superficie_alta) if usuario.es_activo
                 else componentes.etiqueta_estado("Dado de baja", p.texto_tenue, p.fondo)]
    if usuario.debe_cambiar_contrasena and usuario.es_activo:
        etiquetas.append(componentes.etiqueta_estado("Contraseña provisoria", p.acento_texto, p.superficie_alta))
    if es_yo:
        etiquetas.append(componentes.etiqueta_estado("Vos", p.texto_secundario, p.fondo))

    ultimo = (f"Último ingreso: {fecha_larga(usuario.ultimo_ingreso)}, {usuario.ultimo_ingreso:%H:%M}"
              if usuario.ultimo_ingreso else "Todavía no ingresó")

    acciones: list[ft.Control] = []
    if not es_yo:
        if usuario.es_activo:
            acciones.append(tema.boton_secundario("Blanquear contraseña", p,
                                                  lambda _: _blanquear(app, usuario)))
        acciones.append(ft.TextButton(
            content=ft.Text("Dar de baja" if usuario.es_activo else "Reactivar",
                            color=p.error_texto if usuario.es_activo else p.acento_texto, size=14),
            on_click=lambda _: _cambiar_estado(app, usuario), height=44))

    return componentes.tarjeta(
        ft.Row(
            [
                componentes.avatar(usuario.nombre_completo, p, 44),
                ft.Column([
                    ft.Row([ft.Text(usuario.nombre_completo, font_family=SANS_MEDIA, size=16,
                                    color=p.texto if usuario.es_activo else p.texto_tenue),
                            *etiquetas], spacing=10, wrap=True),
                    ft.Text(f"@{usuario.nombre_usuario}  ·  {ultimo}", size=13, color=p.texto_tenue),
                ], spacing=4, expand=True),
                *acciones,
            ],
            spacing=16, wrap=False,
        ),
        p, padding=18,
    )


def construir(app: Aplicacion) -> ft.Control:
    p = app.paleta
    usuarios, error = app.ejecutar(app.usuarios.listar)
    boton_nuevo = ft.FilledButton(
        content=ft.Row([ft.Icon(ft.Icons.PERSON_ADD_ALT_1_OUTLINED, color=p.sobre_acento, size=20),
                        ft.Text("Nuevo usuario", font_family=SANS_SEMI, size=15, color=p.sobre_acento)],
                       spacing=8, tight=True),
        on_click=lambda _: _abrir_alta(app), height=48,
        style=ft.ButtonStyle(bgcolor=p.acento, shape=ft.RoundedRectangleBorder(radius=tema.RADIO)),
    )
    filas: list[ft.Control] = ([tema.aviso(error, p)] if error
                               else [_fila_usuario(app, u) for u in usuarios])
    return ft.Column([
        componentes.encabezado_seccion(
            "Configuración", "Usuarios",
            "Quiénes pueden ingresar al sistema. Cada persona usa su propio usuario, así la "
            "auditoría muestra quién hizo cada cosa.", p, boton_nuevo),
        *filas,
    ], spacing=16)
