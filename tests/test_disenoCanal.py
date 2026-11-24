"""Regresión del módulo 2 (canal de derivación) con los valores de referencia de la v3.0.0."""
import pytest

from disenoCanal import DisenoCanal

toleranciaRelativa = 1e-9


@pytest.fixture
def canal():
    pendiente = DisenoCanal.calcularPendiente(cotaAguasArriba=1.1, cotaAguasAbajo=1.0, longitud=100)
    return DisenoCanal(coeficienteManning=0.014, pendiente=pendiente)


def test_verificarSeccion(canal):
    seccion = canal.evaluarSeccion(x=5.2, y=1.2, z=1.0)
    assert seccion["Q"] == pytest.approx(4.9350418541031935, rel=toleranciaRelativa)
    assert seccion["v"] == pytest.approx(1.542200579407248, rel=toleranciaRelativa)
    assert seccion["Pm"] == pytest.approx(5.67213595499958, rel=toleranciaRelativa)
    assert seccion["Rh"] == pytest.approx(0.5641613715516516, rel=toleranciaRelativa)
    assert seccion["Froude"] == pytest.approx(0.6279925718620699, rel=toleranciaRelativa)


def test_dimensionarParaCaudal(canal):
    seccion = canal.dimensionarParaCaudal(caudalDiseno=4.9350418541031935, base=1.2, talud=2)
    assert seccion["z"] == pytest.approx(1.0, rel=toleranciaRelativa)
