# Historial de versiones

Este proyecto usa [versionado semántico](https://semver.org/lang/es/):
- **MAYOR:** cambia cómo se instala o se ejecuta, o la estructura.
- **MENOR:** se añade un módulo o una funcionalidad.
- **PARCHE:** correcciones.

Cada versión tiene su etiqueta (tag) de Git: `v1.0.0`, `v2.0.0`, etc.

Las versiones 1.0.0 a 3.0.0 se desarrollaron fuera de Git (octubre y noviembre de 2026) y se registraron después como commits independientes para conservar la trazabilidad. Las tres dan resultados idénticos en el cálculo del caudal de equipamiento.

## [Sin publicar]

### Planeado
- **4.1.0:** módulo de energías del mar con la central mareomotriz (energía potencial anual y LCOE con escenarios de sensibilidad) y módulo común de economía (`energias/comun/economia.py`).

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
