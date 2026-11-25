"""Pruebas de energias.solar.termica.fChartAcs (docs/especificaciones/solar/termica/fChartAcs.md, secciones 5 y 6)."""
import pytest

from energias.solar.termica.fChartAcs import SistemaFChart

toleranciaRelativa = 1e-9

# Tabla 2 del informe (inclinación de 18°, acimut original)
climaInforme = {
    "HTmes_kWhm2mes": [189.18, 193.52, 225.08, 209.54, 206.89, 179.8, 175.44, 191.28, 162.25, 177.51, 181.63, 188.05],
    "Tamb_C": [13.8, 15.3, 16.7, 19, 19.5, 18.5, 17.5, 17.4, 17, 16.5, 14.6, 12.6],
}

# Sección 5.1: tabla mensual con la correlación del informe (D1, D2, f, Qu, Qaux)
mensualInforme = [
    (0.7695, 0.5665, 0.6908, 2240.0, 1002.6), (0.8715, 0.5393, 0.7551, 2211.6, 717.2),
    (0.9155, 0.5139, 0.7802, 2530.0, 712.6), (0.8807, 0.4721, 0.7594, 2383.1, 754.9),
    (0.8415, 0.4630, 0.7351, 2383.8, 858.8), (0.7557, 0.4812, 0.6783, 2128.5, 1009.5),
    (0.7136, 0.4993, 0.6489, 2104.2, 1138.4), (0.7780, 0.5011, 0.6944, 2251.7, 990.9),
    (0.6819, 0.5084, 0.6260, 1964.5, 1173.5), (0.7220, 0.5175, 0.6558, 2126.6, 1116.0),
    (0.7634, 0.5520, 0.6862, 2153.2, 984.8), (0.7649, 0.5883, 0.6885, 2232.4, 1010.2),
]
# Sección 5.2: tabla mensual con Klein y corrección para ACS
mensualKlein = [
    (1.0058, 2.1498, 0.6776, 2197.1, 1045.5), (1.1391, 2.0672, 0.7593, 2223.9, 704.9),
    (1.1966, 1.9901, 0.7951, 2578.3, 664.3), (1.1512, 1.8635, 0.7778, 2440.7, 697.3),
    (1.0999, 1.8360, 0.7508, 2434.4, 808.2), (0.9878, 1.8910, 0.6816, 2138.9, 999.1),
    (0.9327, 1.9461, 0.6444, 2089.5, 1153.1), (1.0169, 1.9516, 0.6957, 2255.8, 986.8),
    (0.8914, 1.9736, 0.6165, 1934.6, 1203.4), (0.9437, 2.0012, 0.6481, 2101.5, 1141.1),
    (0.9978, 2.1058, 0.6753, 2119.1, 1018.9), (0.9998, 2.2159, 0.6702, 2173.1, 1069.5),
]


@pytest.fixture(scope="module")
def informe():
    return SistemaFChart(climaInforme, correlacion="informe").calcular()


@pytest.fixture(scope="module")
def klein():
    return SistemaFChart(climaInforme).calcular()


def compararMensual(dfMensual, esperado):
    for fila, (d1, d2, f, qu, qaux) in zip(dfMensual.iter_rows(named=True), esperado):
        assert round(fila["D1"], 4) == d1
        assert round(fila["D2"], 4) == d2
        assert round(fila["FraccionSolar"], 4) == f
        assert round(fila["Qu_kWhmes"], 1) == qu
        assert round(fila["Qaux_kWhmes"], 1) == qaux


# ----------------------------------------------------------------------
# Demanda y área inicial
# ----------------------------------------------------------------------
def test_demanda(informe):
    assert informe["volumenDiario_L"] == 3000
    assert informe["demandaDiaria_kWh"] == pytest.approx(104.6, rel=toleranciaRelativa)
    assert informe["demandaAnual_kWh"] == pytest.approx(38179.0, rel=toleranciaRelativa)
    assert [round(q, 1) for q in informe["dfDemanda"]["Qm_kWhmes"].to_list()[:3]] == [3242.6, 2928.8, 3242.6]
    assert round(informe["dfDemanda"]["Qm_kWhmes"][3], 1) == 3138.0


def test_areaInicial(informe, klein):
    assert informe["areaInicial_m2"] == pytest.approx(24.185672315855594, rel=toleranciaRelativa)
    assert klein["areaInicial_m2"] == pytest.approx(24.185672315855594, rel=toleranciaRelativa)


# ----------------------------------------------------------------------
# Correlación del informe (sección 5.1)
# ----------------------------------------------------------------------
def test_informeDimensionamiento(informe):
    resultado = informe["dimensionamiento"]
    assert resultado["converge"]
    assert resultado["iteraciones"] == 67
    assert resultado["area_m2"] == pytest.approx(17.5856723158555, rel=toleranciaRelativa)
    assert resultado["fraccionAnual"] == pytest.approx(0.6995920204795473, rel=toleranciaRelativa)
    assert resultado["numeroColectores"] == 9
    assert resultado["areaInstalada_m2"] == 18
    assert resultado["energiaSolarAnual_kWh"] == pytest.approx(26709.723749888642, rel=toleranciaRelativa)
    assert resultado["energiaAuxiliarAnual_kWh"] == pytest.approx(11469.276250111361, rel=toleranciaRelativa)
    assert resultado["advertencias"] == []


def test_informeMensual(informe):
    compararMensual(informe["dimensionamiento"]["dfMensual"], mensualInforme)


