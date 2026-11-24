"""Pruebas de energias.comun.economia (valores de docs/especificaciones/mar/Calculo_mareomotriz_LCOE.md, §3.3)."""
import pytest

from energias.comun.economia import IndicadoresEconomicos

toleranciaRelativa = 1e-9
energiaUtilKWh = 22911539.80645161  # K21 del Excel de la mareomotriz


@pytest.fixture
def indicadores():
    return IndicadoresEconomicos(tasaDescuento=0.07, vidaUtil=25)


def test_factorValorPresente(indicadores):
    assert indicadores.factorValorPresente() == pytest.approx(11.653583, abs=1e-6)
    assert indicadores.factorValorPresente() == pytest.approx((1 - 1.07**-25) / 0.07, rel=toleranciaRelativa)


def test_factorRecuperacionCapital(indicadores):
    assert indicadores.factorRecuperacionCapital() == pytest.approx(0.0858105, abs=1e-7)
    assert indicadores.factorRecuperacionCapital() * indicadores.factorValorPresente() == pytest.approx(1.0)


def test_valoresPresentes(indicadores):
    assert indicadores.valorPresenteCostos(14_500_000, 450_000) == pytest.approx(19744112.43, abs=0.01)
    assert indicadores.valorPresenteEnergia(energiaUtilKWh) == pytest.approx(267001534.88, abs=0.01)


def test_lcoe(indicadores):
    assert indicadores.lcoe(14_500_000, 450_000, energiaUtilKWh) == pytest.approx(0.07394756153502048, rel=toleranciaRelativa)


def test_lcoeEquivaleAAnualidadConCrf(indicadores):
    """El LCOE por valor presente es igual a (CAPEX·CRF + OPEX) / E."""
    anualidad = 14_500_000 * indicadores.factorRecuperacionCapital() + 450_000
    assert indicadores.lcoe(14_500_000, 450_000, energiaUtilKWh) == pytest.approx(anualidad / energiaUtilKWh, rel=toleranciaRelativa)


def test_tasaCero():
    indicadores = IndicadoresEconomicos(tasaDescuento=0.0, vidaUtil=25)
    assert indicadores.factorValorPresente() == 25.0
    assert indicadores.factorRecuperacionCapital() == pytest.approx(0.04)
    assert indicadores.lcoe(100.0, 2.0, 10.0) == pytest.approx((100 + 2 * 25) / (10 * 25))


@pytest.mark.parametrize("vidaUtil", [0, -5])
def test_vidaUtilInvalida(vidaUtil):
    with pytest.raises(ValueError):
        IndicadoresEconomicos(tasaDescuento=0.07, vidaUtil=vidaUtil)


def test_tasaNegativa():
    with pytest.raises(ValueError):
        IndicadoresEconomicos(tasaDescuento=-0.01, vidaUtil=25)


def test_energiaYCostosInvalidos(indicadores):
    with pytest.raises(ValueError):
        indicadores.lcoe(14_500_000, 450_000, 0.0)
    with pytest.raises(ValueError):
        indicadores.valorPresenteCostos(-1.0, 450_000)
