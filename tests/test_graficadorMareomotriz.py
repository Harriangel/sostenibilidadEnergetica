"""Pruebas de energias.mar.graficadorMareomotriz."""
import pytest
from matplotlib.figure import Figure

from energias.mar.graficadorMareomotriz import GraficadorMareomotriz
from energias.mar.mareomotriz import CentralMareomotriz


@pytest.fixture(scope="module")
def central():
    return CentralMareomotriz()


@pytest.fixture(scope="module")
def resultados(central):
    return central.calcular()


@pytest.mark.parametrize("unidadLcoe", ["kWh", "MWh"])
def test_figuraEscenarios(resultados, unidadLcoe):
    fig = GraficadorMareomotriz().crearFiguraEscenarios(resultados["dfEscenarios"], "EUR", unidadLcoe)
    assert isinstance(fig, Figure)
    alturas = [barra.get_height() for barra in fig.axes[0].patches]
    factor = 1000 if unidadLcoe == "MWh" else 1
    assert alturas == pytest.approx([v * factor for v in resultados["dfEscenarios"]["LCOE_EUR_por_kWh"].to_list()])


@pytest.mark.parametrize("parametro", list(CentralMareomotriz.parametrosSensibilidad))
def test_figuraSensibilidad(central, resultados, parametro):
    fig = GraficadorMareomotriz().crearFiguraSensibilidad(
        central.barridoSensibilidad(parametro),
        parametro,
        central.parametros[parametro],
        resultados["lcoeBase_porKWh"],
        "EUR",
    )
    assert isinstance(fig, Figure)
    assert "Base" in fig.axes[0].get_legend().get_texts()[0].get_text()


def test_guardarFiguras(resultados, tmp_path):
    graficador = GraficadorMareomotriz(tmp_path / "outputs" / "mareomotriz")
    fig = graficador.crearFiguraEscenarios(resultados["dfEscenarios"], "EUR")
    rutas = graficador.guardarFigura(fig, "lcoeEscenarios")
    assert [ruta.name for ruta in rutas] == ["lcoeEscenarios.png", "lcoeEscenarios.svg"]


def test_validaciones(central, resultados):
    graficador = GraficadorMareomotriz()
    with pytest.raises(ValueError):
        graficador.crearFiguraEscenarios(resultados["dfEscenarios"], "EUR", "GWh")
    with pytest.raises(ValueError):
        graficador.crearFiguraSensibilidad(central.barridoSensibilidad("capex"), "opex", 1.0, 0.07, "EUR")
    with pytest.raises(ValueError):
        graficador.guardarFigura(Figure(), "sinCarpeta")
