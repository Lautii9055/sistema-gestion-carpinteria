"""Servicio de autenticación (RF-01 a RF-03.7).

Reglas de seguridad que implementa:
- Contraseñas con hash bcrypt (costo 12, salt aleatorio incluido).
- Mensaje de error genérico: nunca dice si falló el usuario o la contraseña.
- Si el usuario no existe se verifica igual contra un hash ficticio, para que
  el tiempo de respuesta no revele qué usuarios existen.
- Bloqueo temporal tras N contraseñas incorrectas seguidas (parámetros).
- Todo intento queda en la auditoría; los fallidos desde el último ingreso se
  informan al usuario al entrar (RF-03.7).
"""
import socket
from collections.abc import Callable
from datetime import datetime, timedelta

import bcrypt

from carpinteria.negocio.entidades import Sesion, Usuario
from carpinteria.negocio.puertos import (RepositorioAuditoria, RepositorioParametros,
                                         RepositorioUsuarios)

COSTO_BCRYPT = 12
LIMITE_BYTES_BCRYPT = 72  # bcrypt solo usa los primeros 72 bytes

# Valores por defecto si un parámetro no estuviera cargado en la base.
POR_DEFECTO = {
    "max_intentos_login": 5,
    "minutos_bloqueo": 15,
    "largo_minimo_contrasena": 10,
    "minutos_inactividad": 15,
}

# Hash de una contraseña que nadie conoce: se usa cuando el usuario no existe.
_HASH_FICTICIO = bcrypt.hashpw(b"usuario-inexistente", bcrypt.gensalt(COSTO_BCRYPT))


class ErrorAutenticacion(Exception):
    """Error que se puede mostrar tal cual al usuario."""


class CredencialesInvalidas(ErrorAutenticacion):
    def __init__(self) -> None:
        super().__init__("Usuario o contraseña incorrectos.")


class UsuarioBloqueado(ErrorAutenticacion):
    def __init__(self, minutos: int) -> None:
        self.minutos = minutos
        unidad = "minuto" if minutos == 1 else "minutos"
        super().__init__(
            f"Por seguridad, el usuario quedó bloqueado. Probá de nuevo en {minutos} {unidad}."
        )


class ContrasenaNoValida(ErrorAutenticacion):
    pass


def generar_hash(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt(COSTO_BCRYPT)).decode("ascii")


def _coincide(contrasena: str, hash_guardado: bytes | str) -> bool:
    datos = contrasena.encode("utf-8")
    if len(datos) > LIMITE_BYTES_BCRYPT:
        return False
    if isinstance(hash_guardado, str):
        hash_guardado = hash_guardado.encode("ascii")
    try:
        return bcrypt.checkpw(datos, hash_guardado)
    except ValueError:  # hash con formato inválido
        return False


