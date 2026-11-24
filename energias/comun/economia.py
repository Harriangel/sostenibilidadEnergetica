"""Indicadores económicos comunes a todas las tecnologías: valor presente y LCOE."""


class IndicadoresEconomicos:
    """Valor presente, factor de recuperación de capital y LCOE para una tasa y una vida útil.

    Convenciones (las del método de valor presente de una anualidad vencida):
      - El CAPEX se invierte íntegro en el año 0.
      - El OPEX y la energía son constantes y ocurren al final de cada año, de 1 a la vida útil.

        FVP  = Σ_{t=1..VU} 1/(1+r)^t = [1 − (1+r)^(−VU)] / r      (VU si r = 0)
        CRF  = 1 / FVP
        VP costos  = CAPEX + OPEX · FVP
        VP energía = E · FVP
        LCOE = VP costos / VP energía                              [moneda / unidad de energía]

    La unidad del LCOE es la moneda de los costos dividida por la unidad de la energía anual
    (por ejemplo EUR/kWh si la energía se da en kWh/año).
    """

    def __init__(self, tasaDescuento: float, vidaUtil: float):
        if vidaUtil <= 0:
            raise ValueError(f"La vida útil debe ser mayor que 0 años (se recibió {vidaUtil}).")
        if tasaDescuento < 0:
            raise ValueError(f"La tasa de descuento no puede ser negativa (se recibió {tasaDescuento}).")
        self.tasaDescuento = tasaDescuento
        self.vidaUtil = vidaUtil

    def factorValorPresente(self) -> float:
        """FVP de una anualidad vencida [años]; si la tasa es 0 vale la vida útil."""
        if self.tasaDescuento == 0:
            return float(self.vidaUtil)
        return (1 - (1 + self.tasaDescuento) ** -self.vidaUtil) / self.tasaDescuento

    def factorRecuperacionCapital(self) -> float:
        """CRF = 1 / FVP [1/año]: anualidad equivalente a una inversión de 1 en el año 0."""
        return 1 / self.factorValorPresente()

    def valorPresenteCostos(self, capex: float, opex: float) -> float:
        """VP costos = CAPEX + OPEX · FVP [moneda]."""
        if capex < 0 or opex < 0:
            raise ValueError("El CAPEX y el OPEX no pueden ser negativos.")
        return capex + opex * self.factorValorPresente()

    def valorPresenteEnergia(self, energiaAnual: float) -> float:
        """VP energía = E · FVP [unidad de energía], con E la energía anual."""
        if energiaAnual <= 0:
            raise ValueError(f"La energía anual debe ser positiva (se recibió {energiaAnual}).")
        return energiaAnual * self.factorValorPresente()

    def lcoe(self, capex: float, opex: float, energiaAnual: float) -> float:
        """LCOE por valor presente [moneda / unidad de energía]."""
        return self.valorPresenteCostos(capex, opex) / self.valorPresenteEnergia(energiaAnual)
