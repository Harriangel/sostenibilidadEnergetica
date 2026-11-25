"""Pruebas de energias.solar.fotovoltaica.horasSolaresPico
(docs/especificaciones/solar/fotovoltaica/horasSolaresPico.md, secciones 2.3 y 5)."""
from pathlib import Path

import pytest

from energias.solar.fotovoltaica.horasSolaresPico import SistemaFotovoltaicoHsp
from energias.solar.recursoSolar import RecursoSolar

toleranciaRelativa = 1e-9

# Sección 2.3: (Hm, Em, Ym)
mensualEsperado = [
    (152.6316, 656.31588, 131.263176), (136.1752, 585.55336, 117.110672), (139.8038, 601.15634, 120.231268),
    (133.6260, 574.59180, 114.918360), (138.7715, 596.71745, 119.343490), (135.1080, 580.96440, 116.192880),
    (142.1846, 611.39378, 122.278756), (143.5982, 617.47226, 123.494452), (145.9800, 627.71400, 125.542800),
    (146.0255, 627.90965, 125.581930), (135.2100, 581.40300, 116.280600), (144.0167, 619.27181, 123.854362),
]


@pytest.fixture(scope="module")
def resultados():
    return SistemaFotovoltaicoHsp().calcular()


def test_mensual(resultados):
    df = resultados["dfMensual"]
    for fila, (hm, em, ym) in zip(df.iter_rows(named=True), mensualEsperado):
        assert fila["RadiacionMensual_kWhm2mes"] == pytest.approx(hm, rel=toleranciaRelativa)
        assert fila["Energia_kWhmes"] == pytest.approx(em, rel=toleranciaRelativa)
        assert fila["Rendimiento_kWhkWpmes"] == pytest.approx(ym, rel=toleranciaRelativa)


def test_anual(resultados):
    assert resultados["radiacionMaxima_kWhm2dia"] == 4.9236
    assert resultados["radiacionMinima_kWhm2dia"] == 4.4542
    assert resultados["radiacionAnual_kWhm2"] == pytest.approx(1693.1311, rel=toleranciaRelativa)
    assert resultados["energiaAnual_kWh"] == pytest.approx(7280.46373, rel=toleranciaRelativa)
    assert resultados["promedioDiario_kWh"] == pytest.approx(19.946475972602737, rel=toleranciaRelativa)
    assert resultados["rendimientoAnual_kWhkWp"] == pytest.approx(1456.092746, rel=toleranciaRelativa)
    assert resultados["factorPlanta"] == pytest.approx(0.16622063310502283, rel=toleranciaRelativa)
    assert resultados["rendimientoGlobal"] == pytest.approx(0.86)


def test_eficienciaInversor(resultados):
    conInversor = SistemaFotovoltaicoHsp(eficienciaInversor=0.96).calcular()
    assert conInversor["energiaAnual_kWh"] == pytest.approx(0.96 * resultados["energiaAnual_kWh"], rel=toleranciaRelativa)


def test_unidadEnergia(resultados):
    enMWh = SistemaFotovoltaicoHsp(unidadEnergia="MWh").calcular()
    assert enMWh["energiaAnual"] == pytest.approx(7.28046373, rel=toleranciaRelativa)
    assert "Energia_MWhmes" in enMWh["dfMensual"].columns
    assert enMWh["energiaAnual_kWh"] == pytest.approx(resultados["energiaAnual_kWh"], rel=toleranciaRelativa)


def test_desdeRecursoSolar():
    """Con el TMY y la inclinación óptima, la radiación anual es la del recurso solar (2.287,66 kWh/m²)."""
    recurso = RecursoSolar(Path(__file__).resolve().parent.parent / "data" / "solar" / "tmyCiudadMexico.csv")
    resultados = SistemaFotovoltaicoHsp.desdeRecursoSolar(recurso, 19, potenciaNominal=5).calcular()
    assert resultados["radiacionAnual_kWhm2"] == pytest.approx(2287.663821134124, rel=toleranciaRelativa)
    assert resultados["energiaAnual_kWh"] == pytest.approx(2287.663821134124 * 5 * 0.86, rel=toleranciaRelativa)


@pytest.mark.parametrize(
    "parametros",
    [
        {"potenciaNominal": 0},
        {"perdidasSistema": 1},
        {"perdidasSistema": -0.1},
        {"eficienciaInversor": 0},
        {"eficienciaInversor": 1.01},
        {"radiacionDiaria": [5] * 11},
        {"radiacionDiaria": [-1] + [5] * 11},
        {"unidadEnergia": "TWh"},
    ],
)
def test_validaciones(parametros):
    with pytest.raises(ValueError):
        SistemaFotovoltaicoHsp(**parametros)
