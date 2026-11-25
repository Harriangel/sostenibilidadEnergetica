# Especificaciones de energía solar

Especificaciones para el módulo `energias/solar/`, construidas a partir de los scripts y documentos de los cursos de energía solar de la maestría (UNIR).

| Especificación | Tecnología | Origen | Estado |
|---|---|---|---|
| [`recursoSolar.md`](recursoSolar.md) | Común (térmica, fotovoltaica, concentración) | `GTI_optimized.py`, `GTI_comparison.py`, `graphics.py`; Anexo B del informe F-Chart | Implementada (v4.2.0) |
| [`termica/fChartAcs.md`](termica/fChartAcs.md) | Solar térmica: ACS | `F-Chart.py`; informe «Dimensionamiento de un sistema solar térmico para un hotel» | Implementada (v4.2.0) |
| [`fotovoltaica/horasSolaresPico.md`](fotovoltaica/horasSolaresPico.md) | Solar fotovoltaica | `Análisis de radiación diaria.xlsx` | Implementada (v4.2.0), salvo el lector de PVWatts (sección 4.1), que espera los archivos exportados |
| Calentamiento de albercas | Solar térmica | `dimSisTerAlb.py` | Pendiente: fuente de las constantes (sección 2) |
| Concentrador | Solar de concentración | `energiaDisponible.py` | Pendiente: alcance (sección 3) |

## 1. Decisiones

- **Posición del sol calculada.** Se calcula a la hora de cada registro del TMY (hh:30) con Spencer y Duffie-Beckman, y ya no se usa el archivo de SunEarthTools. El script original tomaba el acimut de las hh:00; con la corrección, la inclinación óptima de Ciudad de México pasa de 18° a 19° y la radiación anual sube entre 0,3 % y 0,7 %.
- **F-Chart.** Por defecto se usa la correlación de Klein, Beckman y Duffie con la corrección para ACS. La correlación exponencial del informe queda como alternativa para reproducirlo.
- **Gráficas.** Con matplotlib (API `Figure`) y `energias/comun/graficos.py`, no con plotly.
- **Datos.** El TMY de NSRDB se guarda en `data/solar/`. La clave de la API de NREL no se versiona: se lee de una variable de entorno (`NREL_API_KEY`) si se implementa la descarga.

## 2. Pendiente: calentamiento de albercas (`dimSisTerAlb.py`)

Fórmulas del script:

```
Qpool       = C · Ap · (Tw − Ta)                               [kW]     demanda térmica
Epool       = Qpool · 24                                        [kWh/día]
η colector  = η0 · (1 − bu·u) − (b1 + b2·u) · (Ti − Ta) / G              eficiencia con viento
Ac          = Epool / (ηsis · HT)                               [m²]
Ecubierta   = Epool · (1 − r)                                           alberca cubierta
```

Valores del ejemplo: C = 0,089; Ap = 50 m²; Tw = 28 °C; Ta = 24 °C; η0 = 0,91; bu = 0,042 s/m; u = 1,34 m/s; b1 = 11,979 W/m²·°C; b2 = 14,289; Ti = 28 °C; G = 1000 W/m²; ηsis = 0,6; HT = 5,5 kWh/m²·día; r = 0,6.

Resultados del script: Qpool = 17,8 kW; Epool = 427,2 kWh/día; η = 73,43 %; Ac = 129,45 m²; con cubierta, 170,88 kWh/día y 51,78 m².

Por confirmar antes de especificar:
- Fuente y unidades de C (el script lo usa en kW/m²·°C, es decir, 89 W/m²·°C) y de b2 (W·s/m³·°C para que b2·u quede en W/m²·°C).
- Si el área debe usar la eficiencia del colector calculada (hoy no se usa: el área usa ηsis = 0,6).
- Si hay un informe o Excel del ejercicio con valores de referencia.

## 3. Pendiente: concentrador (`energiaDisponible.py`)

El script implementa solo el concentrador lineal, con entradas por teclado:

```
Aa = W · L                      área de apertura          [m²]
Ar = π · Dr · L                 área del receptor (tubo)  [m²]
C  = Aa / Ar                    relación de concentración
E  = DNI · η0 · C / 1000        flujo sobre el receptor   [kW/m²]
```

El script usa π ≈ 3,1416 y llama «energía» al flujo. No considera pérdidas térmicas del receptor.

Por confirmar:
- Si se implementan también los concentradores parabólico (disco) y esférico que aparecen en el menú, y con qué fórmulas (la propuesta es tomarlas de Duffie y Beckman, cap. 7).
- Si hay Excel o informe del curso con valores de referencia.
- Si se agrega la potencia útil del receptor con pérdidas (Qu = Aa·η0·DNI − Ar·UL·(Tr − Ta)) y la energía anual con la DNI del TMY.

## 4. Seguridad

`importData.py` (carpeta «Calentamiento solar a gran escala» del repositorio de la maestría) tiene escrita una clave de la API de NREL y un correo. Ese archivo está publicado en GitHub: la clave debe revocarse y no debe copiarse a esta plataforma.
