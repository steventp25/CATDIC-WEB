# Fundación F2 · sesión (contrato §4.1; escenario 12 del §7): cookie, bloqueo por intentos, caducidad,
# desactivación y salida. El reloj se simula sustituyendo sesiones._ahora; nada depende de esperar de verdad.
from datetime import datetime, timedelta

import pytest

import main
from f2_ayudas import CONTRASENA, cliente, crear_persona, dar, filas, preparar_entorno
from identidad import contrasenas, sesiones

pytestmark = pytest.mark.seguridad_real

OBRA = "terra-living"


class Reloj:
    def __init__(self):
        self.t = datetime(2026, 11, 20, 8, 0, 0)

    def __call__(self):
        return self.t

    def avanzar(self, **delta):
        self.t += timedelta(**delta)


@pytest.fixture
def reloj(tmp_path, monkeypatch):
    preparar_entorno(tmp_path, monkeypatch)
    r = Reloj()
    monkeypatch.setattr(sesiones, "_ahora", r)
    return r


def _entrar(c, usuario, contrasena=CONTRASENA):
    return c.post("/api/sesion", json={"usuario": usuario, "contrasena": contrasena})


def test_cookie_httponly_samesite_strict_y_sin_hash_en_la_respuesta(reloj):
    p = crear_persona("persona-a")
    dar(p, OBRA, "consultar")
    with cliente(main.app) as c:
        r = _entrar(c, "Persona-A")          # el usuario no distingue mayúsculas
        assert r.status_code == 200
        cookie = r.headers["set-cookie"].lower()
        assert "catdic_sesion=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert "path=/" in cookie and f"max-age={7 * 24 * 3600}" in cookie
        assert "hash" not in r.text and CONTRASENA not in r.text
        yo = c.get("/api/sesion").json()["usuario"]
        assert yo["usuario"] == "persona-a" and yo["obras"] == [
            {"obra_id": OBRA, "nombre": yo["obras"][0]["nombre"], "funciones": ["consultar"]}]
    token_guardado = filas("SELECT token_hash FROM sesiones")[0]["token_hash"]
    assert len(token_guardado) == 64     # la base guarda el sha256, no el token


def test_contrasena_con_scrypt_y_minimo_de_longitud():
    h = contrasenas.generar_hash("una-clave-larga")
    assert h.startswith("scrypt$16384$8$1$") and "una-clave-larga" not in h
    assert contrasenas.verificar("una-clave-larga", h) and not contrasenas.verificar("otra-clave-larga", h)
    assert h != contrasenas.generar_hash("una-clave-larga")     # sal distinta
    assert not contrasenas.verificar("x", "basura") and not contrasenas.verificar("x", "scrypt$1$2$3$no$base64")
    with pytest.raises(contrasenas.ContrasenaInvalida):
        contrasenas.generar_hash("corta")


def test_cinco_fallos_bloquean_con_espera_creciente_y_sin_contrasena_en_la_auditoria(reloj):
    crear_persona("persona-a")
    with cliente(main.app) as c:
        for _ in range(5):
            r = _entrar(c, "persona-a", "clave-equivocada-1")
            assert r.status_code == 401 and r.json()["detail"] == "Usuario o contraseña incorrectos."
        # El sexto intento, aunque sea correcto, espera 15 min
        r = _entrar(c, "persona-a")
        assert r.status_code == 429 and 899 <= int(r.headers["retry-after"]) <= 901
        reloj.avanzar(minutes=14)
        assert _entrar(c, "persona-a").status_code == 429
        reloj.avanzar(minutes=2)
        # Pasada la espera: otro fallo dobla la espera (30 min)
        assert _entrar(c, "persona-a", "clave-equivocada-2").status_code == 401
        r = _entrar(c, "persona-a")
        assert r.status_code == 429 and 1799 <= int(r.headers["retry-after"]) <= 1801
        reloj.avanzar(minutes=31)
        assert _entrar(c, "persona-a").status_code == 200       # el éxito reinicia la cuenta
        assert _entrar(c, "persona-a", "clave-equivocada-3").status_code == 401
        assert _entrar(c, "persona-a").status_code == 200
        # Un usuario inexistente responde igual que una contraseña mala
        r = _entrar(c, "no-existe")
        assert r.status_code == 401 and r.json()["detail"] == "Usuario o contraseña incorrectos."
    acciones = [f["accion"] for f in filas("SELECT accion FROM auditoria WHERE modulo = 'SESION' ORDER BY id")]
    assert acciones.count("ENTRADA_FALLIDA") == 8 and acciones.count("ENTRADA_BLOQUEADA") == 3
    assert acciones.count("ENTRADA") == 2
    texto = " ".join(f["detalle_json"] or "" for f in filas("SELECT detalle_json FROM auditoria"))
    assert "clave-equivocada" not in texto and CONTRASENA not in texto


def test_espera_con_tope_de_24_horas(reloj):
    crear_persona("persona-a")
    with cliente(main.app) as c:
        for _ in range(5):
            _entrar(c, "persona-a", "mala-mala-mala")
        for _ in range(12):            # cada fallo tras la espera la duplica
            reloj.avanzar(hours=25)
            assert _entrar(c, "persona-a", "mala-mala-mala").status_code == 401
        r = _entrar(c, "persona-a")
        assert r.status_code == 429 and int(r.headers["retry-after"]) <= 24 * 3600 + 1


