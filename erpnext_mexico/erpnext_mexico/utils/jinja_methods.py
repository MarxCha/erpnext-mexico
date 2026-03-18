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

def get_qr_code_data_uri(data: str) -> str:
    """Generate a QR code as a base64 data URI for embedding in HTML/print formats."""
    try:
        import io
        import base64
        import qrcode

        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except ImportError:
        # Fallback: return an empty 1x1 pixel if qrcode not installed
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
