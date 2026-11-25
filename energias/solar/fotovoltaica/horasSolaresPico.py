"""Energía útil de un sistema fotovoltaico por el método de horas solares pico.

Implementa la sección 2 y las ampliaciones 1 a 3 de
docs/especificaciones/solar/fotovoltaica/horasSolaresPico.md (hoja «Energía útil» del libro
«Análisis de radiación diaria.xlsx»).
"""
import numpy as np
import polars as pl

from energias.comun.unidades import Unidades


class SistemaFotovoltaicoHsp:
    """Em = H · días · Pnom · (1 − pérdidas) · ηinv, con H la radiación diaria media de cada mes.

    H en kWh/m²·día equivale a horas solares pico (H / 1 kW/m²), así que Em queda en kWh/mes.
    """

    diasPorMes = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    nombresMeses = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    horasPorAnio = 8760
    # GHI mensual de NASA POWER (2001–2020) para Bogotá (lat 4,6493; lon −74,1671), kWh/m²·día
    radiacionBogotaNasa = (4.9236, 4.8634, 4.5098, 4.4542, 4.4765, 4.5036, 4.5866, 4.6322, 4.866, 4.7105, 4.507, 4.6457)

    def __init__(
        self,
        radiacionDiaria=radiacionBogotaNasa,
        potenciaNominal: float = 5.0,
        perdidasSistema: float = 0.14,
        eficienciaInversor: float = 1.0,
        unidadEnergia: str = "kWh",
    ):
        """
        radiacionDiaria: 12 valores de radiación diaria media en el plano (kWh/m²·día); por defecto,
            la GHI horizontal de NASA POWER para Bogotá (caso del Excel).
        potenciaNominal: kWp. perdidasSistema: fracción en [0, 1). eficienciaInversor: (0, 1].
        unidadEnergia: kWh, MWh o GWh para la energía reportada.
        """
        radiacion = np.asarray(radiacionDiaria, dtype=float)
        if radiacion.shape != (12,):
            raise ValueError("La radiación diaria debe tener 12 valores mensuales.")
        if (radiacion < 0).any():
            raise ValueError("La radiación diaria no puede ser negativa.")
        if potenciaNominal <= 0:
            raise ValueError(f"La potencia nominal debe ser positiva (se recibió {potenciaNominal}).")
        if not 0 <= perdidasSistema < 1:
            raise ValueError(f"Las pérdidas del sistema deben estar en [0, 1) (se recibió {perdidasSistema}).")
        if not 0 < eficienciaInversor <= 1:
            raise ValueError(f"La eficiencia del inversor debe estar en (0, 1] (se recibió {eficienciaInversor}).")
        Unidades.factorEnergia(unidadEnergia)  # valida la unidad
        self.radiacionDiaria = radiacion
        self.potenciaNominal = potenciaNominal
        self.perdidasSistema = perdidasSistema
        self.eficienciaInversor = eficienciaInversor
        self.unidadEnergia = unidadEnergia
        self.dias = np.array(self.diasPorMes, dtype=float)

    @classmethod
    def desdeRecursoSolar(cls, recursoSolar, inclinacion: float, **parametros) -> "SistemaFotovoltaicoHsp":
        """Sistema con la radiación en el plano del panel calculada por RecursoSolar (TMY)."""
        dfMensual = recursoSolar.radiacionMensual(inclinacion)
        return cls(radiacionDiaria=dfMensual["HTdia_kWhm2dia"].to_numpy(), **parametros)

    def rendimientoGlobal(self) -> float:
        """Rendimiento global del sistema (performance ratio): (1 − pérdidas) · ηinv."""
        return (1 - self.perdidasSistema) * self.eficienciaInversor

    def radiacionMensual(self) -> np.ndarray:
        """Hm = H · días (kWh/m²·mes)."""
        return self.radiacionDiaria * self.dias

    def energiaMensualKWh(self) -> np.ndarray:
        """Em = Hm · Pnom · (1 − pérdidas) · ηinv (kWh/mes), en el orden de la hoja de Excel."""
        return self.radiacionMensual() * self.potenciaNominal * (1 - self.perdidasSistema) * self.eficienciaInversor

    def calcularMensual(self) -> pl.DataFrame:
        """Radiación mensual, energía útil y rendimiento específico de cada mes."""
        radiacionMensual = self.radiacionMensual()
        energiaKWh = self.energiaMensualKWh()
        nombreEnergia = f"Energia_{self.unidadEnergia}mes"
        return pl.DataFrame(
            {
                "Mes": list(self.nombresMeses),
                "Dias": list(self.diasPorMes),
                "RadiacionDiaria_kWhm2dia": self.radiacionDiaria,
                "RadiacionMensual_kWhm2mes": radiacionMensual,
                nombreEnergia: Unidades.convertirEnergia(energiaKWh, "kWh", self.unidadEnergia),
                "Rendimiento_kWhkWpmes": energiaKWh / self.potenciaNominal,
            }
        )

    def calcular(self) -> dict:
        """Resultados anuales (energía en la unidad elegida y en kWh) y tabla mensual."""
        dfMensual = self.calcularMensual()
        energiaAnualKWh = float(np.sum(self.energiaMensualKWh()))
        return {
            "radiacionMaxima_kWhm2dia": float(self.radiacionDiaria.max()),
            "radiacionMinima_kWhm2dia": float(self.radiacionDiaria.min()),
            "radiacionAnual_kWhm2": float(np.sum(self.radiacionMensual())),
            "energiaAnual_kWh": energiaAnualKWh,
            "energiaAnual": Unidades.convertirEnergia(energiaAnualKWh, "kWh", self.unidadEnergia),
            "unidadEnergia": self.unidadEnergia,
            "promedioDiario_kWh": energiaAnualKWh / 365,
            "rendimientoAnual_kWhkWp": energiaAnualKWh / self.potenciaNominal,
            "factorPlanta": energiaAnualKWh / (self.potenciaNominal * self.horasPorAnio),
            "rendimientoGlobal": self.rendimientoGlobal(),
            "dfMensual": dfMensual,
        }
