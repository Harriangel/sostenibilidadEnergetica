# Historial de versiones

Este proyecto usa [versionado semántico](https://semver.org/lang/es/):
- **MAYOR:** cambia cómo se instala o se ejecuta, o la estructura.
- **MENOR:** se añade un módulo o una funcionalidad.
- **PARCHE:** correcciones.

Cada versión tiene su etiqueta (tag) de Git: `v1.0.0`, `v2.0.0`, etc.

Las versiones 1.0.0 a 3.0.0 se desarrollaron fuera de Git (octubre y noviembre de 2026) y se registraron después como commits independientes para conservar la trazabilidad. Las tres dan resultados idénticos en el cálculo del caudal de equipamiento.

## [Sin publicar]

### Documentación
- Especificaciones de energía solar en `docs/especificaciones/solar/`: recurso solar (posición del sol e irradiancia inclinada), F-Chart para ACS (correlación de Klein por defecto y la del informe como alternativa) y fotovoltaica por horas solares pico con comparación frente a PVWatts. Alberca y concentrador, pendientes de confirmar fuentes.

## [4.1.1]: corrección de un aviso de polars

### Corregido
- `ProcesadorCaudales.asignarPeriodosAnuales` usaba `is_in` con una serie del mismo tipo, obsoleto en polars (`DeprecationWarning`); ahora pasa la serie con `implode()`. Los resultados no cambian.

## [4.1.0]: central mareomotriz

Añade el módulo de energías del mar con la central mareomotriz y el módulo común de economía. La hidráulica no cambia.

### Añadido
- **Economía común** (`energias/comun/economia.py`, `IndicadoresEconomicos`), reutilizable por todas las tecnologías: factor de valor presente de una anualidad vencida (vida útil si la tasa es 0), factor de recuperación de capital, valor presente de costos y de energía, y LCOE por valor presente. Valida vida útil > 0 y tasa ≥ 0.
- **Central mareomotriz** (`energias/mar/mareomotriz.py`, `CentralMareomotriz`), según `docs/especificaciones/mar/Calculo_mareomotriz_LCOE.md` (secciones 3.1 a 3.4):
  - pasos de agua por turbina y año según el tipo de marea (diurna o semidiurna) y la dirección (unidireccional o bidireccional);
  - energía potencial y útil anual (J, kWh, MWh y GWh) y potencia media;
  - LCOE por valor presente con los intermedios (FVP, CRF, valores presentes) y una tabla polars de escenarios (base, A: CAPEX +15 %, B: energía −10 %) con su variación frente al caso base;
  - barrido de sensibilidad del LCOE frente a la tasa de descuento, la eficiencia, el desnivel o el CAPEX;
  - ampliaciones de la sección 7: número de turbinas (multiplica energía, CAPEX y OPEX) y disponibilidad (multiplica la energía útil);
  - validaciones con `ValueError`; tipo de marea y dirección sin distinguir mayúsculas ni tildes;
  - moneda como etiqueta, EUR por defecto.
- **Gráficas** (`energias/mar/graficadorMareomotriz.py`): barras del LCOE por escenario y sensibilidad del LCOE con el valor base marcado.
- **Consola:** `scripts/ejecutarMareomotriz.py`, que imprime las salidas como la sección 4 de la especificación y guarda tablas y gráficas en `outputs/mareomotriz/`.
- **Interfaz:** página `interfaz/pages/2_Mareomotriz.py` con entradas, métricas, tablas, gráficas, fórmulas en LaTeX, supuestos y descargas en CSV, PNG y SVG.
- **Pruebas:** `test_economia.py`, `test_mareomotriz.py` (valores del Excel con tolerancia 1e-9, casos borde, validaciones y ampliaciones), `test_graficadorMareomotriz.py` y pruebas de humo de la página.
- `energias/comun/unidades.py`: `joulesAKWh`; `energias/comun/graficos.py`: formatos de eje en porcentaje y en millones.

### Notas
- No se implementan las fórmulas alternativas de K31, K36 y K41 del Excel (sección 3.5 de la especificación): subestiman el LCOE.
- Las etiquetas usan las unidades correctas: LCOE en moneda/kWh (y moneda/MWh) y CAPEX en moneda por turbina; las leyendas del Excel tenían erratas.

## [4.0.0]: reestructuración multitecnología

Cambia la estructura y la forma de instalar y ejecutar el aplicativo. Los resultados numéricos son idénticos a los de la 3.0.0.

### Añadido
- **Paquete instalable** `energias/` con `pyproject.toml` (`python -m pip install -e .`), que también configura `pytest`.
- **Módulos comunes** en `energias/comun/`:
  - `unidades.py` (`Unidades`): factores W/kW/MW/GW y Wh/kWh/MWh/GWh, conversión entre unidades de energía y J↔Wh.
  - `graficos.py` (`Graficos`): guardado de figuras en png y svg, conversión a bytes y formatos de eje.
- **Consola:** `scripts/ejecutarHidraulica.py`, con los parámetros editables que antes estaban al final de `analisisCaudalDiseno.py`.
- **Interfaz multipágina:** `interfaz/app.py` es la página de inicio (descripción de la plataforma y tecnologías disponibles) e `interfaz/pages/1_Hidraulica.py` contiene la interfaz de la hidráulica con sus tres pestañas.
- **Pruebas automáticas** con `pytest` en `tests/`:
  - regresión de la hidráulica con los valores de referencia de la 3.0.0 (dos casos del módulo 1, canal, tubería forzada y Colebrook);
  - módulos comunes;
  - pruebas de humo de cada página con `streamlit.testing.v1.AppTest`.
- Nueva dependencia: `pytest`.

### Cambiado
- Los módulos de cálculo pasan de `scripts/` a `energias/hidraulica/` (con `git mv`, conservando su historial) y usan imports absolutos.
- `Graficador` usa `energias.comun.graficos` para guardar, convertir a bytes y dar formato a los ejes; `CalculadoraPotencia` toma los factores de `energias.comun.unidades`.
- Los datos pasan a `data/hidraulica/` y las salidas a `outputs/hidraulica/`, que se crea al guardar.
- Las claves de `st.session_state` y de los widgets de la página de la hidráulica llevan el prefijo `hidraulica_`.
- `README.md` y `CLAUDE.md` describen la nueva instalación y ejecución.

## [3.0.0]: canal de derivación y tubería forzada

### Añadido
- **Módulo 2, canal de derivación** (`disenoCanal.py`): sección trapezoidal por Manning.
  - Dos modos: dimensionar la profundidad para Qe o verificar una sección dada.
  - Pendiente por cotas o directa.
  - Coeficiente n por material.
  - Número de Froude con clasificación del flujo.
  - Lados renombrados x, y, z, w; A solo para el área.
- **Módulo 3, tubería forzada** (`disenoTuberiaForzada.py`): diámetro económico iterativo con tolerancia (5 % por defecto).
  - Factor de fricción por Colebrook-White o Swamee-Jain, más laminar.
  - Tabla de rugosidad de 10 materiales.
  - Costo por metro con moneda elegible (USD por defecto, con tasa de cambio).
  - Espesor de la pared.
- **Gráficas:** sección del canal, diagrama de Moody con el punto de operación y convergencia del diámetro.
- **Interfaz:** pestañas "1. Caudal de equipamiento", "2. Canal de derivación" y "3. Tubería forzada". Fórmulas en LaTeX, descargas en PNG, SVG y CSV, y guardado en `outputs/`.
- **Especificación de origen:** `Canal_de_derivación_y_tubería_forzada.xlsx`, con estas correcciones:
  - unidades de ν y μ;
  - f calculado con el caudal de diseño;
  - diámetro económico iterado hasta converger.

## [2.0.0]: interfaz Streamlit y gráfica de energía diaria

### Añadido
- **Interfaz web** (`interfazStreamlit.py`):
  - **Barra lateral:** fuente, archivo de `data/` o subido, parámetros del cálculo.
  - **Resultados:** métricas, pestañas con las gráficas, tablas y descargas.
  - **Guardado** en `outputs/`.
  - **Errores:** mensajes cuando el archivo no corresponde a la fuente.
- **Gráfica y CSV de la energía generada por día** con el caudal de equipamiento óptimo (`energiaDiariaClasificada`, `energiaDiariaCaudalOptimo.csv`).

### Cambiado
- `AnalisisCaudalDiseno` separa el cálculo de la presentación: `calcular()`, `crearFiguras()` y `guardarResultados()`. `ejecutar()` (consola) las usa y da los mismos resultados.
- `Graficador` usa la API `Figure` de matplotlib (sin `pyplot`) y devuelve figuras en lugar de solo guardarlas.
- `AnalisisCaudalDiseno` acepta `rutaArchivo` para procesar archivos subidos.
- Nueva dependencia: `streamlit`.

## [1.0.0]: análisis de caudal de diseño por consola

### Añadido
- **Lectura de caudales diarios** de dos fuentes: IDEAM (Colombia, DHIME) y CONAGUA (México, con metadatos antes del encabezado). Busca el encabezado y lee en UTF-8 con respaldo en latin-1.
- **Periodos hidrológicos de octubre a septiembre:**
  - excluye el 29 de febrero;
  - exige un mínimo de días con dato por periodo (300 por defecto);
  - completa los días faltantes;
  - numera los días de 1 a 365.
- **Curvas de caudal clasificado** por periodo y promedio.
- **Energía anual por caudal de equipamiento:**
  - caudal mínimo técnico por tipo de turbina (factor K);
  - eficiencia por turbina y generador o eficiencia total;
  - paso automático de Qe según el caudal máximo;
  - unidades W, kW, MW o GW.
- **Identificación del Qe de energía máxima.**
- **Gráficas** en PNG y SVG (caudales por periodo, caudales clasificados con promedio punteado, energía anual contra Qe) y **CSV de resultados** en `outputs/`.
- **README** con la descripción, la instalación y los parámetros.