def test_bloqueo_es_por_usuario_y_direccion(reloj):
    """Los fallos contra un usuario no bloquean a otro usuario."""
    crear_persona("persona-a")
    crear_persona("persona-b")
    with cliente(main.app) as c:
        for _ in range(5):
            _entrar(c, "persona-a", "mala-mala-mala")
        assert _entrar(c, "persona-a").status_code == 429
        assert _entrar(c, "persona-b").status_code == 200


def test_caduca_a_las_12_horas_sin_uso(reloj):
    crear_persona("persona-a")
    with cliente(main.app) as c:
        assert _entrar(c, "persona-a").status_code == 200
        reloj.avanzar(hours=11, minutes=59)
        assert c.get("/api/sesion").status_code == 200      # el uso renueva la inactividad
        reloj.avanzar(hours=11, minutes=59)
        assert c.get("/api/sesion").status_code == 200
        reloj.avanzar(hours=12)
        assert c.get("/api/sesion").status_code == 401
        reloj.avanzar(minutes=1)
        assert c.get("/api/sesion").status_code == 401      # cerrada: no revive
    assert filas("SELECT motivo_cierre FROM sesiones")[0]["motivo_cierre"] == "caducada_12_h_sin_uso"


def test_caduca_a_los_7_dias_aunque_se_use(reloj):
    crear_persona("persona-a")
    with cliente(main.app) as c:
        assert _entrar(c, "persona-a").status_code == 200
        for _ in range(16):
            reloj.avanzar(hours=10)
            assert c.get("/api/sesion").status_code == 200
        reloj.avanzar(hours=8)                               # 168 h desde la entrada
        assert c.get("/api/sesion").status_code == 401
    assert filas("SELECT motivo_cierre FROM sesiones")[0]["motivo_cierre"] == "caducada_7_dias"


def test_desactivar_cierra_todas_las_sesiones_y_no_deja_entrar(reloj):
    admin = crear_persona("admin-global", es_admin=True)
    p = crear_persona("persona-a")
    dar(p, OBRA, "consultar")
    with cliente(main.app, p) as uno, cliente(main.app, p) as dos, cliente(main.app, admin) as ad:
        assert uno.get(f"/api/obras/{OBRA}").status_code == 200 and dos.get("/api/sesion").status_code == 200
        version = next(u for u in ad.get("/api/usuarios").json()["usuarios"] if u["id"] == p.id)["version"]
        r = ad.patch(f"/api/usuarios/{p.id}", json={"version": version, "activo": False})
        assert r.status_code == 200, r.text
        assert uno.get(f"/api/obras/{OBRA}").status_code == 401 and dos.get("/api/sesion").status_code == 401
        assert _entrar(uno, "persona-a").status_code == 401
        # Versión vieja -> 409; el admin no puede desactivarse a sí mismo
        assert ad.patch(f"/api/usuarios/{p.id}", json={"version": version, "activo": True}).status_code == 409
        assert ad.patch(f"/api/usuarios/{admin.id}", json={"version": 1, "activo": False}).status_code == 409
    cerradas = filas("SELECT motivo_cierre FROM sesiones WHERE usuario_id = ?", (p.id,))
    assert [f["motivo_cierre"] for f in cerradas] == ["usuario_desactivado"] * 2
    detalle = filas("SELECT detalle_json FROM auditoria WHERE accion = 'CAMBIAR_USUARIO'")[0]["detalle_json"]
    assert '"sesiones_cerradas": 2' in detalle


def test_salir_y_cierre_de_sesiones_por_el_admin(reloj):
    admin = crear_persona("admin-global", es_admin=True)
    p = crear_persona("persona-a")
    with cliente(main.app, p) as c:
        assert c.delete("/api/sesion").status_code == 200
        assert c.get("/api/sesion").status_code == 401
    with cliente(main.app, p) as uno, cliente(main.app, admin) as ad:
        assert uno.get("/api/usuarios").status_code == 403           # gestionar usuarios es solo de es_admin
        assert ad.delete(f"/api/usuarios/{p.id}/sesiones").json() == {"sesiones_cerradas": 1}
        assert uno.get("/api/sesion").status_code == 401


def test_admin_crea_usuarios_validados_sin_exponer_el_hash(reloj):
    admin = crear_persona("admin-global", es_admin=True)
    with cliente(main.app, admin) as ad:
        r = ad.post("/api/usuarios", json={"usuario": "nuevo.usuario", "nombre_visible": "Persona nueva",
                                           "contrasena": "clave-nueva-larga"})
        assert r.status_code == 201 and "hash" not in r.text
        assert ad.post("/api/usuarios", json={"usuario": "NUEVO.usuario", "nombre_visible": "x",
                                              "contrasena": "clave-nueva-larga"}).status_code == 409
        assert ad.post("/api/usuarios", json={"usuario": "x", "nombre_visible": "x",
                                              "contrasena": "clave-nueva-larga"}).status_code == 422
        assert ad.post("/api/usuarios", json={"usuario": "otro-usuario", "nombre_visible": "x",
                                              "contrasena": "corta"}).status_code == 422
        assert "hash" not in ad.get("/api/usuarios").text
    with cliente(main.app) as c:
        assert _entrar(c, "nuevo.usuario", "clave-nueva-larga").status_code == 200
