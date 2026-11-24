# Historial de versiones

Este proyecto usa [versionado semántico](https://semver.org/lang/es/):
- **MAYOR:** cambia cómo se instala o se ejecuta, o la estructura.
- **MENOR:** se añade un módulo o una funcionalidad.
- **PARCHE:** correcciones.

Cada versión tiene su etiqueta (tag) de Git: `v1.0.0`, `v2.0.0`, etc.

Las versiones 1.0.0 a 3.0.0 se desarrollaron fuera de Git (octubre y noviembre de 2026) y se registraron después como commits independientes para conservar la trazabilidad. Las tres dan resultados idénticos en el cálculo del caudal de equipamiento.

## [Sin publicar]

### Planeado
- **4.0.0:** reestructuración en un paquete multitecnología (`energias/`), con módulos comunes (economía, unidades, gráficas), pruebas automáticas con `pytest` e interfaz Streamlit multipágina.
- **4.1.0:** módulo de energías del mar con la central mareomotriz (energía potencial anual y LCOE con escenarios de sensibilidad).

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
