import math

import polars as pl


class DisenoTuberiaForzada:
    """Diámetro económico de una tubería forzada.

    El diámetro económico se obtiene iterando: en cada paso se recalculan la velocidad,
    el número de Reynolds, el factor de fricción f y el costo por metro de la tubería con
    el diámetro del paso anterior, hasta que el error relativo entre dos diámetros
    consecutivos sea menor o igual que la tolerancia (5 % por defecto).
    """

    metodosFriccion = ("Colebrook-White", "Swamee-Jain")

    # Rugosidad absoluta de algunos materiales (tabla del diagrama de Moody del Excel):
    # (material, ε en pulgadas, ε en mm, ε usado en el cálculo en mm).
    # Para el concreto, que se da como rango, se usa el valor medio.
    tablaRugosidad = (
        ("Vidrio, plástico", "0", "0", 0.0),
        ("PVC", "0,000 06", "0,0015", 0.0015),
        ("Concreto (se usa el valor medio)", "0,035 - 0,35", "0,9 - 9", 4.95),
        ("Goma lisa", "0,0004", "0,01", 0.01),
        ("Tubería de cobre o bronce", "0,000 06", "0,0015", 0.0015),
        ("Hierro fundido", "0,01", "0,26", 0.26),
        ("Hierro galvanizado", "0,0059", "0,15", 0.15),
        ("Hierro forjado", "0,0018", "0,046", 0.046),
        ("Acero inoxidable", "0,000 08", "0,002", 0.002),
        ("Acero comercial", "0,0018", "0,045", 0.045),
    )

    # Ecuación del diámetro económico: D = 1.106 * (f*h*p / (η*a*c))^0.143 * Q^0.43
    coeficienteDiametro = 1.106
    exponenteCostos = 0.143
    exponenteCaudal = 0.43

    # Costo de la tubería en dólares por metro: c = 12.16 + 513.5 * D^1.5 (D en m)
    costoFijoUsd = 12.16
    costoVariableUsd = 513.5
    exponenteCostoDiametro = 1.5

    def __init__(
        self,
        rugosidadMm: float,
        densidadAgua: float = 1000.0,
        viscosidad: float = 0.001,
        horasFuncionamiento: float = 6000.0,
        precioEnergia: float = 0.27,
        eficienciaGlobal: float = 0.9,
        factorAmortizacion: float = 0.064,
        metodoFriccion: str = "Colebrook-White",
        tolerancia: float = 0.05,
        velocidadInicial: float = 2.5,
        moneda: str = "USD",
        tasaCambio: float = 1.0,
        maxIteraciones: int = 100,
    ):
        if metodoFriccion not in self.metodosFriccion:
            raise ValueError(f"Método '{metodoFriccion}' no válido. Opciones: {', '.join(self.metodosFriccion)}.")
        if rugosidadMm < 0:
            raise ValueError("La rugosidad no puede ser negativa.")
        for nombre, valor in (
            ("densidad del agua", densidadAgua),
            ("viscosidad", viscosidad),
            ("horas de funcionamiento", horasFuncionamiento),
            ("precio de la energía", precioEnergia),
            ("eficiencia global", eficienciaGlobal),
            ("factor de amortización", factorAmortizacion),
            ("tolerancia", tolerancia),
            ("velocidad inicial", velocidadInicial),
            ("tasa de cambio", tasaCambio),
        ):
            if valor <= 0:
                raise ValueError(f"La {nombre} debe ser positiva.")
        self.rugosidadMm = rugosidadMm
        self.rugosidad = rugosidadMm / 1000  # m
        self.densidadAgua = densidadAgua
        self.viscosidad = viscosidad
        self.horasFuncionamiento = horasFuncionamiento
        self.precioEnergia = precioEnergia
        self.eficienciaGlobal = eficienciaGlobal
        self.factorAmortizacion = factorAmortizacion
        self.metodoFriccion = metodoFriccion
        self.tolerancia = tolerancia
        self.velocidadInicial = velocidadInicial
        self.moneda = moneda.strip() or "USD"
        self.tasaCambio = tasaCambio
        self.maxIteraciones = maxIteraciones

    # ------------------------------------------------------------------
    # Tabla de rugosidad
    # ------------------------------------------------------------------
    @classmethod
    def rugosidadPorMaterial(cls) -> dict:
        """{material: ε usado en mm}."""
        return {material: usado for material, _, _, usado in cls.tablaRugosidad}

    @classmethod
    def tablaRugosidadDataFrame(cls) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "Material": [fila[0] for fila in cls.tablaRugosidad],
                "ε (pulgadas)": [fila[1] for fila in cls.tablaRugosidad],
                "ε (mm)": [fila[2] for fila in cls.tablaRugosidad],
                "ε usado (mm)": [fila[3] for fila in cls.tablaRugosidad],
            }
        )

    # ------------------------------------------------------------------
    # Factor de fricción de Darcy
    # ------------------------------------------------------------------
    @staticmethod
    def friccionSwameeJain(reynolds: float, rugosidadRelativa: float) -> float:
        """Ecuación explícita de Swamee-Jain."""
        return 0.25 / math.log10(rugosidadRelativa / 3.7 + 5.74 / reynolds**0.9) ** 2

    @staticmethod
    def friccionColebrook(reynolds: float, rugosidadRelativa: float) -> float:
        """Ecuación implícita de Colebrook-White, resuelta de forma iterativa."""
        factor = DisenoTuberiaForzada.friccionSwameeJain(reynolds, rugosidadRelativa)
        for _ in range(100):
            factorNuevo = (
                -2 * math.log10(rugosidadRelativa / 3.7 + 2.51 / (reynolds * math.sqrt(factor)))
            ) ** -2
            if abs(factorNuevo - factor) < 1e-12:
                return factorNuevo
            factor = factorNuevo
        return factor

    @staticmethod
    def clasificarRegimen(reynolds: float) -> str:
        if reynolds < 2000:
            return "laminar"
        if reynolds < 4000:
            return "de transición"
        return "turbulento"

    def calcularFriccion(self, reynolds: float, rugosidadRelativa: float, metodo: str = None) -> float:
        """f según el método elegido; en régimen laminar se usa f = 64/Re."""
        if reynolds < 2000:
            return 64 / reynolds
        if (metodo or self.metodoFriccion) == "Swamee-Jain":
            return self.friccionSwameeJain(reynolds, rugosidadRelativa)
        return self.friccionColebrook(reynolds, rugosidadRelativa)

    def compararMetodosFriccion(self, reynolds: float, rugosidadRelativa: float) -> pl.DataFrame:
        """f con cada método y su diferencia porcentual respecto a Colebrook-White."""
        valores = {metodo: self.calcularFriccion(reynolds, rugosidadRelativa, metodo) for metodo in self.metodosFriccion}
        referencia = valores["Colebrook-White"]
        return pl.DataFrame(
            {
                "Método": list(valores.keys()),
                "Factor de fricción f": list(valores.values()),
                "Diferencia vs Colebrook-White (%)": [(f - referencia) / referencia * 100 for f in valores.values()],
            }
        )

    # ------------------------------------------------------------------
    # Hidráulica, costo y espesor
    # ------------------------------------------------------------------
    def calcularVelocidad(self, caudal: float, diametro: float) -> float:
        return 4 * caudal / (math.pi * diametro**2)

    def calcularReynolds(self, velocidad: float, diametro: float) -> float:
        return self.densidadAgua * velocidad * diametro / self.viscosidad

    def calcularCostoTuberia(self, diametro: float) -> float:
        """Costo por metro en la moneda elegida (la correlación está en dólares)."""
        return self.tasaCambio * (self.costoFijoUsd + self.costoVariableUsd * diametro**self.exponenteCostoDiametro)

    def calcularEspesor(self, diametro: float) -> float:
        """e = (D + 508) / 400, con D y e en milímetros."""
        return (diametro * 1000 + 508) / 400

    def calcularDiametroEconomico(self, factorFriccion: float, costoTuberia: float, caudal: float) -> float:
        relacion = (factorFriccion * self.horasFuncionamiento * self.precioEnergia) / (
            self.eficienciaGlobal * self.factorAmortizacion * costoTuberia
        )
        return self.coeficienteDiametro * relacion**self.exponenteCostos * caudal**self.exponenteCaudal

    def evaluarDiametro(self, caudal: float, diametro: float) -> dict:
        """Velocidad, Reynolds, f, costo y espesor para un diámetro dado."""
        velocidad = self.calcularVelocidad(caudal, diametro)
        reynolds = self.calcularReynolds(velocidad, diametro)
        rugosidadRelativa = self.rugosidad / diametro
        return {
            "diametro": diametro,
            "velocidad": velocidad,
            "reynolds": reynolds,
            "regimen": self.clasificarRegimen(reynolds),
            "rugosidadRelativa": rugosidadRelativa,
            "factorFriccion": self.calcularFriccion(reynolds, rugosidadRelativa),
            "costoTuberia": self.calcularCostoTuberia(diametro),
            "espesor": self.calcularEspesor(diametro),
        }

    # ------------------------------------------------------------------
    # Iteración
    # ------------------------------------------------------------------
    def iterarDiametro(self, caudal: float) -> dict:
        """Itera hasta que el error relativo entre diámetros consecutivos sea <= tolerancia.

        Diámetro inicial: el que da la velocidad inicial supuesta para el caudal.
        Error relativo = |D nuevo - D anterior| / D nuevo.
        """
        if caudal <= 0:
            raise ValueError("El caudal de diseño debe ser positivo.")

        diametro = math.sqrt(4 * caudal / (math.pi * self.velocidadInicial))
        filas = []
        converge = False
        errorRelativo = float("nan")
        for iteracion in range(1, self.maxIteraciones + 1):
            paso = self.evaluarDiametro(caudal, diametro)
            diametroNuevo = self.calcularDiametroEconomico(paso["factorFriccion"], paso["costoTuberia"], caudal)
            errorRelativo = abs(diametroNuevo - diametro) / diametroNuevo
            filas.append(
                {
                    "Iteracion": iteracion,
                    "DiametroEntrada_m": diametro,
                    "Velocidad_ms": paso["velocidad"],
                    "Reynolds": paso["reynolds"],
                    "RugosidadRelativa": paso["rugosidadRelativa"],
                    "FactorFriccion": paso["factorFriccion"],
                    "CostoTuberia": paso["costoTuberia"],
                    "DiametroCalculado_m": diametroNuevo,
                    "ErrorRelativo_pct": errorRelativo * 100,
                }
            )
            diametro = diametroNuevo
            if errorRelativo <= self.tolerancia:
                converge = True
                break

        return {
            "historial": pl.DataFrame(filas),
            "converge": converge,
            "iteraciones": len(filas),
            "errorFinal": errorRelativo,
            "resultado": self.evaluarDiametro(caudal, diametro),
        }
