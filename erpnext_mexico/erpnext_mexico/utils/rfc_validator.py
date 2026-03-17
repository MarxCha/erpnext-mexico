"""
Validador de RFC mexicano.
Soporta RFC de persona moral (12 chars) y persona física (13 chars).
Incluye validación de dígito verificador.
"""

import re

# Regex para RFC personas morales (12 caracteres)
RFC_MORAL_PATTERN = re.compile(
    r"^[A-ZÑ&]{3}"       # 3 letras (razón social)
    r"\d{6}"              # 6 dígitos (fecha constitución AAMMDD)
    r"[A-Z0-9]{3}$"      # 3 caracteres alfanuméricos (homoclave)
)

# Regex para RFC personas físicas (13 caracteres)
RFC_FISICA_PATTERN = re.compile(
    r"^[A-ZÑ&]{4}"       # 4 letras (apellidos + nombre)
    r"\d{6}"              # 6 dígitos (fecha nacimiento AAMMDD)
    r"[A-Z0-9]{3}$"      # 3 caracteres alfanuméricos (homoclave)
)

# RFC genéricos especiales
RFC_PUBLICO_GENERAL = "XAXX010101000"
RFC_EXTRANJERO = "XEXX010101000"

# Tabla de valores para dígito verificador
_DIGIT_MAP = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15, "G": 16, "H": 17, "I": 18,
    "J": 19, "K": 20, "L": 21, "M": 22, "N": 23, "&": 24, "O": 25, "P": 26, "Q": 27,
    "R": 28, "S": 29, "T": 30, "U": 31, "V": 32, "W": 33, "X": 34, "Y": 35, "Z": 36,
    " ": 37, "Ñ": 38,
}


def validate_rfc(rfc: str) -> tuple[bool, str]:
    """
    Valida un RFC mexicano.
    
    Args:
        rfc: RFC a validar (se convierte a mayúsculas automáticamente).
        
    Returns:
        Tupla (es_válido, mensaje_error).
    """
    if not rfc:
        return False, "RFC vacío"

    rfc = rfc.strip().upper()

    # RFC genéricos son siempre válidos
    if rfc in (RFC_PUBLICO_GENERAL, RFC_EXTRANJERO):
        return True, ""

    # Validar longitud
    if len(rfc) not in (12, 13):
        return False, f"RFC debe tener 12 o 13 caracteres, tiene {len(rfc)}"

    # Validar formato
    if len(rfc) == 12:
        if not RFC_MORAL_PATTERN.match(rfc):
            return False, "Formato de RFC persona moral inválido"
    else:
        if not RFC_FISICA_PATTERN.match(rfc):
            return False, "Formato de RFC persona física inválido"

    # Validar dígito verificador
    if not _validate_check_digit(rfc):
        return False, "Dígito verificador inválido"

    return True, ""


def get_rfc_type(rfc: str) -> str:
    """
    Determina el tipo de RFC.
    
    Returns:
        "moral", "fisica", "publico_general", "extranjero", o "desconocido"
    """
    rfc = rfc.strip().upper()
    if rfc == RFC_PUBLICO_GENERAL:
        return "publico_general"
    if rfc == RFC_EXTRANJERO:
        return "extranjero"
    if len(rfc) == 12:
        return "moral"
    if len(rfc) == 13:
        return "fisica"
    return "desconocido"


def _validate_check_digit(rfc: str) -> bool:
    """Valida el dígito verificador del RFC (último carácter)."""
    # Pad a 13 caracteres para persona moral
    padded = (" " + rfc) if len(rfc) == 12 else rfc

    # Calcular suma ponderada (posiciones 13 a 2)
    total = 0
    for i, char in enumerate(padded[:-1]):
        value = _DIGIT_MAP.get(char, 0)
        total += value * (13 - i)

    # Módulo 11
    remainder = total % 11
    if remainder == 0:
        expected = "0"
    else:
        check = 11 - remainder
        expected = "A" if check == 10 else str(check)

    return padded[-1] == expected
