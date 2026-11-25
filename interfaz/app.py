"""Página de inicio de la interfaz web de la plataforma.

Ejecución, desde la raíz del repositorio:
    python -m streamlit run interfaz/app.py

Cada tecnología tiene su página en interfaz/pages/ (Streamlit las lista en la barra lateral).
"""
import polars as pl
import streamlit as st

import energias


class PaginaInicio:
    """Describe la plataforma y las tecnologías disponibles."""

    # (tecnología, estado en el aplicativo, página de Streamlit o None si aún no existe)
    tecnologias = (
        ("Hidráulica (pequeña central)", "Implementada: caudal de equipamiento, canal de derivación y tubería forzada", "pages/1_Hidraulica.py"),
        ("Mareomotriz", "Implementada: energía anual por energía potencial y LCOE con escenarios", "pages/2_Mareomotriz.py"),
        ("Solar térmica", "Implementada: recurso solar (TMY) y ACS por F-Chart; albercas pendiente", "pages/3_SolarTermica.py"),
        ("Solar fotovoltaica", "Implementada: energía útil por horas solares pico", "pages/4_Fotovoltaica.py"),
        ("Solar de concentración", "Pendiente", None),
        ("Eólica (en tierra)", "Pendiente", None),
        ("Biomasa", "Pendiente", None),
        ("Corrientes marinas", "Pendiente", None),
        ("Undimotriz (olas)", "Pendiente", None),
        ("Eólica marina (offshore)", "Pendiente", None),
        ("Geotermia", "Pendiente", None),
    )

    def mostrarDescripcion(self) -> None:
        st.title("Plataforma de diseño de centrales de energía renovable")
        st.caption(f"Versión {energias.__version__}")
        st.markdown(
            "Herramienta para el **diseño de prefactibilidad** de centrales de energía renovable, "
            "con un módulo por tecnología. Cada módulo:\n"
            "- estima el recurso y la energía anual;\n"
            "- dimensiona los componentes principales;\n"
            "- calcula indicadores económicos comparables entre tecnologías, empezando por el LCOE.\n\n"
            "Los cálculos de cada tecnología se estudian primero en Excel, se documentan en una "
            "especificación y se implementan con pruebas que reproducen los valores de ese Excel."
        )

    def mostrarTecnologiasDisponibles(self) -> None:
        st.subheader("Tecnologías disponibles")
        for nombre, estado, pagina in self.tecnologias:
            if pagina is not None:
                st.page_link(pagina, label=f"{nombre}: {estado}", icon="➡️")

    def mostrarHojaDeRuta(self) -> None:
        st.subheader("Hoja de ruta")
        dfTecnologias = pl.DataFrame(
            {
                "Tecnología": [nombre for nombre, _, _ in self.tecnologias],
                "Estado en el aplicativo": [estado for _, estado, _ in self.tecnologias],
            }
        )
        st.dataframe(dfTecnologias, hide_index=True)

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Plataforma de energías renovables", layout="wide")
        self.mostrarDescripcion()
        self.mostrarTecnologiasDisponibles()
        self.mostrarHojaDeRuta()
        st.info("Elige una tecnología en la barra lateral para empezar.")


PaginaInicio().ejecutar()