class ServicioAutenticacion:
    def __init__(self, usuarios: RepositorioUsuarios, auditoria: RepositorioAuditoria,
                 parametros: RepositorioParametros,
                 reloj: Callable[[], datetime] = datetime.now,
                 equipo: str | None = None) -> None:
        self._usuarios = usuarios
        self._auditoria = auditoria
        self._parametros = parametros
        self._reloj = reloj
        self._equipo = equipo or socket.gethostname()

    # ---------- parámetros ----------
    def _parametro(self, clave: str) -> int:
        valor = self._parametros.obtener(clave)
        return int(valor) if valor is not None else POR_DEFECTO[clave]

    @property
    def largo_minimo_contrasena(self) -> int:
        return self._parametro("largo_minimo_contrasena")

    @property
    def minutos_inactividad(self) -> int:
        return self._parametro("minutos_inactividad")

    # ---------- ingreso ----------
    def ingresar(self, nombre_usuario: str, contrasena: str) -> Sesion:
        nombre_usuario = nombre_usuario.strip()
        ahora = self._reloj()
        usuario = self._usuarios.buscar_por_nombre(nombre_usuario) if nombre_usuario else None

        if usuario is None or not usuario.es_activo:
            _coincide(contrasena, _HASH_FICTICIO)  # mismo tiempo que un intento real
            self._auditar("LOGIN_FALLIDO", usuario_ingresado=nombre_usuario[:50] or None,
                          id_usuario=usuario.id if usuario else None,
                          detalle=None if usuario is None else "usuario dado de baja")
            raise CredencialesInvalidas()

        if usuario.esta_bloqueado(ahora):
            # Mientras dura el bloqueo ni siquiera se verifica la contraseña.
            self._auditar("LOGIN_FALLIDO", id_usuario=usuario.id, detalle="intento durante el bloqueo")
            raise UsuarioBloqueado(self._minutos_restantes(usuario.bloqueado_hasta, ahora))

        if not _coincide(contrasena, usuario.hash_contrasena):
            self._registrar_fallo(usuario, ahora)  # lanza la excepción que corresponda

        fallidos = self._auditoria.contar_ingresos_fallidos(usuario.id, usuario.ultimo_ingreso)
        self._usuarios.registrar_ingreso_exitoso(usuario.id, ahora)
        self._auditar("LOGIN_OK", id_usuario=usuario.id)
        return Sesion(
            usuario=usuario,
            ultimo_ingreso_anterior=usuario.ultimo_ingreso,
            intentos_fallidos_desde_entonces=fallidos,
            debe_cambiar_contrasena=usuario.debe_cambiar_contrasena,
        )

    def _registrar_fallo(self, usuario: Usuario, ahora: datetime) -> None:
        intentos = usuario.intentos_fallidos + 1
        self._auditar("LOGIN_FALLIDO", id_usuario=usuario.id)
        if intentos >= self._parametro("max_intentos_login"):
            minutos = self._parametro("minutos_bloqueo")
            # Al bloquear, el contador vuelve a 0: al vencer, hay N intentos nuevos.
            self._usuarios.registrar_fallo(usuario.id, 0, ahora + timedelta(minutes=minutos))
            self._auditar("USUARIO_BLOQUEADO", id_usuario=usuario.id,
                          detalle=f"{intentos} intentos fallidos seguidos; bloqueo de {minutos} min")
            raise UsuarioBloqueado(minutos)
        self._usuarios.registrar_fallo(usuario.id, intentos, None)
        raise CredencialesInvalidas()

    @staticmethod
    def _minutos_restantes(hasta: datetime, ahora: datetime) -> int:
        segundos = (hasta - ahora).total_seconds()
        return max(1, int(-(-segundos // 60)))  # redondeo hacia arriba

    # ---------- cierre de sesión ----------
    def cerrar_sesion(self, sesion: Sesion, por_inactividad: bool = False) -> None:
        self._auditar("CIERRE_INACTIVIDAD" if por_inactividad else "LOGOUT",
                      id_usuario=sesion.usuario.id)

    # ---------- contraseñas ----------
    def validar_contrasena_nueva(self, usuario: Usuario, nueva: str, confirmacion: str) -> list[str]:
        """Devuelve los problemas encontrados (lista vacía = válida). RF-03.2"""
        problemas = []
        if len(nueva) < self.largo_minimo_contrasena:
            problemas.append(f"Tiene que tener al menos {self.largo_minimo_contrasena} caracteres.")
        if len(nueva.encode("utf-8")) > LIMITE_BYTES_BCRYPT:
            problemas.append("Es demasiado larga (máximo 72 bytes).")
        if nueva.strip().casefold() == usuario.nombre_usuario.casefold():
            problemas.append("No puede ser igual al nombre de usuario.")
        if nueva != confirmacion:
            problemas.append("Las dos contraseñas no coinciden.")
        if not problemas and _coincide(nueva, usuario.hash_contrasena):
            problemas.append("Tiene que ser distinta de la contraseña actual.")
        return problemas

    def cambiar_contrasena(self, id_usuario: int, nueva: str, confirmacion: str) -> None:
        usuario = self._usuarios.buscar_por_id(id_usuario)
        if usuario is None:
            raise ErrorAutenticacion("El usuario ya no existe.")
        problemas = self.validar_contrasena_nueva(usuario, nueva, confirmacion)
        if problemas:
            raise ContrasenaNoValida(" ".join(problemas))
        self._usuarios.cambiar_contrasena(id_usuario, generar_hash(nueva), self._reloj())
        self._auditar("CAMBIO_CONTRASENA", id_usuario=id_usuario)

    def cambiar_contrasena_propia(self, id_usuario: int, actual: str, nueva: str,
                                  confirmacion: str) -> None:
        """Cambio voluntario desde "Mi contraseña": pide la actual (RF-02)."""
        usuario = self._usuarios.buscar_por_id(id_usuario)
        if usuario is None or not _coincide(actual, usuario.hash_contrasena):
            raise ContrasenaNoValida("La contraseña actual no es correcta.")
        self.cambiar_contrasena(id_usuario, nueva, confirmacion)

    # ---------- auditoría ----------
    def _auditar(self, codigo: str, **datos) -> None:
        self._auditoria.registrar(codigo, equipo=self._equipo, **datos)
