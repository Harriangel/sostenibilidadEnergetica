"""Pruebas de energias.solar.recursoSolar (docs/especificaciones/solar/recursoSolar.md, secciones 6 y 7)."""
from pathlib import Path

import numpy as np
import pytest

from energias.solar.recursoSolar import LectorTmy, PosicionSolar, RecursoSolar

toleranciaRelativa = 1e-9
rutaTmy = Path(__file__).resolve().parent.parent / "data" / "solar" / "tmyCiudadMexico.csv"

# Radiación anual en el plano (Wh/m²·año), sección 6.2
radiacionAnualEsperada = {
    0: 2193006.4656910943,
    18: 2287430.537328812,
    19: 2287663.821134124,
    20: 2287358.108851803,
    30: 2255036.124906734,
    42.95: 2135470.319068133,
    43: 2134843.9896685863,
}

# Sección 6.3: inclinación de 19°
mensualEsperado = [
    # (HTdia, HTmes, Tamb)
    (6.179, 191.55, 13.81), (7.002, 196.06, 15.32), (7.297, 226.19, 16.71), (6.995, 209.84, 19.02),
    (6.656, 206.35, 19.54), (5.959, 178.78, 18.45), (5.628, 174.48, 17.50), (6.141, 190.36, 17.43),
    (5.403, 162.09, 16.95), (5.744, 178.06, 16.45), (6.093, 182.79, 14.61), (6.166, 191.13, 12.60),
]


@pytest.fixture(scope="module")
def recurso():
    return RecursoSolar(rutaTmy)


# ----------------------------------------------------------------------
# Lector
# ----------------------------------------------------------------------
def test_lectorMetadatosYRegistros():
    metadatos, df = LectorTmy(rutaTmy).leer()
    assert metadatos == {"latitud": 19.45, "longitud": -99.14, "zonaHoraria": -6.0, "elevacion": 2240.0}
    assert df.height == 8760
    assert df["Minuto"].unique().to_list() == [30]


def escribirTmyRecortado(tmp_path, quitarColumna=None, quitarRegistros=0) -> Path:
    lineas = rutaTmy.read_text(encoding="utf-8").splitlines()
    if quitarColumna is not None:
        encabezados = lineas[2].split(",")
        indice = encabezados.index(quitarColumna)
        lineas = lineas[:2] + [",".join(v for i, v in enumerate(l.split(",")) if i != indice) for l in lineas[2:]]
    if quitarRegistros:
        lineas = lineas[:-quitarRegistros]
    ruta = tmp_path / "tmy.csv"
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta


def test_lectorSinColumna(tmp_path):
    with pytest.raises(ValueError, match="DNI"):
        LectorTmy(escribirTmyRecortado(tmp_path, quitarColumna="DNI")).leer()


def test_lectorRegistrosIncompletos(tmp_path):
    with pytest.raises(ValueError, match="8760"):
        LectorTmy(escribirTmyRecortado(tmp_path, quitarRegistros=1)).leer()


def test_lectorArchivoInexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        LectorTmy(tmp_path / "noExiste.csv").leer()


# ----------------------------------------------------------------------
# Posición del sol
# ----------------------------------------------------------------------
def test_cenitCalculadoFrenteANsrdb(recurso):
    """Sección 6.1: el cenit calculado difiere del de NSRDB en menos de 1° (RMS < 0,5°)."""
    df = recurso.dfTmy.filter(recurso.dfTmy["Cenit_grados"] < 85)
    diferencia = (df["CenitCalculado_grados"] - df["Cenit_grados"]).to_numpy()
    assert np.abs(diferencia).max() < 1.0
    assert np.sqrt((diferencia**2).mean()) < 0.5


def test_posicionSolarMediodia():
    """Cerca del mediodía solar el acimut es ~180° (sur) en el hemisferio norte en invierno."""
    posicion = PosicionSolar(19.45, -99.14, -6).calcular([1], [12.6])
    assert posicion["cenit"][0] == pytest.approx(42.5, abs=0.5)
    assert posicion["acimut"][0] == pytest.approx(180, abs=3)


