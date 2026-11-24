import math


class DisenoCanal:
    """Canal de derivación de sección trapezoidal (ecuación de Chezy-Manning).

    Lados de la sección:
        x = ancho superior (espejo de agua)
        y = ancho de la base
        z = profundidad del agua
        w = longitud del lado inclinado (talud)
    La letra A se usa únicamente para el área de la sección.
    """

    # Coeficiente de rugosidad de Manning n (valores de los comentarios del Excel)
    coeficientesManning = {
        "Concreto sin pulir": 0.014,
        "Canal excavado": 0.025,
    }

    def __init__(self, coeficienteManning: float, pendiente: float, gravedad: float = 9.8):
        if coeficienteManning <= 0:
            raise ValueError("El coeficiente de Manning n debe ser positivo.")
        if pendiente <= 0:
            raise ValueError("La pendiente debe ser positiva (la cota aguas arriba debe superar a la de aguas abajo).")
        self.coeficienteManning = coeficienteManning
        self.pendiente = pendiente
        self.gravedad = gravedad

    @staticmethod
    def calcularPendiente(cotaAguasArriba: float, cotaAguasAbajo: float, longitud: float) -> float:
        """s = (cota aguas arriba - cota aguas abajo) / L."""
        if longitud <= 0:
            raise ValueError("La longitud del canal debe ser positiva.")
        return (cotaAguasArriba - cotaAguasAbajo) / longitud

    def calcularSeccion(self, x: float, y: float, z: float) -> dict:
        """Geometría de la sección: lado inclinado w, área A, perímetro mojado Pm y radio hidráulico Rh."""
        if y <= 0 or z <= 0:
            raise ValueError("La base y y la profundidad z deben ser positivas.")
        if x < y:
            raise ValueError("El ancho superior x no puede ser menor que la base y.")
        proyeccionTalud = (x - y) / 2
        w = math.hypot(z, proyeccionTalud)
        area = (x + y) / 2 * z
        perimetroMojado = 2 * w + y
        return {
            "x": x,
            "y": y,
            "z": z,
            "w": w,
            "proyeccionTalud": proyeccionTalud,
            "talud": proyeccionTalud / z,
            "A": area,
            "Pm": perimetroMojado,
            "Rh": area / perimetroMojado,
        }

    def calcularCaudal(self, seccion: dict) -> float:
        """Q = Rh^(2/3) * A * s^(1/2) / n."""
        return seccion["Rh"] ** (2 / 3) * seccion["A"] * math.sqrt(self.pendiente) / self.coeficienteManning

    @staticmethod
    def clasificarFlujo(froude: float) -> str:
        if froude < 0.8:
            return "subcrítico"
        if froude <= 1.2:
            return "cercano al crítico (inestable; conviene evitarlo)"
        return "supercrítico"

    def evaluarSeccion(self, x: float, y: float, z: float) -> dict:
        """Capacidad de una sección dada (cálculo directo del Excel) con v y número de Froude."""
        seccion = self.calcularSeccion(x, y, z)
        caudal = self.calcularCaudal(seccion)
        velocidad = caudal / seccion["A"]
        profundidadHidraulica = seccion["A"] / seccion["x"]
        froude = velocidad / math.sqrt(self.gravedad * profundidadHidraulica)
        seccion.update(
            {
                "Q": caudal,
                "v": velocidad,
                "profundidadHidraulica": profundidadHidraulica,
                "Froude": froude,
                "tipoFlujo": self.clasificarFlujo(froude),
            }
        )
        return seccion

    def dimensionarParaCaudal(self, caudalDiseno: float, base: float, talud: float) -> dict:
        """Profundidad normal z para un caudal de diseño dado la base y y el talud
        (proyección horizontal / altura). Se resuelve la ecuación de Manning por bisección."""
        if caudalDiseno <= 0:
            raise ValueError("El caudal de diseño debe ser positivo.")
        if talud < 0:
            raise ValueError("El talud no puede ser negativo.")

        def caudalConProfundidad(z: float) -> float:
            return self.calcularCaudal(self.calcularSeccion(base + 2 * talud * z, base, z))

        limiteSuperior = 1.0
        while caudalConProfundidad(limiteSuperior) < caudalDiseno:
            limiteSuperior *= 2
            if limiteSuperior > 1e4:
                raise ValueError("No se encontró una profundidad que conduzca el caudal de diseño.")
        limiteInferior = 1e-9
        for _ in range(200):
            punto = (limiteInferior + limiteSuperior) / 2
            if caudalConProfundidad(punto) < caudalDiseno:
                limiteInferior = punto
            else:
                limiteSuperior = punto
        profundidad = (limiteInferior + limiteSuperior) / 2
        return self.evaluarSeccion(base + 2 * talud * profundidad, base, profundidad)
