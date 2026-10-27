"""Inicio (diseño 2): saludo, aviso de último ingreso (RF-03.7), resumen del
taller, trabajos en curso y lo que hay para resolver."""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Alerta, DetalleTrabajo, ResumenInicio, Sesion
from carpinteria.negocio.inicio import texto_entregas
from carpinteria.negocio.trabajos import (INSTALADO, PRESUPUESTADO, formato_pesos, limite_de_entrega,
                                          texto_entrega)
from carpinteria.presentacion import componentes, tema, vista_clientes, vista_trabajos
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


def _ir_a_trabajos(app: Aplicacion, **filtros) -> None:
    """Abre el listado de trabajos con un filtro ya aplicado."""
    app.recuerdos["trabajos"] = {"texto": "", "estado": "todos", "periodo": "Todos", "por_cobrar": False,
                                 **filtros}
    app.ir_a("trabajos")


def _id_estado(app: Aplicacion, nombre: str) -> str:
    estado, _ = app.ejecutar(app.trabajos.estado_por_nombre, nombre)
    return str(estado.id) if estado else "todos"


def _cifra(app: Aplicacion, etiqueta: str, valor: str, detalle: str, al_tocar, destacada: bool = False):
    p = app.paleta
    return ft.Container(
        content=ft.Column([
            ft.Text(etiqueta, size=13, font_family=SANS_MEDIA, color=p.texto_tenue),
            ft.Text(valor, font_family=SERIF, size=40, color=p.acento_texto if destacada else p.texto),
            ft.Text(detalle, size=13, color=p.texto_tenue, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ], spacing=2),
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=14,
        padding=ft.Padding.symmetric(horizontal=20, vertical=16), on_click=al_tocar, ink=True,
        col={"xs": 12, "sm": 6, "xl": 3},
    )


def _entrega(d: DetalleTrabajo) -> str:
    if d.estado.nombre == INSTALADO:
        return "Instalado"
    if d.trabajo.fecha_entrega:
        return texto_entrega(d.trabajo).replace("Semana del", "Sem.")
    return "—" if d.estado.nombre == PRESUPUESTADO else "A coordinar"


def _saldo(d: DetalleTrabajo) -> str:
    t = d.trabajo
    if t.monto_total is None:
        return "Sin monto"
    if d.estado.nombre == PRESUPUESTADO:
        return formato_pesos(t.monto_total)
    return formato_pesos(t.pendiente_de_cobro) if t.pendiente_de_cobro else "Cobrado"


def _fila_en_curso(app: Aplicacion, d: DetalleTrabajo, hoy: date) -> ft.Container:
    p = app.paleta
    limite = limite_de_entrega(d.trabajo)
    atrasada = limite and limite < hoy and d.estado.nombre not in (PRESUPUESTADO, INSTALADO)
    return ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text(d.trabajo.descripcion, size=15, font_family=SANS_MEDIA, color=p.texto, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{d.cliente.nombre_completo} · {d.obra.localidad}", size=13, color=p.texto_tenue,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=0, expand=True),
            ft.Container(componentes.etiqueta_estado_trabajo(d.estado.nombre, p), width=130),
            ft.Text(_entrega(d), size=14, width=88, color=p.error_texto if atrasada else p.texto_secundario),
            ft.Text(_saldo(d), size=14, width=120, text_align=ft.TextAlign.RIGHT, color=p.texto),
        ], spacing=12),
        padding=ft.Padding.symmetric(horizontal=12, vertical=10), border_radius=10, ink=True,
        on_click=lambda _: app.ir_a("trabajo", id_trabajo=d.trabajo.id),
        tooltip="Entrega atrasada" if atrasada else None,
    )


def _tarjeta_en_curso(app: Aplicacion, r: ResumenInicio, hoy: date) -> ft.Container:
    p = app.paleta
    encabezado = ft.Row([tema.titulo("Trabajos en curso", p, 28), ft.Container(expand=True),
                         ft.TextButton(content=ft.Text("Ver todos", color=p.acento_texto, size=14),
                                       on_click=lambda _: _ir_a_trabajos(app))])
    if not r.en_curso:
        cuerpo: list[ft.Control] = [ft.Text("No hay trabajos en curso. Los nuevos aparecen acá hasta que "
                                            "se cobran.", size=14, color=p.texto_tenue)]
    else:
        titulos = ft.Row([
            ft.Text("Trabajo · cliente", size=12, color=p.texto_tenue, expand=True),
            ft.Text("Estado", size=12, color=p.texto_tenue, width=130),
            ft.Text("Entrega", size=12, color=p.texto_tenue, width=88),
            ft.Text("Saldo", size=12, color=p.texto_tenue, width=120, text_align=ft.TextAlign.RIGHT),
        ], spacing=12)
        cuerpo = [ft.Container(titulos, padding=ft.Padding.symmetric(horizontal=12)),
                  ft.Divider(color=p.borde, height=1),
                  *[_fila_en_curso(app, d, hoy) for d in r.en_curso]]
    return componentes.tarjeta(ft.Column([encabezado, *cuerpo], spacing=6), p, padding=20,
                               col={"xs": 12, "lg": 8})


