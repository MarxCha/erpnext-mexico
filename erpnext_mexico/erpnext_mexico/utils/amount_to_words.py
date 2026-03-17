"""Conversión de montos a texto en español mexicano para CFDI."""

UNITS = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
TEENS = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
         "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
TENS = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
        "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
HUNDREDS = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
            "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

CURRENCY_NAMES = {
    "MXN": ("PESO", "PESOS", "M.N."),
    "USD": ("DÓLAR", "DÓLARES", "USD"),
    "EUR": ("EURO", "EUROS", "EUR"),
}

def convert(amount: float, currency: str = "MXN") -> str:
    """Convierte monto a texto. Ej: 1500.50 → 'MIL QUINIENTOS PESOS 50/100 M.N.'"""
    if amount < 0:
        return "MENOS " + convert(abs(amount), currency)

    integer_part = int(amount)
    decimal_part = round((amount - integer_part) * 100)

    singular, plural, suffix = CURRENCY_NAMES.get(currency, ("PESO", "PESOS", "M.N."))
    currency_word = singular if integer_part == 1 else plural

    if integer_part == 0:
        words = "CERO"
    else:
        words = _number_to_words(integer_part)

    return f"{words} {currency_word} {decimal_part:02d}/100 {suffix}"


def _number_to_words(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "CIEN"
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    if n < 100:
        unit = n % 10
        ten = n // 10
        if unit == 0:
            return TENS[ten]
        if ten == 2:
            return f"VEINTI{UNITS[unit]}"
        return f"{TENS[ten]} Y {UNITS[unit]}"
    if n < 1000:
        hundred = n // 100
        remainder = n % 100
        if remainder == 0:
            return "CIEN" if hundred == 1 else HUNDREDS[hundred]
        return f"{HUNDREDS[hundred]} {_number_to_words(remainder)}"
    if n < 1_000_000:
        thousands = n // 1000
        remainder = n % 1000
        prefix = "MIL" if thousands == 1 else f"{_number_to_words(thousands)} MIL"
        if remainder == 0:
            return prefix
        return f"{prefix} {_number_to_words(remainder)}"
    if n < 1_000_000_000:
        millions = n // 1_000_000
        remainder = n % 1_000_000
        prefix = "UN MILLÓN" if millions == 1 else f"{_number_to_words(millions)} MILLONES"
        if remainder == 0:
            return prefix
        return f"{prefix} {_number_to_words(remainder)}"
    return str(n)