def test_informeCasos(informe):
    casos = {fila["Caso"]: fila for fila in informe["dfCasos"].iter_rows(named=True)}
    esperado = {
        "Representativo": ("Enero", 24.1857, 1.0583, 0.7791, 0.8517),
        "Subdimensionado": ("Marzo", 10.5647, 0.5500, 0.3087, 0.5061),
        "Sobredimensionado": ("Septiembre", 42.9789, 1.6667, 1.2425, 0.9813),
    }
    for caso, (mes, area, d1, d2, f) in esperado.items():
        fila = casos[caso]
        assert fila["Mes"] == mes
        assert (round(fila["Area_m2"], 4), round(fila["D1"], 4), round(fila["D2"], 4), round(fila["FraccionSolar"], 4)) == (area, d1, d2, f)


def test_informeFraccionAreaInicial(informe):
    assert informe["fraccionAreaInicial"] == pytest.approx(0.8581201767963327, rel=toleranciaRelativa)


# ----------------------------------------------------------------------
# Klein con corrección para ACS (sección 5.2)
# ----------------------------------------------------------------------
def test_kleinDimensionamiento(klein):
    resultado = klein["dimensionamiento"]
    assert resultado["converge"]
    assert resultado["iteraciones"] == 13
    assert resultado["area_m2"] == pytest.approx(22.985672315855577, rel=toleranciaRelativa)
    assert resultado["fraccionAnual"] == pytest.approx(0.6989916074842719, rel=toleranciaRelativa)
    assert resultado["numeroColectores"] == 12
    assert resultado["energiaSolarAnual_kWh"] == pytest.approx(26686.800582142023, rel=toleranciaRelativa)
    assert resultado["energiaAuxiliarAnual_kWh"] == pytest.approx(11492.199417857983, rel=toleranciaRelativa)
    assert resultado["advertencias"] == []


def test_kleinMensual(klein):
    compararMensual(klein["dimensionamiento"]["dfMensual"], mensualKlein)


def test_kleinCasos(klein):
    casos = {fila["Caso"]: fila for fila in klein["dfCasos"].iter_rows(named=True)}
    esperado = {"Representativo": (2.2620, 0.7022), "Subdimensionado": (0.9147, 0.4375), "Sobredimensionado": (3.6903, 0.9186)}
    for caso, (d2, f) in esperado.items():
        assert (round(casos[caso]["D2"], 4), round(casos[caso]["FraccionSolar"], 4)) == (d2, f)


def test_kleinFraccionAreaInicial(klein):
    assert klein["fraccionAreaInicial"] == pytest.approx(0.7242100831362482, rel=toleranciaRelativa)


def test_variantesConLaMismaArea():
    """Con 17,59 m²: Klein con corrección para ACS 0,573; sin corrección y con Tref = Tw (45 − Tamb) 0,635."""
    assert SistemaFChart(climaInforme).fraccionAnual(17.59) == pytest.approx(0.573, abs=5e-4)
    conTw = SistemaFChart(climaInforme, correccionAcs=False, temperaturaReferencia=45)
    assert conTw.fraccionAnual(17.59) == pytest.approx(0.635, abs=5e-4)


# ----------------------------------------------------------------------
# Casos borde y validaciones
# ----------------------------------------------------------------------
@pytest.mark.parametrize("correlacion", SistemaFChart.correlaciones)
def test_areaCeroSinFraccion(correlacion):
    sistema = SistemaFChart(climaInforme, correlacion=correlacion)
    assert sistema.calcularMensual(0)["FraccionSolar"].abs().max() == 0
    assert sistema.fraccionAnual(0) == 0


@pytest.mark.parametrize("correlacion", SistemaFChart.correlaciones)
def test_fraccionEntreCeroYUno(correlacion):
    curva = SistemaFChart(climaInforme, correlacion=correlacion).curvaFraccionArea()
    assert curva["FraccionAnual"].min() >= 0
    assert curva["FraccionAnual"].max() <= 1
    assert curva["FraccionAnual"].is_sorted()


def test_sinConvergenciaAdvierte():
    resultado = SistemaFChart(climaInforme, fraccionObjetivoMinima=0.65, fraccionObjetivoMaxima=0.65, maxIteraciones=50).dimensionar()
    assert not resultado["converge"]
    assert resultado["iteraciones"] == 50
    assert "iteraciones" in resultado["advertencias"][0]


def test_kleinFueraDeRangoAdvierte():
    resultado = SistemaFChart(climaInforme).calcularMensual(200)
    assert SistemaFChart(climaInforme).advertenciasRango(resultado)


def test_aceptaDataFrameDelRecursoSolar():
    import polars as pl

    df = pl.DataFrame(climaInforme)
    assert SistemaFChart(df).areaInicial() == pytest.approx(24.185672315855594, rel=toleranciaRelativa)


@pytest.mark.parametrize(
    "parametros",
    [
        {"temperaturaUso": 15},
        {"eficienciaOptica": 0},
        {"eficienciaOptica": 1.1},
        {"coeficientePerdidas": -1},
        {"fraccionObjetivoMinima": 0.8},
        {"eficienciaSistema": 0},
        {"correlacion": "polinomica"},
        {"numeroHabitaciones": 0},
        {"areaColector": 0},
    ],
)
def test_validaciones(parametros):
    with pytest.raises(ValueError):
        SistemaFChart(climaInforme, **parametros)


def test_climaInvalido():
    with pytest.raises(ValueError):
        SistemaFChart({"HTmes_kWhm2mes": [190] * 11, "Tamb_C": [15] * 11})
    with pytest.raises(ValueError):
        SistemaFChart({"HTmes_kWhm2mes": [0] + [190] * 11, "Tamb_C": [15] * 12})

