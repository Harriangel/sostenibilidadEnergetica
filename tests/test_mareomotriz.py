"""Pruebas de energias.mar.mareomotriz con los valores de la especificación
docs/especificaciones/mar/Calculo_mareomotriz_LCOE.md (secciones 4 y 6)."""
import math

import pytest

from energias.mar.mareomotriz import CentralMareomotriz

toleranciaRelativa = 1e-9

# Sección 6 de la especificación, con los nombres en camelCase de la clase
esperado = {
    "cicloMarea_h": 12.4,  # K12
    "ciclosPorDia": 1.9354838709677418,  # K13
    "ciclosPorAnio": 706.4516129032257,  # K14
    "pasosPorAnio": 1412.9032258064515,  # K15
    "energiaPotencial_J": 217056692903225.8,  # K19
    "energiaPotencial_kWh": 60293525.80645161,  # K20
    "energiaUtil_kWh": 22911539.80645161,  # K21
    "energiaUtil_MWh": 22911.539806451612,  # K23
    "energiaUtil_GWh": 22.91153980645161,  # K24
    "lcoeBase_porKWh": 0.07394756153502048,  # K30
    "lcoeEscenarioA_porKWh": 0.08209358212253212,  # K35
    "lcoeEscenarioB_porKWh": 0.08216395726113387,  # K40
}


@pytest.fixture(scope="module")
def resultadosBase():
    return CentralMareomotriz().calcular()


# ----------------------------------------------------------------------
# Reproducción del Excel
# ----------------------------------------------------------------------
@pytest.mark.parametrize("clave", list(esperado))
def test_reproduceExcel(resultadosBase, clave):
    assert math.isclose(resultadosBase[clave], esperado[clave], rel_tol=toleranciaRelativa), clave


def test_intermediosValorPresente(resultadosBase):
    """Intermedios de la sección 3.3 (dados con 2 o 6 decimales en la especificación)."""
    assert resultadosBase["factorValorPresente"] == pytest.approx(11.653583, abs=1e-6)
    assert resultadosBase["factorRecuperacionCapital"] == pytest.approx(0.0858105, abs=1e-7)
    assert resultadosBase["valorPresenteOpex"] == pytest.approx(5244112.43, abs=0.01)
    assert resultadosBase["valorPresenteCostos"] == pytest.approx(19744112.43, abs=0.01)
    assert resultadosBase["valorPresenteEnergia_kWh"] == pytest.approx(267001534.88, abs=0.01)


def test_tablaEscenarios(resultadosBase):
    """Tabla de la sección 3.4."""
    df = resultadosBase["dfEscenarios"]
    assert df["Escenario"].to_list() == ["Base", "A", "B"]
    assert df["ValorPresenteCostos_EUR"].to_list() == pytest.approx([19744112.43, 21919112.43, 19744112.43], abs=0.01)
    assert df["ValorPresenteEnergia_kWh"].to_list() == pytest.approx([267001534.88, 267001534.88, 240301381.39], abs=0.01)
    assert df["LCOE_EUR_por_kWh"].to_list() == pytest.approx(
        [esperado["lcoeBase_porKWh"], esperado["lcoeEscenarioA_porKWh"], esperado["lcoeEscenarioB_porKWh"]],
        rel=toleranciaRelativa,
    )
    assert df["LCOE_EUR_por_MWh"][0] == pytest.approx(73.94756153502048, rel=toleranciaRelativa)
    assert df["VariacionFrenteBase_pct"].to_list() == pytest.approx([0.0, 11.02, 11.11], abs=0.005)


def test_potenciaMedia(resultadosBase):
    assert resultadosBase["potenciaMedia_MW"] == pytest.approx(esperado["energiaUtil_kWh"] / 1e3 / 8760, rel=toleranciaRelativa)


def test_monedaEsEtiqueta():
    resultados = CentralMareomotriz(moneda="USD").calcular()
    assert resultados["lcoeBase_porKWh"] == pytest.approx(esperado["lcoeBase_porKWh"], rel=toleranciaRelativa)
    assert "LCOE_USD_por_kWh" in resultados["dfEscenarios"].columns


# ----------------------------------------------------------------------
# Casos borde
# ----------------------------------------------------------------------
def test_unidireccionalMitadDePasos(resultadosBase):
    resultados = CentralMareomotriz(direccion="Unidireccional").calcular()
    assert math.isclose(resultados["pasosPorAnio"], esperado["pasosPorAnio"] / 2, rel_tol=toleranciaRelativa)
    assert math.isclose(resultados["energiaUtil_kWh"], esperado["energiaUtil_kWh"] / 2, rel_tol=toleranciaRelativa)


