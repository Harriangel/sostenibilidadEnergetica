"""Regresión del módulo 3 (tubería forzada) y de Colebrook con los valores de referencia de la v3.0.0."""
import pytest

from disenoTuberiaForzada import DisenoTuberiaForzada

toleranciaRelativa = 1e-9


def test_diametroEconomicoTolerancia5Porciento():
    tuberia = DisenoTuberiaForzada(rugosidadMm=0.2, eficienciaGlobal=0.9)
    iteracion = tuberia.iterarDiametro(0.5)
    assert iteracion["converge"]
    assert iteracion["iteraciones"] == 3
    assert iteracion["resultado"]["diametro"] == pytest.approx(0.8342021876785625, rel=toleranciaRelativa)


def test_diametroEconomicoConvergido():
    tuberia = DisenoTuberiaForzada(rugosidadMm=0.2, eficienciaGlobal=0.9, tolerancia=1e-9)
    resultado = tuberia.iterarDiametro(0.5)["resultado"]
    assert resultado["diametro"] == pytest.approx(0.829721252601844, rel=toleranciaRelativa)
    assert resultado["factorFriccion"] == pytest.approx(0.015330366062117984, rel=toleranciaRelativa)


def test_colebrook():
    factor = DisenoTuberiaForzada.friccionColebrook(250000, 0.002)
    assert factor == pytest.approx(0.024139763482553166, rel=toleranciaRelativa)