def _item_alerta(app: Aplicacion, a: Alerta) -> ft.Container:
    p = app.paleta
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.ERROR_OUTLINE if a.urgente else ft.Icons.INFO_OUTLINE, size=20,
                    color=p.error_texto if a.urgente else p.acento_texto),
            ft.Column([ft.Text(a.titulo, size=14, font_family=SANS_MEDIA, color=p.texto),
                       ft.Text(a.detalle, size=13, color=p.texto_tenue)], spacing=2, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
        padding=ft.Padding.symmetric(horizontal=10, vertical=10), border_radius=10, ink=True,
        on_click=(lambda _: app.ir_a("trabajo", id_trabajo=a.id_trabajo)) if a.id_trabajo else None,
    )


def _tarjeta_alertas(app: Aplicacion, r: ResumenInicio) -> ft.Container:
    p = app.paleta
    if r.alertas:
        cuerpo = [_item_alerta(app, a) for a in r.alertas[:8]]
        if len(r.alertas) > 8:
            cuerpo.append(ft.Text(f"y {len(r.alertas) - 8} más", size=13, color=p.texto_tenue))
    else:
        cuerpo = [ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=p.exito, size=20),
                          ft.Text("Todo al día: no hay nada pendiente.", size=14, color=p.texto_secundario)],
                         spacing=10)]
    return componentes.tarjeta(ft.Column([tema.titulo("Para resolver", p, 28), *cuerpo], spacing=6),
                               p, padding=20, col={"xs": 12, "lg": 4})


def construir(app: Aplicacion, sesion: Sesion) -> ft.Control:
    p = app.paleta
    ahora = datetime.now()
    hoy = ahora.date()
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

    saludo_y_acciones = ft.Row([
        ft.Column([
            tema.etiqueta_superior(fecha_larga(ahora), p),
            tema.titulo(f"{saludo(ahora)}, {nombre}.", p, 48),
        ], spacing=4, expand=True),
        componentes.boton_con_icono("Nuevo trabajo", ft.Icons.ADD, p, lambda _: vista_trabajos.abrir_nuevo(app)),
        componentes.boton_con_icono("Nuevo cliente", ft.Icons.PERSON_ADD_ALT_1_OUTLINED, p,
                                    lambda _: vista_clientes.abrir_formulario(app), principal=False),
    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.END)

    r, error = app.ejecutar(app.inicio.resumen)
    if error:
        return ft.Column([aviso_ingreso, saludo_y_acciones, tema.aviso(error, p)], spacing=28)

    if r.presupuestos_sin_confirmar == 0:
        detalle_presupuestos = "ninguno esperando respuesta"
    elif r.dias_presupuesto_mas_antiguo:
        detalle_presupuestos = f"el más antiguo, hace {r.dias_presupuesto_mas_antiguo} días"
    else:
        detalle_presupuestos = "el más antiguo, de hoy"
    cifras = ft.ResponsiveRow([
        _cifra(app, "En producción", str(r.en_produccion),
               "trabajo en el taller" if r.en_produccion == 1 else "trabajos en el taller",
               lambda _: _ir_a_trabajos(app, estado=_id_estado(app, "En producción"))),
        _cifra(app, "Entregas en 7 días", str(len(r.entregas_proximas)), texto_entregas(r.entregas_proximas, hoy),
               lambda _: _ir_a_trabajos(app)),
        _cifra(app, "Por cobrar", formato_pesos(r.por_cobrar),
               f"de {r.trabajos_por_cobrar} trabajo{'s' if r.trabajos_por_cobrar != 1 else ''}",
               lambda _: _ir_a_trabajos(app, por_cobrar=True), destacada=r.por_cobrar > 0),
        _cifra(app, "Presupuestos sin confirmar", str(r.presupuestos_sin_confirmar), detalle_presupuestos,
               lambda _: _ir_a_trabajos(app, estado=_id_estado(app, PRESUPUESTADO))),
    ], spacing=16, run_spacing=16)

    return ft.Column(
        [
            aviso_ingreso,
            saludo_y_acciones,
            cifras,
            ft.ResponsiveRow([_tarjeta_en_curso(app, r, hoy), _tarjeta_alertas(app, r)],
                             spacing=16, run_spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
        ],
        spacing=28,
    )
