"""Regresión del módulo 1 (caudal de equipamiento) con los valores de referencia de la v3.0.0
(docs/contextoAplicativo.md, sección 7)."""
import pytest

from analisisCaudalDiseno import AnalisisCaudalDiseno

toleranciaRelativa = 1e-9


@pytest.fixture(scope="module")
def casoConagua():
    analisis = AnalisisCaudalDiseno(
        fuente="CONAGUA",
        saltoNeto=150,
        tipoTurbina="Francis",
        eficienciaTotal=0.88,
        minDiasPorPeriodo=300,
    )
    return analisis, analisis.calcular()


@pytest.fixture(scope="module")
def casoIdeam():
    analisis = AnalisisCaudalDiseno(
        fuente="IDEAM",
        saltoNeto=10,
        tipoTurbina="Kaplan",
        eficienciaTurbina=0.85,
        eficienciaGenerador=0.95,
        minDiasPorPeriodo=300,
    )
    return analisis, analisis.calcular()


def test_conaguaCaudalYEnergiaMaxima(casoConagua):
    _, resultados = casoConagua
    maximo = resultados["maximo"]
    assert maximo["CaudalEquipamiento"] == pytest.approx(238.79333333333335, rel=toleranciaRelativa)
    assert maximo["EnergiaAnual_kWh"] == pytest.approx(1516526226.2599678, rel=toleranciaRelativa)


def test_conaguaPasoPeriodosYValoresQe(casoConagua):
    analisis, resultados = casoConagua
    dfResumen = resultados["dfResumenPeriodos"]
    assert analisis.calculadora.pasoQeUtilizado == 50
    assert dfResumen.filter(dfResumen["Incluido"]).height == 25
    assert dfResumen.height == 33
    assert resultados["dfEnergia"].height == 39


def test_ideamCaudalYEnergiaMaxima(casoIdeam):
    _, resultados = casoIdeam
    maximo = resultados["maximo"]
    assert maximo["CaudalEquipamiento"] == pytest.approx(3.4717000000000002, rel=toleranciaRelativa)
    assert maximo["EnergiaAnual_kWh"] == pytest.approx(1032428.0985059995, rel=toleranciaRelativa)


def test_ideamPasoPeriodosYValoresQe(casoIdeam):
    analisis, resultados = casoIdeam
    dfResumen = resultados["dfResumenPeriodos"]
    assert analisis.calculadora.pasoQeUtilizado == pytest.approx(0.1)
    assert dfResumen.filter(dfResumen["Incluido"]).height == 20
    assert dfResumen.height == 27
    assert resultados["dfEnergia"].height == 227
