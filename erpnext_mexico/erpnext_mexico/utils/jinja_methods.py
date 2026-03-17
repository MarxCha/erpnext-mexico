"""Métodos Jinja para print formats de CFDI."""

def amount_to_words_mx(amount, currency="MXN"):
    """Convierte un monto numérico a texto en español mexicano.
    Ejemplo: 1500.50 → "MIL QUINIENTOS PESOS 50/100 M.N."
    """
    from erpnext_mexico.utils.amount_to_words import convert
    return convert(amount, currency)

def format_rfc(rfc):
    """Formatea RFC para display."""
    return (rfc or "").strip().upper()