def test_mareaDiurnaCicloDe24_8Horas():
    assert math.isclose(CentralMareomotriz(tipoMarea="Diurna").calcular()["cicloMarea_h"], 24.8)


def test_tasaCero():
    resultados = CentralMareomotriz(tasaDescuento=0.0).calcular()
    assert resultados["factorValorPresente"] == 25.0
    lcoeEsperado = (14_500_000 + 450_000 * 25) / (esperado["energiaUtil_kWh"] * 25)
    assert resultados["lcoeBase_porKWh"] == pytest.approx(lcoeEsperado, rel=toleranciaRelativa)


@pytest.mark.parametrize("tipoMarea", ["semidiurna", "SEMIDIURNA", "  Semidiurna "])
@pytest.mark.parametrize("direccion", ["bidireccional", "BIDIRECCIONAL", "Bidireccionál"])
def test_textoSinDistinguirMayusculasNiTildes(tipoMarea, direccion):
    resultados = CentralMareomotriz(tipoMarea=tipoMarea, direccion=direccion).calcular()
    assert math.isclose(resultados["pasosPorAnio"], esperado["pasosPorAnio"], rel_tol=toleranciaRelativa)


# ----------------------------------------------------------------------
# Validaciones
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "parametros",
    [
        {"tipoMarea": "Mixta"},
        {"tipoMarea": ""},
        {"direccion": "Tridireccional"},
        {"eficiencia": 0.0},
        {"eficiencia": 1.2},
        {"eficiencia": -0.3},
        {"masaAgua": 0.0},
        {"masaAgua": -1.0},
        {"desnivel": 0.0},
        {"desnivel": -3.6},
        {"vidaUtil": 0},
        {"tasaDescuento": -0.01},
        {"numeroTurbinas": 0},
        {"numeroTurbinas": 2.5},
        {"disponibilidad": 0.0},
        {"disponibilidad": 1.1},
        {"capex": -1.0},
    ],
)
def test_validaciones(parametros):
    with pytest.raises(ValueError):
        CentralMareomotriz(**parametros)


# ----------------------------------------------------------------------
# Ampliaciones (sección 7 de la especificación)
# ----------------------------------------------------------------------
def test_tresTurbinasTriplicanEnergiaYDejanIgualElLcoe(resultadosBase):
    resultados = CentralMareomotriz(numeroTurbinas=3).calcular()
    assert resultados["pasosPorAnio"] == pytest.approx(esperado["pasosPorAnio"], rel=toleranciaRelativa)  # por turbina
    assert resultados["energiaUtil_kWh"] == pytest.approx(3 * esperado["energiaUtil_kWh"], rel=toleranciaRelativa)
    assert resultados["capexTotal"] == pytest.approx(3 * 14_500_000)
    assert resultados["lcoeBase_porKWh"] == pytest.approx(esperado["lcoeBase_porKWh"], rel=toleranciaRelativa)


def test_disponibilidadIgualAlEscenarioB():
    resultados = CentralMareomotriz(disponibilidad=0.9).calcular()
    assert resultados["lcoeBase_porKWh"] == pytest.approx(esperado["lcoeEscenarioB_porKWh"], rel=toleranciaRelativa)


# ----------------------------------------------------------------------
# Sensibilidad
# ----------------------------------------------------------------------
@pytest.mark.parametrize("parametro", list(CentralMareomotriz.parametrosSensibilidad))
def test_barridoIncluyeElValorBase(parametro):
    central = CentralMareomotriz()
    df = central.barridoSensibilidad(parametro)
    fila = df.filter(df[parametro] == float(central.parametros[parametro]))
    assert fila.height == 1
    assert fila["LCOE_EUR_por_kWh"][0] == pytest.approx(esperado["lcoeBase_porKWh"], rel=toleranciaRelativa)


def test_barridoMonotono():
    central = CentralMareomotriz()
    assert central.barridoSensibilidad("capex")["LCOE_EUR_por_kWh"].is_sorted()
    assert central.barridoSensibilidad("tasaDescuento")["LCOE_EUR_por_kWh"].is_sorted()
    assert central.barridoSensibilidad("eficiencia")["LCOE_EUR_por_kWh"].is_sorted(descending=True)


def test_parametroSensibilidadInvalido():
    with pytest.raises(ValueError):
        CentralMareomotriz().barridoSensibilidad("opex")
