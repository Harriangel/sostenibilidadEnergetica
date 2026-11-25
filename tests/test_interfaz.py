"""Pruebas de humo de la interfaz multipágina con streamlit.testing.v1.AppTest."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

carpetaInterfaz = Path(__file__).resolve().parent.parent / "interfaz"
tiempoMaximo = 120  # segundos por ejecución del script


def test_paginaInicio():
    app = AppTest.from_file(str(carpetaInterfaz / "app.py"), default_timeout=tiempoMaximo).run()
    assert not app.exception
    assert "Plataforma" in app.title[0].value


def test_paginaHidraulicaSinCalcular():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "1_Hidraulica.py"), default_timeout=tiempoMaximo).run()
    assert not app.exception
    assert "hidraulica_resultadosAnalisis" not in app.session_state


def test_paginaHidraulicaCalcula():
    """Caso IDEAM de referencia (Kaplan, H = 10 m, ηg = 0,85 y ηG = 0,95) calculado desde la interfaz."""
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "1_Hidraulica.py"), default_timeout=tiempoMaximo).run()
    app.sidebar.radio[1].set_value("Turbina y generador por separado").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert not app.error

    estado = app.session_state["hidraulica_resultadosAnalisis"]
    maximo = estado["resultados"]["maximo"]
    assert maximo["CaudalEquipamiento"] == pytest.approx(3.4717000000000002, rel=1e-9)
    assert maximo["EnergiaAnual_kWh"] == pytest.approx(1032428.0985059995, rel=1e-9)
    # Las pestañas del canal y de la tubería usan el Qe calculado
    etiquetas = [metrica.label for metrica in app.metric]
    assert "Diámetro económico D (m)" in etiquetas
    assert "Número de Froude" in etiquetas


def test_paginaMareomotrizCalculaConValoresPorDefecto():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "2_Mareomotriz.py"), default_timeout=tiempoMaximo).run()
    assert not app.exception
    assert not app.error
    resultados = app.session_state["mareomotriz_resultados"]
    assert resultados["lcoeBase_porKWh"] == pytest.approx(0.07394756153502048, rel=1e-9)
    assert resultados["energiaUtil_kWh"] == pytest.approx(22911539.80645161, rel=1e-9)
    etiquetas = [metrica.label for metrica in app.metric]
    assert "LCOE base (EUR/kWh)" in etiquetas


def test_paginaMareomotrizCambiaEntradas():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "2_Mareomotriz.py"), default_timeout=tiempoMaximo).run()
    app.selectbox(key="mareomotriz_direccion").set_value("Unidireccional").run()
    app.number_input(key="mareomotriz_numeroTurbinas").set_value(3).run()
    app.selectbox(key="mareomotriz_unidadEnergia").set_value("GWh").run()
    app.selectbox(key="mareomotriz_parametroSensibilidad").set_value("capex").run()
    assert not app.exception
    resultados = app.session_state["mareomotriz_resultados"]
    assert resultados["energiaUtil_kWh"] == pytest.approx(3 * 22911539.80645161 / 2, rel=1e-9)
    assert resultados["lcoeBase_porKWh"] == pytest.approx(2 * 0.07394756153502048, rel=1e-9)


def test_paginaSolarTermicaCalculaConValoresPorDefecto():
    """TMY de Ciudad de México, inclinación óptima (19°) y Klein: 22,91 m² y 12 colectores."""
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "3_SolarTermica.py"), default_timeout=tiempoMaximo).run()
    assert not app.exception
    assert not app.error
    estado = app.session_state["solarTermica_resultados"]
    assert estado["inclinacion"] == 19
    dimensionamiento = estado["resultados"]["dimensionamiento"]
    assert dimensionamiento["numeroColectores"] == 12
    assert dimensionamiento["area_m2"] == pytest.approx(22.91, abs=0.01)
    assert "Colectores" in [metrica.label for metrica in app.metric]


def test_paginaSolarTermicaCorrelacionInformeEInclinacionManual():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "3_SolarTermica.py"), default_timeout=tiempoMaximo).run()
    app.selectbox(key="solarTermica_correlacion").set_value("informe").run()
    app.radio(key="solarTermica_modoInclinacion").set_value("Manual").run()
    app.slider(key="solarTermica_inclinacion").set_value(43).run()
    assert not app.exception
    estado = app.session_state["solarTermica_resultados"]
    assert estado["inclinacion"] == 43
    assert estado["sistema"].correlacion == "informe"


def test_paginaFotovoltaicaReproduceElExcel():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "4_Fotovoltaica.py"), default_timeout=tiempoMaximo).run()
    assert not app.exception
    assert not app.error
    resultados = app.session_state["fotovoltaica_resultados"]["resultados"]
    assert resultados["energiaAnual_kWh"] == pytest.approx(7280.46373, rel=1e-9)
    assert resultados["factorPlanta"] == pytest.approx(0.16622063310502283, rel=1e-9)


def test_paginaFotovoltaicaConTmyYMWh():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "4_Fotovoltaica.py"), default_timeout=tiempoMaximo).run()
    app.radio(key="fotovoltaica_fuente").set_value("tmy").run()
    app.selectbox(key="fotovoltaica_unidadEnergia").set_value("MWh").run()
    assert not app.exception
    resultados = app.session_state["fotovoltaica_resultados"]["resultados"]
    assert resultados["radiacionAnual_kWhm2"] == pytest.approx(2287.663821134124, rel=1e-9)
    assert resultados["unidadEnergia"] == "MWh"


def test_paginaFotovoltaicaEntradaManual():
    app = AppTest.from_file(str(carpetaInterfaz / "pages" / "4_Fotovoltaica.py"), default_timeout=tiempoMaximo).run()
    app.radio(key="fotovoltaica_fuente").set_value("manual").run()
    assert not app.exception
    resultados = app.session_state["fotovoltaica_resultados"]["resultados"]
    assert resultados["energiaAnual_kWh"] == pytest.approx(7280.46373, rel=1e-9)