def test_diaDelAnio():
    assert PosicionSolar.diaDelAnio([1, 2, 12], [1, 1, 31]).tolist() == [1, 32, 365]


@pytest.mark.parametrize("parametros", [{"latitud": 91}, {"longitud": -181}, {"zonaHoraria": 15}])
def test_posicionSolarValidaciones(parametros):
    with pytest.raises(ValueError):
        PosicionSolar(**{"latitud": 19.45, "longitud": -99.14, "zonaHoraria": -6, **parametros})


# ----------------------------------------------------------------------
# Irradiancia inclinada
# ----------------------------------------------------------------------
@pytest.mark.parametrize("inclinacion", list(radiacionAnualEsperada))
def test_radiacionAnual(recurso, inclinacion):
    assert recurso.radiacionAnual(inclinacion) == pytest.approx(radiacionAnualEsperada[inclinacion], rel=toleranciaRelativa)


def test_inclinacionOptima(recurso):
    optima = recurso.inclinacionOptima()
    assert optima["inclinacion"] == 19
    assert optima["radiacionAnual_kWhm2"] == pytest.approx(radiacionAnualEsperada[19] / 1000, rel=toleranciaRelativa)


def test_radiacionMensual(recurso):
    df = recurso.radiacionMensual(19)
    assert df["Dias"].to_list() == [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for fila, (htDia, htMes, tamb) in zip(df.iter_rows(named=True), mensualEsperado):
        assert round(fila["HTdia_kWhm2dia"], 3) == htDia
        assert round(fila["HTmes_kWhm2mes"], 2) == htMes
        assert round(fila["Tamb_C"], 2) == tamb
    assert df["HTmes_kWhm2mes"].sum() * 1000 == pytest.approx(radiacionAnualEsperada[19], rel=toleranciaRelativa)


def test_planoVertical(recurso):
    df = recurso.calcularPlano(90)
    assert np.allclose(df["Gdi_Wm2"].to_numpy(), df["DHI_Wm2"].to_numpy() / 2)
    assert np.allclose(df["Gri_Wm2"].to_numpy(), (df["GHI_Wm2"] * df["Albedo"]).to_numpy() / 2)


def test_sinDirectaNoHayGbi(recurso):
    df = recurso.calcularPlano(19).filter(recurso.dfTmy["DNI_Wm2"] == 0)
    assert df["Gbi_Wm2"].abs().max() == 0


def test_componentesNoNegativas(recurso):
    df = recurso.calcularPlano(45)
    for componente in RecursoSolar.componentesInclinadas:
        assert df[componente].min() >= 0


def test_agregados(recurso):
    dfPlano = recurso.calcularPlano(19)
    diaria = recurso.radiacionDiaria(dfPlano)
    assert diaria.height == 365
    assert diaria["GTI_kWhm2dia"].sum() * 1000 == pytest.approx(radiacionAnualEsperada[19], rel=toleranciaRelativa)
    assert recurso.perfilHorario(dfPlano).height == 24
    assert recurso.perfilHorario(dfPlano, porMes=True).height == 12 * 24


@pytest.mark.parametrize("inclinacion", [-1, 91])
def test_inclinacionInvalida(recurso, inclinacion):
    with pytest.raises(ValueError):
        recurso.calcularPlano(inclinacion)


def test_acimutPanelInvalido():
    with pytest.raises(ValueError):
        RecursoSolar(rutaTmy, acimutPanel=360)


def test_cenitCalculadoComoAlternativa():
    """Con el cenit calculado la radiación anual cambia poco (< 0,5 %)."""
    anual = RecursoSolar(rutaTmy, usarCenitArchivo=False).radiacionAnual(19)
    assert anual == pytest.approx(radiacionAnualEsperada[19], rel=5e-3)
    assert anual != radiacionAnualEsperada[19]
