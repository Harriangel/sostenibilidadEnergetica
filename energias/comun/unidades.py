"""Unidades de potencia y energía comunes a todas las tecnologías."""


class Unidades:
    """Factores de conversión de potencia (W, kW, MW, GW) y energía (Wh, kWh, MWh, GWh).

    Las magnitudes se calculan internamente en W y Wh; estos factores las llevan a la
    unidad elegida por el usuario (valor en la unidad = valor en W o Wh × factor).
    """

    # Factor de conversión desde W (o Wh) a cada unidad de potencia (o de energía)
    factoresPotencia = {"W": 1.0, "kW": 1e-3, "MW": 1e-6, "GW": 1e-9}

    # Julios por vatio-hora
    joulesPorWh = 3600.0

    @classmethod
    def unidadesPotencia(cls) -> list:
        """['W', 'kW', 'MW', 'GW']."""
        return list(cls.factoresPotencia)

    @classmethod
    def unidadesEnergia(cls) -> list:
        """['Wh', 'kWh', 'MWh', 'GWh']."""
        return [f"{unidad}h" for unidad in cls.factoresPotencia]

    @classmethod
    def validarUnidadPotencia(cls, unidad: str) -> str:
        """Devuelve la unidad si es válida (W, kW, MW o GW); si no, lanza ValueError."""
        if unidad not in cls.factoresPotencia:
            raise ValueError(f"Unidad '{unidad}' no válida. Opciones: W, kW, MW o GW.")
        return unidad

    @classmethod
    def factorPotencia(cls, unidad: str) -> float:
        """Factor desde W a la unidad de potencia indicada (W, kW, MW o GW)."""
        return cls.factoresPotencia[cls.validarUnidadPotencia(unidad)]

    @classmethod
    def factorEnergia(cls, unidadEnergia: str) -> float:
        """Factor desde Wh a la unidad de energía indicada (Wh, kWh, MWh o GWh)."""
        if not unidadEnergia.endswith("h") or unidadEnergia[:-1] not in cls.factoresPotencia:
            raise ValueError(f"Unidad de energía '{unidadEnergia}' no válida. Opciones: Wh, kWh, MWh o GWh.")
        return cls.factoresPotencia[unidadEnergia[:-1]]

    @classmethod
    def convertirEnergia(cls, valor: float, unidadOrigen: str, unidadDestino: str) -> float:
        """Convierte una energía entre Wh, kWh, MWh y GWh."""
        return valor / cls.factorEnergia(unidadOrigen) * cls.factorEnergia(unidadDestino)

    @classmethod
    def joulesAWh(cls, joules: float) -> float:
        """J → Wh (1 Wh = 3600 J)."""
        return joules / cls.joulesPorWh

    @classmethod
    def whAJoules(cls, vatiosHora: float) -> float:
        """Wh → J (1 Wh = 3600 J)."""
        return vatiosHora * cls.joulesPorWh
