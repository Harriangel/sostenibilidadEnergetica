"""Pruebas de energias.comun.unidades."""
import pytest

from energias.comun.unidades import Unidades


def test_factoresPotencia():
    assert Unidades.factorPotencia("W") == 1.0
    assert Unidades.factorPotencia("kW") == 1e-3
    assert Unidades.factorPotencia("MW") == 1e-6
    assert Unidades.factorPotencia("GW") == 1e-9


def test_listasDeUnidades():
    assert Unidades.unidadesPotencia() == ["W", "kW", "MW", "GW"]
    assert Unidades.unidadesEnergia() == ["Wh", "kWh", "MWh", "GWh"]


def test_convertirEnergia():
    assert Unidades.convertirEnergia(1.0, "GWh", "kWh") == pytest.approx(1e6)
    assert Unidades.convertirEnergia(2500.0, "kWh", "MWh") == pytest.approx(2.5)


def test_joulesYVatiosHora():
    assert Unidades.joulesAWh(3600.0) == 1.0
    assert Unidades.whAJoules(1.0) == 3600.0
    assert Unidades.joulesAWh(Unidades.whAJoules(123.4)) == pytest.approx(123.4)


@pytest.mark.parametrize("unidad", ["kw", "TW", ""])
def test_unidadPotenciaInvalida(unidad):
    with pytest.raises(ValueError):
        Unidades.factorPotencia(unidad)


@pytest.mark.parametrize("unidad", ["kW", "TWh", "kwh"])
def test_unidadEnergiaInvalida(unidad):
    with pytest.raises(ValueError):
        Unidades.factorEnergia(unidad)
