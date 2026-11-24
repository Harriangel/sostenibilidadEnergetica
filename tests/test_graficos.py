"""Pruebas de energias.comun.graficos."""
import pytest
from matplotlib.figure import Figure

from energias.comun.graficos import Graficos


@pytest.fixture
def figura():
    fig = Figure(figsize=(3, 2))
    ax = fig.subplots()
    ax.plot([0, 1, 2], [0, 1000, 4000])
    return fig


def test_guardarFigura(figura, tmp_path):
    rutas = Graficos.guardarFigura(figura, tmp_path / "salidas", "prueba")
    assert [ruta.name for ruta in rutas] == ["prueba.png", "prueba.svg"]
    assert all(ruta.stat().st_size > 0 for ruta in rutas)


def test_figuraABytes(figura):
    contenido = Graficos.figuraABytesTodos(figura)
    assert contenido["png"].startswith(b"\x89PNG")
    assert b"<svg" in contenido["svg"]


def test_formatoInvalido(figura):
    with pytest.raises(ValueError):
        Graficos.figuraABytes(figura, "jpg")


def test_formatosDeEje():
    assert Graficos.formatoMiles()(1234567.4, 0) == "1,234,567"
    assert Graficos.formatoGeneral()(0.5, 0) == "0.5"
    assert Graficos.formatoComaDecimal()(0.02, 0) == "0,02"
    assert Graficos.formatoDecimales(2)(1234.567, 0) == "1,234.57"
