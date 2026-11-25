"""Pruebas de energias.solar.graficadorSolar."""
from pathlib import Path

import pytest
from matplotlib.figure import Figure

from energias.solar.fotovoltaica.horasSolaresPico import SistemaFotovoltaicoHsp
from energias.solar.graficadorSolar import GraficadorSolar
from energias.solar.recursoSolar import RecursoSolar
from energias.solar.termica.fChartAcs import SistemaFChart

rutaTmy = Path(__file__).resolve().parent.parent / "data" / "solar" / "tmyCiudadMexico.csv"


@pytest.fixture(scope="module")
def datos():
    recurso = RecursoSolar(rutaTmy)
    plano = recurso.calcularPlano(19)
    mensual = recurso.radiacionMensual(19)
    sistema = SistemaFChart(mensual)
    return {
        "recurso": recurso,
        "plano": plano,
        "mensual": mensual,
        "sistema": sistema,
        "dimensionamiento": sistema.dimensionar(),
    }


def test_figurasRecurso(datos):
    graficador = GraficadorSolar()
    recurso, plano = datos["recurso"], datos["plano"]
    figuras = [
        graficador.crearFiguraPerfilHorario(recurso.perfilHorario(plano), list(RecursoSolar.componentesInclinadas), "Perfil"),
        graficador.crearFiguraPerfilHorarioMensual(recurso.perfilHorario(plano, porMes=True), "GTI_Wm2"),
        graficador.crearFiguraRadiacionDiaria(recurso.radiacionDiaria(plano), ["GTI_kWhm2dia"]),
        graficador.crearFiguraRadiacionMensual(datos["mensual"], 19),
        graficador.crearFiguraBarridoInclinacion(recurso.barridoInclinacion(range(0, 91, 10)), 19, {"Latitud + 23,5°": 42.95}),
    ]
    assert all(isinstance(fig, Figure) for fig in figuras)
    assert len(figuras[1].axes[0].lines) == 12


def test_figurasFChart(datos):
    graficador = GraficadorSolar()
    dimensionamiento = datos["dimensionamiento"]
    fig = graficador.crearFiguraFChartMensual(dimensionamiento["dfMensual"])
    alturas = [barra.get_height() for barra in fig.axes[0].patches]
    assert sum(alturas) == pytest.approx(datos["sistema"].demandaMensual.sum())
    fig = graficador.crearFiguraFraccionArea(
        datos["sistema"].curvaFraccionArea(), dimensionamiento["area_m2"], dimensionamiento["fraccionAnual"], 0.6, 0.7
    )
    assert isinstance(fig, Figure)


@pytest.mark.parametrize("unidad", ["kWh", "MWh"])
def test_figuraFotovoltaica(unidad):
    df = SistemaFotovoltaicoHsp(unidadEnergia=unidad).calcularMensual()
    fig = GraficadorSolar().crearFiguraEnergiaFotovoltaica(df, unidad)
    assert [barra.get_height() for barra in fig.axes[0].patches] == pytest.approx(df[f"Energia_{unidad}mes"].to_list())


def test_guardarFigura(datos, tmp_path):
    graficador = GraficadorSolar(tmp_path / "outputs" / "solar")
    rutas = graficador.guardarFigura(graficador.crearFiguraRadiacionMensual(datos["mensual"], 19), "radiacionMensual")
    assert [ruta.name for ruta in rutas] == ["radiacionMensual.png", "radiacionMensual.svg"]
    with pytest.raises(ValueError):
        GraficadorSolar().guardarFigura(Figure(), "sinCarpeta")
