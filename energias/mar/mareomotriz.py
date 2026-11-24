"""Central mareomotriz: energía anual por energía potencial y LCOE por valor presente.

Implementa las secciones 3.1 a 3.4 de docs/especificaciones/mar/Calculo_mareomotriz_LCOE.md
(libro Calculo_de_la_energia_potencial_y_LCOE.xlsx, hoja Act1). Las fórmulas alternativas de
K31, K36 y K41 (sección 3.5) no se implementan: son incorrectas.
"""
import unicodedata

import numpy as np
import polars as pl

from energias.comun.economia import IndicadoresEconomicos
from energias.comun.unidades import Unidades


class CentralMareomotriz:
    """Calcula, para una central de una o varias turbinas iguales:

    1. los pasos de agua por turbina y año según el tipo de marea y la dirección de la turbina;
    2. la energía potencial y la energía eléctrica (útil) anual;
    3. el LCOE por valor presente, con dos escenarios de sensibilidad
       (A: CAPEX × factorCapexEscenarioA; B: energía × factorEnergiaEscenarioB).

    Ampliaciones respecto al Excel (sección 7 de la especificación), neutras con sus valores
    por defecto:
      - numeroTurbinas (1): multiplica la energía, el CAPEX y el OPEX;
      - disponibilidad (1,0): fracción del año en operación; multiplica la energía útil.

    El CAPEX se da en moneda por turbina (inversión única en el año 0) y el OPEX en moneda por
    turbina y año. La moneda es solo una etiqueta (EUR por defecto, como en el Excel).
    """

    # Ciclos de marea por día lunar y pasos de agua por ciclo (claves normalizadas: minúsculas, sin tildes)
    ciclosPorDiaLunar = {"diurna": 1, "semidiurna": 2}
    pasosPorCiclo = {"unidireccional": 1, "bidireccional": 2}
    nombresMarea = {"diurna": "Diurna", "semidiurna": "Semidiurna"}
    nombresDireccion = {"unidireccional": "Unidireccional", "bidireccional": "Bidireccional"}

    # Factor de energía potencial: el centro de masas desciende, en promedio, la mitad del desnivel
    factorEnergiaPotencial = 0.5
    horasPorDia = 24

    # Parámetros que admite el barrido de sensibilidad del LCOE: {parámetro: (etiqueta, unidad)}
    parametrosSensibilidad = {
        "tasaDescuento": ("Tasa de descuento", "-"),
        "eficiencia": ("Eficiencia global η", "-"),
        "desnivel": ("Desnivel h", "m"),
        "capex": ("CAPEX por turbina", "moneda/turbina"),
    }

    def __init__(
        self,
        tipoMarea: str = "Semidiurna",
        direccion: str = "Bidireccional",
        tipoTurbina: str = "Eje horizontal",
        duracionDiaLunar: float = 24.8,
        duracionDiaSolar: float = 24.0,
        diasAnio: int = 365,
        masaAgua: float = 8.7e9,
        gravedad: float = 9.81,
        desnivel: float = 3.6,
        eficiencia: float = 0.38,
        vidaUtil: int = 25,
        tasaDescuento: float = 0.07,
        capex: float = 14_500_000.0,
        opex: float = 450_000.0,
        factorCapexEscenarioA: float = 1.15,
        factorEnergiaEscenarioB: float = 0.90,
        numeroTurbinas: int = 1,
        disponibilidad: float = 1.0,
        moneda: str = "EUR",
    ):
        """
        Parámetros:
            tipoMarea: "Diurna" o "Semidiurna" (sin distinguir mayúsculas ni tildes).
            direccion: "Unidireccional" o "Bidireccional" (sin distinguir mayúsculas ni tildes).
            tipoTurbina: texto descriptivo; no interviene en los cálculos.
            duracionDiaLunar, duracionDiaSolar: horas.
            diasAnio: días de operación al año.
            masaAgua: masa de agua por ciclo y turbina (kg).
            gravedad: m/s².
            desnivel: desnivel efectivo medio (m).
            eficiencia: rendimiento global η (hidráulico + eléctrico), en (0, 1].
            vidaUtil: años; tasaDescuento: fracción (0,07 = 7 %).
            capex: inversión por turbina (moneda/turbina); opex: moneda/año por turbina.
            factorCapexEscenarioA: multiplica el CAPEX en el escenario A.
            factorEnergiaEscenarioB: multiplica la energía útil en el escenario B.
            numeroTurbinas: entero ≥ 1. disponibilidad: fracción del año en operación, en (0, 1].
            moneda: etiqueta de la moneda.
        """
        self.parametros = {
            "tipoMarea": tipoMarea,
            "direccion": direccion,
            "tipoTurbina": tipoTurbina,
            "duracionDiaLunar": duracionDiaLunar,
            "duracionDiaSolar": duracionDiaSolar,
            "diasAnio": diasAnio,
            "masaAgua": masaAgua,
            "gravedad": gravedad,
            "desnivel": desnivel,
            "eficiencia": eficiencia,
            "vidaUtil": vidaUtil,
            "tasaDescuento": tasaDescuento,
            "capex": capex,
            "opex": opex,
            "factorCapexEscenarioA": factorCapexEscenarioA,
            "factorEnergiaEscenarioB": factorEnergiaEscenarioB,
            "numeroTurbinas": numeroTurbinas,
            "disponibilidad": disponibilidad,
            "moneda": moneda,
        }

        claveMarea = self.normalizarTexto(tipoMarea)
        if claveMarea not in self.ciclosPorDiaLunar:
            raise ValueError(f"Tipo de marea '{tipoMarea}' no válido. Opciones: Diurna o Semidiurna.")
        claveDireccion = self.normalizarTexto(direccion)
        if claveDireccion not in self.pasosPorCiclo:
            raise ValueError(f"Dirección '{direccion}' no válida. Opciones: Unidireccional o Bidireccional.")
        if not 0 < eficiencia <= 1:
            raise ValueError(f"La eficiencia debe estar en (0, 1] (se recibió {eficiencia}).")
        if not 0 < disponibilidad <= 1:
            raise ValueError(f"La disponibilidad debe estar en (0, 1] (se recibió {disponibilidad}).")
        if int(numeroTurbinas) != numeroTurbinas or numeroTurbinas < 1:
            raise ValueError(f"El número de turbinas debe ser un entero mayor o igual que 1 (se recibió {numeroTurbinas}).")
        for nombre, valor in (
            ("masa de agua", masaAgua),
            ("desnivel", desnivel),
            ("gravedad", gravedad),
            ("duración del día lunar", duracionDiaLunar),
            ("duración del día solar", duracionDiaSolar),
            ("número de días por año", diasAnio),
            ("factor de CAPEX del escenario A", factorCapexEscenarioA),
            ("factor de energía del escenario B", factorEnergiaEscenarioB),
        ):
            if valor <= 0:
                raise ValueError(f"El valor de {nombre} debe ser positivo (se recibió {valor}).")
        if capex < 0 or opex < 0:
            raise ValueError("El CAPEX y el OPEX no pueden ser negativos.")

        self.tipoMarea = self.nombresMarea[claveMarea]
        self.direccion = self.nombresDireccion[claveDireccion]
        self.tipoTurbina = tipoTurbina
        self.duracionDiaLunar = duracionDiaLunar
        self.duracionDiaSolar = duracionDiaSolar
        self.diasAnio = diasAnio
        self.masaAgua = masaAgua
        self.gravedad = gravedad
        self.desnivel = desnivel
        self.eficiencia = eficiencia
        self.capex = capex
        self.opex = opex
        self.factorCapexEscenarioA = factorCapexEscenarioA
        self.factorEnergiaEscenarioB = factorEnergiaEscenarioB
        self.numeroTurbinas = int(numeroTurbinas)
        self.disponibilidad = disponibilidad
        self.moneda = moneda.strip() or "EUR"
        # Valida vida útil > 0 y tasa >= 0
        self.economia = IndicadoresEconomicos(tasaDescuento=tasaDescuento, vidaUtil=vidaUtil)
        self.vidaUtil = vidaUtil
        self.tasaDescuento = tasaDescuento

    @staticmethod
    def normalizarTexto(texto: str) -> str:
        """Minúsculas y sin tildes, para aceptar 'semidiurna', 'SEMIDIURNA', 'Unidireccionál', etc."""
        textoSinTildes = unicodedata.normalize("NFD", str(texto).strip().lower())
        return "".join(c for c in textoSinTildes if unicodedata.category(c) != "Mn")

    # ------------------------------------------------------------------
    # Sección 3.1: pasos de agua por turbina y año
    # ------------------------------------------------------------------
    def calcularPasos(self) -> dict:
        """K12 a K15: duración del ciclo, ciclos por día y por año, y pasos por turbina y año."""
        cicloMarea = self.duracionDiaLunar / self.ciclosPorDiaLunar[self.normalizarTexto(self.tipoMarea)]
        ciclosPorDia = self.duracionDiaSolar / cicloMarea
        ciclosPorAnio = ciclosPorDia * self.diasAnio
        pasosPorAnio = ciclosPorAnio * self.pasosPorCiclo[self.normalizarTexto(self.direccion)]
        return {
            "cicloMarea_h": cicloMarea,
            "ciclosPorDia": ciclosPorDia,
            "ciclosPorAnio": ciclosPorAnio,
            "pasosPorAnio": pasosPorAnio,
        }

    # ------------------------------------------------------------------
    # Sección 3.2: energía anual
    # ------------------------------------------------------------------
    def calcularEnergia(self, pasosPorAnio: float) -> dict:
        """K19 a K24: energía potencial y útil anual de la central (todas las turbinas)."""
        energiaPorPaso = self.factorEnergiaPotencial * self.masaAgua * self.gravedad * self.desnivel
        energiaPotencialJ = pasosPorAnio * self.masaAgua * self.gravedad * self.desnivel * self.factorEnergiaPotencial
        energiaPotencialJ *= self.numeroTurbinas
        energiaPotencialKWh = Unidades.joulesAKWh(energiaPotencialJ)
        energiaUtilKWh = energiaPotencialKWh * self.eficiencia * self.disponibilidad
        horasPorAnio = self.diasAnio * self.horasPorDia
        return {
            "energiaPorPaso_J": energiaPorPaso,
            "energiaPotencial_J": energiaPotencialJ,
            "energiaPotencial_kWh": energiaPotencialKWh,
            "energiaUtil_kWh": energiaUtilKWh,
            "energiaUtil_MWh": energiaUtilKWh / 1e3,
            "energiaUtil_GWh": energiaUtilKWh / 1e6,
            "potenciaMedia_MW": energiaUtilKWh / 1e3 / horasPorAnio,
        }

    # ------------------------------------------------------------------
    # Secciones 3.3 y 3.4: LCOE y escenarios
    # ------------------------------------------------------------------
    def calcularEscenarios(self, energiaUtilKWh: float) -> list:
        """[(escenario, descripción, CAPEX total, OPEX total, energía útil anual)] de base, A y B."""
        capexTotal = self.capex * self.numeroTurbinas
        opexTotal = self.opex * self.numeroTurbinas
        return [
            ("Base", "Valores de entrada", capexTotal, opexTotal, energiaUtilKWh),
            (
                "A",
                f"CAPEX × {self.factorCapexEscenarioA:g}",
                capexTotal * self.factorCapexEscenarioA,
                opexTotal,
                energiaUtilKWh,
            ),
            (
                "B",
                f"Energía × {self.factorEnergiaEscenarioB:g}",
                capexTotal,
                opexTotal,
                energiaUtilKWh * self.factorEnergiaEscenarioB,
            ),
        ]

    def tablaEscenarios(self, energiaUtilKWh: float = None) -> pl.DataFrame:
        """Valor presente de costos y de energía, LCOE y variación frente al caso base por escenario."""
        if energiaUtilKWh is None:
            energiaUtilKWh = self.calcularEnergia(self.calcularPasos()["pasosPorAnio"])["energiaUtil_kWh"]
        filas = []
        for escenario, descripcion, capex, opex, energia in self.calcularEscenarios(energiaUtilKWh):
            filas.append(
                {
                    "Escenario": escenario,
                    "Cambio": descripcion,
                    f"ValorPresenteCostos_{self.moneda}": self.economia.valorPresenteCostos(capex, opex),
                    "ValorPresenteEnergia_kWh": self.economia.valorPresenteEnergia(energia),
                    f"LCOE_{self.moneda}_por_kWh": self.economia.lcoe(capex, opex, energia),
                }
            )
        df = pl.DataFrame(filas)
        columnaLcoe = f"LCOE_{self.moneda}_por_kWh"
        lcoeBase = df[columnaLcoe][0]
        return df.with_columns(
            (pl.col(columnaLcoe) * 1000).alias(f"LCOE_{self.moneda}_por_MWh"),
            ((pl.col(columnaLcoe) / lcoeBase - 1) * 100).alias("VariacionFrenteBase_pct"),
        )

    def calcular(self) -> dict:
        """Todas las salidas de la sección 4 de la especificación, los intermedios de la 3.3 y la
        tabla de escenarios. Las energías son de la central (numeroTurbinas turbinas); los pasos,
        por turbina. Los costos están en la moneda indicada y el LCOE en moneda/kWh."""
        pasos = self.calcularPasos()
        energia = self.calcularEnergia(pasos["pasosPorAnio"])
        energiaUtil = energia["energiaUtil_kWh"]
        dfEscenarios = self.tablaEscenarios(energiaUtil)
        columnaLcoe = f"LCOE_{self.moneda}_por_kWh"
        lcoeBase, lcoeA, lcoeB = dfEscenarios[columnaLcoe].to_list()
        capexTotal = self.capex * self.numeroTurbinas
        opexTotal = self.opex * self.numeroTurbinas
        factorValorPresente = self.economia.factorValorPresente()

        return {
            **pasos,
            **energia,
            "capexTotal": capexTotal,
            "opexTotal": opexTotal,
            "factorValorPresente": factorValorPresente,
            "factorRecuperacionCapital": self.economia.factorRecuperacionCapital(),
            "valorPresenteOpex": opexTotal * factorValorPresente,
            "valorPresenteCostos": self.economia.valorPresenteCostos(capexTotal, opexTotal),
            "valorPresenteEnergia_kWh": self.economia.valorPresenteEnergia(energiaUtil),
            "lcoeBase_porKWh": lcoeBase,
            "lcoeEscenarioA_porKWh": lcoeA,
            "lcoeEscenarioB_porKWh": lcoeB,
            "lcoeBase_porMWh": lcoeBase * 1000,
            "variacionEscenarioA_pct": (lcoeA / lcoeBase - 1) * 100,
            "variacionEscenarioB_pct": (lcoeB / lcoeBase - 1) * 100,
            "moneda": self.moneda,
            "dfEscenarios": dfEscenarios,
        }

    # ------------------------------------------------------------------
    # Sensibilidad
    # ------------------------------------------------------------------
    def valoresSensibilidad(self, parametro: str, numeroPuntos: int = 41) -> list:
        """Rango por defecto del barrido: tasa de 0 al doble de la base; eficiencia del 50 % de la base
        hasta min(1, 150 %); desnivel y CAPEX del 50 % al 150 % de la base. Incluye el valor base."""
        self.validarParametroSensibilidad(parametro)
        base = self.parametros[parametro]
        if parametro == "tasaDescuento":
            minimo, maximo = 0.0, 2 * base if base > 0 else 0.15
        elif parametro == "eficiencia":
            minimo, maximo = 0.5 * base, min(1.0, 1.5 * base)
        else:
            minimo, maximo = 0.5 * base, 1.5 * base
        valores = set(np.linspace(minimo, maximo, numeroPuntos).tolist()) | {float(base)}
        return sorted(valores)

    def validarParametroSensibilidad(self, parametro: str) -> None:
        if parametro not in self.parametrosSensibilidad:
            raise ValueError(
                f"Parámetro de sensibilidad '{parametro}' no válido. "
                f"Opciones: {', '.join(self.parametrosSensibilidad)}."
            )

    def barridoSensibilidad(self, parametro: str, valores: list = None) -> pl.DataFrame:
        """LCOE base (moneda/kWh) para cada valor del parámetro, con los demás parámetros fijos."""
        self.validarParametroSensibilidad(parametro)
        if valores is None:
            valores = self.valoresSensibilidad(parametro)
        filas = []
        for valor in valores:
            central = CentralMareomotriz(**{**self.parametros, parametro: valor})
            energia = central.calcularEnergia(central.calcularPasos()["pasosPorAnio"])["energiaUtil_kWh"]
            lcoe = central.economia.lcoe(central.capex * central.numeroTurbinas, central.opex * central.numeroTurbinas, energia)
            filas.append({parametro: float(valor), f"LCOE_{self.moneda}_por_kWh": lcoe})
        return pl.DataFrame(filas)
