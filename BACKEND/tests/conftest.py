# Fundación F2: configuración común de las pruebas.
#
# La API exige sesión y permiso por obra en toda ruta (identidad/guardia.py). Las pruebas ANTERIORES a F2 prueban
# la lógica de cada módulo, no la identidad: para ellas, y solo aquí, la guardia se sustituye por un usuario de
# pruebas ('steven', sin id) que ve todas las obras. El código de producción no tiene ningún atajo.
#
# Las pruebas de F2 llevan la marca `seguridad_real` y usan la guardia verdadera, con usuarios, sesiones,
# membresías y encabezados reales (tests/f2_ayudas.py). Ahí se prueba que TODA ruta pasa por el permiso.
import pytest

MARCA = "seguridad_real"


def pytest_configure(config):
    config.addinivalue_line("markers", f"{MARCA}: usa la guardia real de la API (sesión y permisos de F2)")


@pytest.fixture(autouse=True)
def _guardia_de_pruebas(request, monkeypatch):
    monkeypatch.setenv("CATDIC_HOSTS_PERMITIDOS", "testserver")   # el nombre de servidor de TestClient
    if request.node.get_closest_marker(MARCA):
        yield
        return
    import main
    from identidad import contexto, guardia, permisos

    usuario = contexto.Usuario(None, "steven", "Pruebas anteriores a F2", True)

    async def guardia_pruebas():
        contexto.fijar(usuario)

    def todas_las_obras(conn, _usuario, _funcion="consultar"):
        return {f[0] for f in conn.execute("SELECT id FROM proyectos")}

    main.app.dependency_overrides[guardia.guardia] = guardia_pruebas
    monkeypatch.setattr(permisos, "obras_con", todas_las_obras)
    try:
        yield
    finally:
        main.app.dependency_overrides.pop(guardia.guardia, None)
