"""Detalle del trabajo (diseño 3): estado, pagos y fechas (RF-25 a RF-27)."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import DetalleTrabajo, EstadoTrabajo
from carpinteria.negocio.trabajos import (CAMPOS_DE_FECHA, CANCELADO, COBRADO, FECHA_PRESUPUESTO,
                                          ESTADOS_QUE_SE_PUEDEN_ELIMINAR, NOMBRE_DE_FECHA, PRESUPUESTADO,
                                          formato_fecha, formato_pesos, leer_fecha, leer_monto)
from carpinteria.presentacion import componentes, tema, vista_trabajos
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI, SERIF

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def _recargar(app: Aplicacion, id_trabajo: int, mensaje: str | None = None) -> None:
    app.ir_a("trabajo", id_trabajo=id_trabajo)
    if mensaje:
        componentes.aviso_flotante(app.page, mensaje, app.paleta)


def _dialogo_con_error(app: Aplicacion, titulo: str, controles: list[ft.Control], boton: str,
                       accion, ancho: int = 480) -> None:
    """Diálogo genérico: accion() devuelve un mensaje de error o None si salió bien."""
    p = app.paleta
    caja_error = ft.Container(visible=False)

    def confirmar(_=None) -> None:
        error = accion()
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()

    app.mostrar_dialogo(componentes.dialogo(
        p, titulo, ft.Column([caja_error, *controles], spacing=14, tight=True, scroll=ft.ScrollMode.AUTO),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()),
         tema.boton_principal(boton, p, confirmar)], ancho=ancho))


# ---------- acciones ----------
def _pasar_a(app: Aplicacion, d: DetalleTrabajo, estado: EstadoTrabajo) -> None:
    """Avanzar, volver un paso, cancelar o retomar. Al avanzar se sugiere la fecha (RF-26.3)."""
    p = app.paleta
    t = d.trabajo
    avanza = estado == app.trabajos.estado_siguiente(d.estado)
    vuelve = estado == app.trabajos.estado_anterior(d.estado)
    retoma = d.estado.nombre == CANCELADO
    campo = app.trabajos.fecha_sugerida(estado) if avanza else None
    if campo == "fecha_cobro_sena" and not t.monto_sena:
        campo = None  # sin seña cargada no hay cobro de seña que registrar
    campo_fecha = None
    if campo:
        actual = getattr(t, campo)
        campo_fecha = componentes.campo_fecha(NOMBRE_DE_FECHA[campo], formato_fecha(actual or date.today()),
                                              p, autofocus=True)
        explicacion = (f"Ya figura cobrado el {actual:%d/%m/%Y}. Confirmá o corregí la fecha."
                       if campo == "fecha_cobro_saldo" and actual
                       else f"Se registra la fecha de {NOMBRE_DE_FECHA[campo].lower()}. Podés corregirla.")
        controles: list[ft.Control] = [ft.Text(explicacion, size=15, color=p.texto_secundario), campo_fecha]
    elif estado.nombre == CANCELADO:
        controles = [ft.Text("El trabajo queda cancelado con todos sus datos. Si después se retoma, vuelve "
                             "al estado en que estaba.", size=15, color=p.texto_secundario)]
    elif vuelve:
        borra = app.trabajos.fecha_sugerida(d.estado)
        aviso = (f" y se borra la fecha de {NOMBRE_DE_FECHA[borra].lower()}"
                 if borra and borra.startswith(("fecha_comienzo", "fecha_finalizacion", "fecha_entrega"))
                 and getattr(t, borra) else "")
        controles = [ft.Text(f"El trabajo vuelve a «{estado.nombre}»{aviso}. Usalo para corregir un "
                             "paso marcado por error.", size=15, color=p.texto_secundario)]
    elif retoma:
        controles = [ft.Text(f"El trabajo vuelve a «{estado.nombre}», según las fechas que tiene cargadas.",
                             size=15, color=p.texto_secundario)]
    else:
        controles = [ft.Text(f"El trabajo pasa a «{estado.nombre}».", size=15, color=p.texto_secundario)]

    def accion() -> str | None:
        def cambiar():
            fecha = leer_fecha(campo_fecha.value, "la fecha") if campo_fecha else None
            app.trabajos.cambiar_estado(app.sesion, t.id, estado.id, fecha)
        _, error = app.ejecutar(cambiar)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, t.id, f"Trabajo en estado «{estado.nombre}».")
        return None

    if estado.nombre == CANCELADO:
        titulo, boton = "Cancelar trabajo", "Cancelar trabajo"
    elif vuelve:
        titulo, boton = f"Volver a {estado.nombre.lower()}", "Volver"
    elif retoma:
        titulo, boton = "Retomar trabajo", "Retomar"
    else:
        titulo, boton = f"Pasar a {estado.nombre.lower()}", "Confirmar"
    _dialogo_con_error(app, titulo, controles, boton, accion)


def _editar_datos(app: Aplicacion, d: DetalleTrabajo) -> None:
    p = app.paleta
    descripcion = tema.campo("Descripción", p, value=d.trabajo.descripcion, autofocus=True, max_length=200)
    observaciones = tema.campo("Observaciones (opcional)", p, value=d.trabajo.observaciones or "",
                               multiline=True, min_lines=2, max_lines=5, max_length=500)

    def accion() -> str | None:
        _, error = app.ejecutar(app.trabajos.actualizar_datos, app.sesion, d.trabajo.id,
                                descripcion.value or "", observaciones.value)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, d.trabajo.id, "Cambios guardados.")
        return None

    _dialogo_con_error(app, "Editar trabajo", [descripcion, observaciones], "Guardar cambios", accion, 560)


def _editar_pagos(app: Aplicacion, d: DetalleTrabajo) -> None:
    """Montos y las cinco fechas (RF-26 y RF-26.1)."""
    p = app.paleta
    t = d.trabajo
    a_texto = lambda m: formato_pesos(m).replace("$ ", "") if m is not None else ""  # noqa: E731
    total, sena, ayuda = vista_trabajos.campos_montos(app, a_texto(t.monto_total), a_texto(t.monto_sena))
    fechas = {c: componentes.campo_fecha(NOMBRE_DE_FECHA[c], formato_fecha(getattr(t, c)), p)
              for c in CAMPOS_DE_FECHA}
    fechas[FECHA_PRESUPUESTO] = componentes.campo_fecha("Presupuesto", formato_fecha(t.fecha_presupuesto), p)

    def accion() -> str | None:
        def guardar():
            app.trabajos.actualizar_pagos(
                app.sesion, t.id, leer_monto(total.value, "el monto total"), leer_monto(sena.value, "la seña"),
                {c: leer_fecha(f.value, "la fecha de " + (NOMBRE_DE_FECHA.get(c) or "presupuesto").lower())
                 for c, f in fechas.items()})
        _, error = app.ejecutar(guardar)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, t.id, "Montos y fechas guardados.")
        return None

    par = lambda a, b: ft.Row([ft.Container(a, expand=True), ft.Container(b, expand=True)], spacing=12)  # noqa: E731
    _dialogo_con_error(app, "Montos y fechas", [
        tema.etiqueta_superior("Montos", p), par(total, sena), ayuda,
        tema.etiqueta_superior("Fechas", p),
        par(fechas[FECHA_PRESUPUESTO], fechas["fecha_cobro_sena"]),
        par(fechas["fecha_comienzo"], fechas["fecha_finalizacion"]),
        par(fechas["fecha_entrega"], fechas["fecha_cobro_saldo"]),
        ft.Text("Si el trabajo se anotó tarde, poné la fecha real del presupuesto: ninguna otra fecha "
                "puede ser anterior.", size=13, color=p.texto_tenue),
    ], "Guardar", accion, 600)


def _registrar_cobro(app: Aplicacion, d: DetalleTrabajo, campo: str) -> None:
    p = app.paleta
    que = "la seña" if campo == "fecha_cobro_sena" else "el saldo"
    monto = d.trabajo.monto_sena if campo == "fecha_cobro_sena" else d.trabajo.saldo
    fecha = componentes.campo_fecha("Fecha de cobro", formato_fecha(date.today()), p, autofocus=True)
    controles: list[ft.Control] = [ft.Text(f"Monto: {formato_pesos(monto)}", size=16, color=p.texto), fecha]
    if campo == "fecha_cobro_sena" and d.estado.nombre == PRESUPUESTADO:
        controles.append(tema.aviso("Al cobrar la seña, el trabajo pasa a «Confirmado».", p, tipo="info"))
    elif campo == "fecha_cobro_saldo" and d.estado.nombre != "Instalado":
        controles.append(tema.aviso("Pago anticipado: el trabajo sigue su curso y, al instalarlo, "
                                    "se pasa a «Cobrado» con esta fecha.", p, tipo="info"))

    def accion() -> str | None:
        confirmo, error = app.ejecutar(lambda: app.trabajos.registrar_cobro(
            app.sesion, d.trabajo.id, campo, leer_fecha(fecha.value, "la fecha de cobro")))
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, d.trabajo.id, f"Cobro de {que} registrado." + (" Trabajo confirmado." if confirmo else ""))
        return None

    _dialogo_con_error(app, f"Registrar cobro de {que}", controles, "Registrar", accion)


def _eliminar(app: Aplicacion, d: DetalleTrabajo) -> None:
    p = app.paleta

    def accion() -> str | None:
        _, error = app.ejecutar(app.trabajos.eliminar, app.sesion, d.trabajo.id)
        if error:
            return error
        app.cerrar_dialogo()
        app.ir_a("trabajos")
        componentes.aviso_flotante(app.page, f"Trabajo #{d.trabajo.id} eliminado.", p)
        return None

    _dialogo_con_error(app, "Eliminar trabajo", [
        ft.Text(f"Se borra el trabajo #{d.trabajo.id} «{d.trabajo.descripcion}» con todo lo que tenga "
                "cargado. No se puede deshacer; queda registrado en la auditoría.",
                size=15, color=p.texto_secundario)], "Eliminar", accion)


# ---------- partes de la pantalla ----------
def _fecha_de(d: DetalleTrabajo, estado: EstadoTrabajo, app: Aplicacion) -> date | None:
    if estado.nombre == PRESUPUESTADO:
        return d.trabajo.fecha_presupuesto
    campo = app.trabajos.fecha_sugerida(estado)
    return getattr(d.trabajo, campo) if campo else None


def _texto_estado(app: Aplicacion, d: DetalleTrabajo) -> str:
    fecha = _fecha_de(d, d.estado, app)
    return f"{d.estado.nombre} desde el {fecha:%d/%m}" if fecha else d.estado.nombre


def _tarjeta_estado(app: Aplicacion, d: DetalleTrabajo) -> ft.Container:
    p = app.paleta
    recorrido, _ = app.ejecutar(app.trabajos.recorrido)
    cancelado = d.estado.nombre == CANCELADO
    alcanzados = app.trabajos.alcanzados(d.estado)
    pasos = []
    for e in recorrido or []:
        hecho = e.nombre in alcanzados
        actual = e.id == d.estado.id
        fecha = _fecha_de(d, e, app)
        if fecha and hecho:
            nota = f"{fecha:%d/%m}"
        elif fecha and e.nombre == COBRADO:
            nota = f"pagado {fecha:%d/%m}"     # pago anticipado: el trabajo sigue su curso
        elif fecha:
            nota = f"prevista {fecha:%d/%m}"   # fecha pactada de algo que todavía no pasó
        else:
            nota = "—"
        pasos.append(ft.Column([
            ft.Container(height=4, border_radius=4, bgcolor=p.acento if hecho else p.borde_fuerte),
            ft.Text(e.nombre, size=13, font_family=SANS_SEMI if hecho else tema.SANS,
                    color=p.acento_texto if actual else (p.texto if hecho else p.texto_tenue)),
            ft.Text(nota, size=12, color=p.texto_tenue, italic=bool(fecha and not hecho)),
        ], spacing=8, expand=True))

    siguiente = app.trabajos.estado_siguiente(d.estado)
    anterior = app.trabajos.estado_anterior(d.estado)
    acciones: list[ft.Control] = []
    if siguiente:
        acciones.append(componentes.boton_con_icono(
            f"Pasar a {siguiente.nombre.lower()}", ft.Icons.ARROW_FORWARD, p,
            lambda _: _pasar_a(app, d, siguiente)))
    if cancelado:
        retomar = app.trabajos.estado_para_retomar(d.trabajo)
        acciones.append(componentes.boton_con_icono(
            f"Retomar trabajo ({retomar.nombre.lower()})", ft.Icons.REPLAY, p,
            lambda _: _pasar_a(app, d, retomar)))
    if anterior:
        acciones.append(ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.UNDO, size=18, color=p.texto_secundario),
                            ft.Text(f"Volver a {anterior.nombre.lower()}", color=p.texto_secundario, size=14)],
                           spacing=6, tight=True),
            on_click=lambda _: _pasar_a(app, d, anterior), height=44,
            tooltip="Para corregir un paso marcado por error"))
    acciones.append(ft.Container(expand=True))
    if app.trabajos.puede_cancelarse(d.estado):
        cancelado_estado = next((e for e in app.trabajos.estados() if e.nombre == CANCELADO), None)
        acciones.append(ft.TextButton(content=ft.Text("Cancelar trabajo", color=p.error_texto, size=14),
                                      on_click=lambda _: _pasar_a(app, d, cancelado_estado), height=44))
    if d.estado.nombre in ESTADOS_QUE_SE_PUEDEN_ELIMINAR:
        acciones.append(ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color=p.error_texto),
                            ft.Text("Eliminar", color=p.error_texto, size=14)], spacing=4, tight=True),
            on_click=lambda _: _eliminar(app, d), height=44))

    contenido: list[ft.Control] = []
    if cancelado:
        contenido.append(tema.aviso("Trabajo cancelado. Se conservan todos sus datos y se puede retomar.",
                                    p, tipo="info"))
    contenido += [ft.Row(pasos, spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
                  ft.Row(acciones, spacing=10)]
    return componentes.tarjeta(ft.Column(contenido, spacing=18), p, padding=22)


def _fila_importe(etiqueta: str, valor: str, p, color: str | None = None) -> ft.Row:
    return ft.Row([ft.Text(etiqueta, size=15, color=p.texto_tenue, expand=True),
                   ft.Text(valor, size=15, font_family=SANS_MEDIA, color=color or p.texto)])


def _tarjeta_pagos(app: Aplicacion, d: DetalleTrabajo) -> ft.Container:
    p = app.paleta
    t = d.trabajo
    editar = ft.TextButton(content=ft.Text("Editar montos y fechas", color=p.acento_texto, size=14),
                           on_click=lambda _: _editar_pagos(app, d), height=40)
    titulo = ft.Row([tema.titulo("Pagos", p, 26), ft.Container(expand=True), editar])
    if t.monto_total is None:
        return componentes.tarjeta(ft.Column([
            titulo, ft.Text("Todavía no tiene monto. Cargalo cuando esté el presupuesto: la seña se "
                            "sugiere sola.", size=14, color=p.texto_tenue)], spacing=12), p, padding=20)

    porcentaje = (t.monto_sena / t.monto_total * 100) if t.monto_sena and t.monto_total else 0
    sena_cobrada = t.fecha_cobro_sena is not None
    filas: list[ft.Control] = [
        titulo,
        _fila_importe("Monto total", formato_pesos(t.monto_total), p),
        _fila_importe(f"Seña ({porcentaje:.0f}%)" + (f" · {t.fecha_cobro_sena:%d/%m}" if sena_cobrada else ""),
                      formato_pesos(t.monto_sena) + (" ✓" if sena_cobrada and t.monto_sena else ""), p,
                      p.exito if sena_cobrada and t.monto_sena else None),
        ft.ProgressBar(value=float(t.cobrado / t.monto_total) if t.monto_total else 0, bar_height=8,
                       border_radius=8, color=p.acento, bgcolor=p.borde,
                       semantics_label="Porcentaje cobrado"),
        ft.Row([ft.Text("Saldo" + (f" · cobrado {t.fecha_cobro_saldo:%d/%m}" if t.fecha_cobro_saldo else ""),
                        size=15, color=p.texto_tenue, expand=True),
                ft.Text(formato_pesos(t.saldo), font_family=SERIF, size=32,
                        color=p.exito if t.fecha_cobro_saldo else p.texto)],
               vertical_alignment=ft.CrossAxisAlignment.END),
    ]
    if d.estado.nombre != CANCELADO:
        if t.monto_sena and not sena_cobrada:
            filas.append(tema.boton_secundario("Registrar cobro de la seña", p,
                                               lambda _: _registrar_cobro(app, d, "fecha_cobro_sena")))
        elif t.saldo and not t.fecha_cobro_saldo and d.estado.nombre != PRESUPUESTADO:
            filas.append(tema.boton_secundario("Registrar cobro del saldo", p,
                                               lambda _: _registrar_cobro(app, d, "fecha_cobro_saldo")))
    if t.pendiente_de_cobro == 0:
        filas.append(ft.Text("Cobrado por completo.", size=14, color=p.exito))
    return componentes.tarjeta(ft.Column(filas, spacing=12), p, padding=20)


def _tarjeta_fechas(app: Aplicacion, d: DetalleTrabajo) -> ft.Container:
    p = app.paleta
    filas: list[ft.Control] = [ft.Row([tema.titulo("Fechas", p, 26)], height=40)]
    t = d.trabajo
    filas.append(_fila_importe("Presupuesto", formato_fecha(t.fecha_presupuesto) or "—", p))
    if t.fecha_alta and t.fecha_presupuesto and t.fecha_alta.date() != t.fecha_presupuesto:
        filas.append(ft.Text(f"Cargado en el sistema el {t.fecha_alta:%d/%m/%Y}", size=12,
                             color=p.texto_tenue, italic=True))
    for campo in ("fecha_cobro_sena", "fecha_comienzo", "fecha_finalizacion", "fecha_entrega",
                  "fecha_cobro_saldo"):
        valor = getattr(d.trabajo, campo)
        filas.append(_fila_importe(NOMBRE_DE_FECHA[campo], formato_fecha(valor) or "—", p,
                                   None if valor else p.texto_tenue))
    return componentes.tarjeta(ft.Column(filas, spacing=10), p, padding=20)


def construir(app: Aplicacion, id_trabajo: int) -> ft.Control:
    p = app.paleta
    volver = ft.TextButton(
        content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=18, color=p.texto_secundario),
                        ft.Text("Trabajos", color=p.texto_secundario, size=14)], spacing=6, tight=True),
        on_click=lambda _: app.ir_a("trabajos"))
    d, error = app.ejecutar(app.trabajos.detalle, id_trabajo)
    if error:
        return ft.Column([volver, tema.aviso(error, p)], spacing=16)

    c, o, t = d.cliente, d.obra, d.trabajo
    ruta = ft.Row([
        volver, ft.Text("›", color=p.texto_tenue),
        ft.TextButton(content=ft.Text(c.nombre_completo, color=p.texto_secundario, size=14),
                      on_click=lambda _: app.ir_a("cliente", id_cliente=c.id), tooltip="Ver la ficha del cliente"),
        ft.Text("›", color=p.texto_tenue),
        ft.Text(f"#{t.id}", color=p.texto_tenue, size=14),
    ], spacing=4)

    texto_estado, fondo_estado = componentes.colores_estado_trabajo(d.estado.nombre, p)
    encabezado = ft.Row([
        ft.Column([
            componentes.etiqueta_estado(_texto_estado(app, d), texto_estado, fondo_estado),
            tema.titulo(t.descripcion, p, 44),
            ft.Text(f"{c.nombre_completo} · {o.direccion}, {o.localidad} · {c.telefono}", size=15,
                    color=p.texto_secundario, selectable=True),
        ], spacing=6, expand=True),
        componentes.boton_con_icono("Editar datos", ft.Icons.EDIT_OUTLINED, p,
                                    lambda _: _editar_datos(app, d), principal=False),
        componentes.boton_con_icono("Listado de corte", ft.Icons.DESCRIPTION_OUTLINED, p, None,
                                    disabled=True, tooltip="Disponible cuando esté el despiece"),
    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.END)

    partes: list[ft.Control] = [
        ruta, encabezado, _tarjeta_estado(app, d),
        ft.ResponsiveRow([
            ft.Container(_tarjeta_pagos(app, d), col={"xs": 12, "lg": 7}),
            ft.Container(_tarjeta_fechas(app, d), col={"xs": 12, "lg": 5}),
        ], spacing=16, run_spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
    ]
    if t.observaciones:
        partes.append(componentes.tarjeta(ft.Column([
            tema.etiqueta_superior("Observaciones", p),
            ft.Text(t.observaciones, size=15, color=p.texto_secundario, selectable=True)], spacing=8),
            p, padding=20))
    partes += [
        ft.Row([tema.titulo("Muebles y módulos", p, 30), ft.Container(expand=True),
                componentes.boton_con_icono("Agregar mueble", ft.Icons.ADD, p, None, principal=False,
                                            disabled=True, tooltip="Disponible con el catálogo y el despiece")]),
        componentes.estado_vacio(
            ft.Icons.CHAIR_OUTLINED, "Próximamente",
            "Los muebles, módulos y el despiece se cargan acá cuando estén el catálogo de materiales "
            "y el motor de despiece.", p),
    ]
    return ft.Column(partes, spacing=18)
