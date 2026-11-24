r"""Ejecución por consola del módulo hidráulico (caudal de equipamiento).

Uso, desde la raíz del repositorio y con el paquete instalado (python -m pip install -e .):
    python scripts\ejecutarHidraulica.py

Edita los parámetros de abajo. Los datos se leen de data/hidraulica/ y los resultados
(csv, png y svg) se guardan en outputs/hidraulica/.
"""
from energias.hidraulica.analisisCaudalDiseno import AnalisisCaudalDiseno

# Parámetros editables
parametros = {
    "fuente": "CONAGUA",          # IDEAM (Colombia) o CONAGUA (México)
    "nombreArchivo": None,        # None usa el archivo por defecto de la fuente; o ej. "SAACP.csv"
    "minDiasPorPeriodo": 300,     # días con dato mínimos para incluir un periodo
    "saltoNeto": 150,             # metros
    "tipoTurbina": "Francis",     # Pelton, Ossberger, Kaplan, Semikaplan, Francis o Hélice
    "unidadEnergia": "kW",        # W, kW, MW o GW (la energía se expresa en Wh, kWh, MWh o GWh)
    "densidadAgua": 1000,         # kg/m³
    "gravedad": 9.8,              # m/s²
    "eficienciaTurbina": 0.85,    # ηg (se ignora si se indica eficienciaTotal)
    "eficienciaGenerador": 0.95,  # ηG (se ignora si se indica eficienciaTotal)
    "eficienciaTotal": 0.88,      # ηg*ηG; con None se usa ηg*ηG
    "pasoQe": None,               # None: automático según el caudal máximo; o un valor en m³/s
}

if __name__ == "__main__":
    AnalisisCaudalDiseno(**parametros).ejecutar()
