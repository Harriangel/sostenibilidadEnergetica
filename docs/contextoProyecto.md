# Contexto del proyecto: plataforma de diseño de centrales de energía renovable

## 1. Visión

El proyecto empezó como un aplicativo para el caudal de diseño de una pequeña central hidroeléctrica (ver `contextoAplicativo.md`). Ahora crece hacia una **plataforma en Python para el diseño de prefactibilidad de centrales de energía renovable**, con un módulo por tecnología.

Cada módulo:
- estima el recurso y la energía anual;
- dimensiona los componentes principales;
- calcula indicadores económicos comparables entre tecnologías, empezando por el LCOE.

Los cálculos de cada tecnología se estudian primero en Excel. Luego se convierten en una especificación en markdown, y de ahí en código probado contra los valores de ese Excel.

## 2. Tecnologías

| Tecnología | Estado del estudio | Estado en el aplicativo |
|---|---|---|
| Hidráulica (pequeña central) | En estudio | Implementada: caudal de equipamiento, canal de derivación, tubería forzada (v3.0.0; en `energias/hidraulica/` desde la v4.0.0) |
| Mareomotriz | Estudiada; especificación lista | Siguiente módulo (v4.1.0) |
| Solar fotovoltaica | Estudiada | Pendiente |
| Solar térmica | Estudiada | Pendiente |
| Solar de concentración | Estudiada | Pendiente |
| Eólica (en tierra) | Estudiada | Pendiente |
| Biomasa | Estudiada | Pendiente |
| Corrientes marinas | Por estudiar | Pendiente |
| Undimotriz (olas) | Por estudiar | Pendiente |
| Eólica marina (offshore) | Por estudiar | Pendiente |
| Geotermia | Por estudiar | Pendiente |

Las energías del mar (mareomotriz, corrientes marinas, undimotriz) se agrupan en `energias/mar/`. La eólica marina puede ir en `energias/eolica/` reutilizando la eólica en tierra.

## 3. Flujo de trabajo por tecnología

1. **Estudio** (Proyecto de Claude o chat): teoría y cálculos en Excel.
2. **Especificación** (`docs/especificaciones/<tecnologia>/`): un markdown con:
   - entradas con su celda, unidad y valor de ejemplo;
   - fórmulas celda por celda;
   - salidas con sus valores esperados;
   - pruebas de aceptación;
   - observaciones sobre el Excel.

   El Excel se guarda junto al markdown. El modelo de referencia es `docs/especificaciones/mar/Calculo_mareomotriz_LCOE.md`.
3. **Implementación** (Claude Code, en una rama `<tecnologia>`): clases en `energias/<tecnologia>/`, reutilizando `energias/comun/`.
4. **Pruebas** (`tests/`): reproducir los valores del Excel (tolerancia relativa 1e-9 cuando el cálculo es cerrado), más casos borde y validaciones.
5. **Interfaz:** una página de Streamlit por tecnología.
6. **Documentación:** README, `CHANGELOG.md`, este documento y `CLAUDE.md` si cambian las convenciones.
7. **Integración:** fusionar la rama en `main` y etiquetar la versión.

## 4. Arquitectura objetivo (a partir de la v4.0.0)

```
<repositorio>/
├── CLAUDE.md                      convenciones para Claude Code
├── README.md                      instalación, ejecución y módulos disponibles
├── CHANGELOG.md                   historial de versiones
├── pyproject.toml                 paquete instalable (pip install -e .) y configuración de pytest
├── requirements.txt
├── docs/
│   ├── contextoAplicativo.md      módulo hidráulico (historia, decisiones, pendientes)
│   ├── contextoProyecto.md        este documento
│   └── especificaciones/
│       ├── hidraulica/            Excel de canal y tubería; Excel de Colebrook
│       └── mar/                   especificación y Excel de la mareomotriz
├── energias/                      paquete de cálculo (sin Streamlit)
│   ├── comun/
│   │   ├── economia.py            valor presente, factor de recuperación de capital, LCOE
│   │   ├── unidades.py            factores W/kW/MW/GW y J↔Wh
│   │   └── graficos.py            guardado de figuras, conversión a bytes y formatos de eje
│   ├── hidraulica/                lector, procesador, calculadora, canal, tubería, clase principal
│   └── mar/
│       └── mareomotriz.py
├── interfaz/
│   ├── app.py                     página de inicio
│   └── pages/                     una página por tecnología
├── scripts/                       ejecución por consola de cada tecnología
├── data/<tecnologia>/             datos de entrada
├── outputs/<tecnologia>/          resultados (no se versionan)
└── tests/                         una prueba por módulo
```

Estado en la v4.0.0: la estructura está implementada salvo `energias/comun/economia.py` y `energias/mar/`, que llegan con la mareomotriz (v4.1.0). Convenciones adoptadas al implementarla:
- Script de consola por tecnología: `scripts/ejecutar<Tecnologia>.py` (por ejemplo `ejecutarHidraulica.py`), con los parámetros editables al inicio.
- Página por tecnología: `interfaz/pages/<n>_<Tecnologia>.py` (por ejemplo `1_Hidraulica.py`); el número fija el orden en la barra lateral.
- Las claves de `st.session_state` y de los widgets de cada página llevan el prefijo de la tecnología (`hidraulica_`, `mareomotriz_`).
- `outputs/<tecnologia>/` se crea al guardar resultados; en el repositorio solo se versiona `outputs/.gitkeep`.

Principios:
- **Cálculo separado de la presentación.** `energias/` no importa Streamlit, y las gráficas usan la API `Figure` de matplotlib. Así el cálculo se usa desde la consola, la interfaz y las pruebas.
- **Lo común, una sola vez.** El LCOE, el valor presente, las unidades y el guardado de figuras viven en `energias/comun/` y los reutilizan todas las tecnologías.
- **Validar, no devolver ceros.** Una entrada inválida lanza `ValueError` con un mensaje claro en español.
- **Reproducibilidad.** Cada módulo tiene pruebas con los valores de su Excel de origen.

## 5. Versionamiento

- **Rama principal:** `main`, que siempre funciona y pasa las pruebas.
- **Ramas de trabajo:** una por tema (`reestructuracion`, `mar/mareomotriz`, `solar/fotovoltaica`, etc.), fusionadas a `main` al terminar.
- **Commits:** en español, con prefijo de tipo: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- **Etiquetas:** versionado semántico (`vMAYOR.MENOR.PARCHE`) en cada versión publicada, con su entrada en `CHANGELOG.md`.

## 6. Hoja de ruta

| Versión | Contenido |
|---|---|
| 1.0.0 | Caudal de equipamiento por consola |
| 2.0.0 | Interfaz Streamlit y energía diaria |
| 3.0.0 | Canal de derivación y tubería forzada |
| 4.0.0 | Reestructuración multitecnología, módulos comunes y pruebas automáticas |
| 4.1.0 | Mareomotriz: energía potencial y LCOE |
| 4.x | LCOE para la hidráulica, pendientes del módulo hidráulico y nuevas tecnologías según avance el estudio |
