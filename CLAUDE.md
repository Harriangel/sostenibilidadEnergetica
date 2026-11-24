# CLAUDE.md

Plataforma en Python para el diseño de prefactibilidad de centrales de energía renovable, con un módulo por tecnología. Antes de trabajar, lee `docs/contextoProyecto.md` (visión, flujo de trabajo y arquitectura) y, si tocas la hidráulica, `docs/contextoAplicativo.md`.

## Entorno

- Windows, Python 3.13, PowerShell. Entorno virtual en `.venv`.
- Usa `python -m <herramienta>` (`python -m pip`, `python -m pytest`, `python -m streamlit`): con el Python de la Microsoft Store los ejecutables no siempre quedan en el PATH.
- Dependencias en `requirements.txt`; si agregas una, regístrala ahí.

## Convenciones de código

- **Idioma:** identificadores, docstrings, comentarios, mensajes y documentación en español.
- **Nombres:** variables, funciones, métodos y archivos `.py` en camelCase (`caudalEquipamiento`, `disenoCanal.py`); clases en PascalCase (`DisenoCanal`). Si una especificación trae nombres en snake_case, tradúcelos a camelCase.
- **Programación orientada a objetos:** una clase por responsabilidad. Cada tecnología tiene una clase principal que orquesta el cálculo.
- **Datos:** `polars`, no `pandas`. **Gráficas:** `matplotlib` con la API `Figure` (no `pyplot`) en el código de cálculo.
- **Cálculo separado de la interfaz:** el paquete de cálculo no importa Streamlit. Las clases devuelven dataframes, diccionarios y figuras; imprimir y guardar son pasos aparte.
- **Validación:** ante entradas inválidas lanza `ValueError` con un mensaje claro en español. Nunca devuelvas 0 en silencio.
- **Parámetros, no números mágicos:** las constantes de una especificación van como parámetros con valor por defecto o como atributos de clase con nombre.
- **Unidades:** indícalas en nombres de columnas, etiquetas y docstrings (`EnergiaAnual_kWh`, "Caudal (m³/s)"). Las unidades de energía elegibles son W/Wh, kW/kWh, MW/MWh y GW/GWh.
- **Moneda:** elegible por el usuario; USD por defecto, salvo que la especificación de la tecnología use otra.

## Pruebas

- `pytest` en `tests/`, una prueba por módulo.
- Todo módulo nuevo reproduce los valores de su Excel de origen (tolerancia relativa 1e-9 si el cálculo es cerrado) e incluye casos borde y validaciones.
- Los resultados de referencia de la hidráulica (`docs/contextoAplicativo.md`, sección 7) deben seguir pasando.
- Ejecuta `python -m pytest` antes de cada commit; no hagas commit con pruebas fallando.

## Documentación

- Cada cambio funcional actualiza `README.md` y `CHANGELOG.md` (sección "Sin publicar" hasta etiquetar).
- Las especificaciones de cada tecnología, con su Excel, van en `docs/especificaciones/<tecnologia>/`.

## Git

- Trabaja en una rama por tema y fusiona a `main` cuando las pruebas pasen.
- Commits en español con prefijo de tipo (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`), pequeños y con un solo propósito.
- Etiquetas con versionado semántico.
- **Pregunta antes de** hacer push, fusionar a `main`, crear etiquetas o reescribir historial.
- No se versionan `.venv/`, `__pycache__/` ni el contenido de `outputs/`.

## Ejecución

> Esta sección describe la estructura previa a la reestructuración (v3.0.0). Actualízala al completar la v4.0.0.

```powershell
python -m pip install -r requirements.txt
python scripts\analisisCaudalDiseno.py                  # consola (módulo 1)
python -m streamlit run scripts\interfazStreamlit.py     # interfaz web
```
