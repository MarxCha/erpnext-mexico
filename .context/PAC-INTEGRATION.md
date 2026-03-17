# PAC-INTEGRATION — Guía de Integración con PACs

## Biblioteca Core: satcfdi

**PyPI**: `pip install satcfdi` (v4.8.2+)
**GitHub**: github.com/SAT-CFDI/python-satcfdi
**Licencia**: MIT
**Estado**: Activamente mantenido (último release: marzo 2026)

### Capacidades de satcfdi
- Generación XML CFDI 4.0 completo (todos los tipos: I, E, T, N, P)
- Firma digital con CSD (RSA-SHA256)
- Timbrado vía 5 PACs integrados: Comercio Digital, Diverza, Finkok, Prodigia, SW Sapien
- Cancelación de CFDI
- Descarga masiva del SAT (FIEL requerida)
- Validación de RFC contra SAT
- Complementos: Pagos 2.0, Nómina 1.2, Carta Porte 3.1, Comercio Exterior, y más
- Generación de PDF/HTML desde XML timbrado
- Generación de DIOT y Contabilidad electrónica

### Ejemplo básico de uso
```python
from satcfdi.models import Signer
from satcfdi.create.cfd import cfdi40
from satcfdi.pacs import finkok

# Cargar certificado CSD
signer = Signer.load(
    certificate=open('CSD001_EKU9003173C9.cer', 'rb').read(),
    key=open('CSD001_EKU9003173C9.key', 'rb').read(),
    password='12345678a'
)

# Construir CFDI
invoice = cfdi40.Comprobante(
    emisor=cfdi40.Emisor(
        rfc='EKU9003173C9',
        nombre='ESCUELA KEMPER URGATE',
        regimen_fiscal='601'
    ),
    receptor=cfdi40.Receptor(
        rfc='XAXX010101000',
        nombre='PÚBLICO EN GENERAL',
        uso_cfdi='S01',
        domicilio_fiscal_receptor='42501',
        regimen_fiscal_receptor='616'
    ),
    conceptos=[
        cfdi40.Concepto(
            clave_prod_serv='01010101',
            cantidad=1,
            clave_unidad='H87',
            descripcion='Producto de prueba',
            valor_unitario=100.00,
            objeto_imp='02',
            impuestos=cfdi40.Impuestos(
                traslados=[cfdi40.Traslado(
                    impuesto='002', tipo_factor='Tasa',
                    tasa_o_cuota='0.160000', base=100.00
                )]
            )
        )
    ],
    forma_pago='01',
    metodo_pago='PUE',
    tipo_de_comprobante='I',
    moneda='MXN',
    lugar_expedicion='42501',
)

# Firmar
invoice.sign(signer)

# Timbrar con Finkok
env = finkok.Environment(
    username='usuario@test.com',
    password='password',
    environment='test'  # 'production' para real
)
result = env.stamp(invoice)

# Resultado
print(result.uuid)          # UUID del CFDI
print(result.xml)           # XML timbrado completo
print(result.fecha_timbrado)
```

---

## PAC Recomendado #1: Finkok / Quadrum

**URL**: finkok.com / wiki.finkok.com
**API**: SOAP (via satcfdi wrapper)
**Sandbox**: demo-facturacion.finkok.com (gratuito, ilimitado)
**Pricing**: Desde $150 MXN/mes por 500 timbres. Paquete 1,000 timbres ~$250 MXN

### Registro sandbox
1. Ir a demo-facturacion.finkok.com
2. Crear cuenta con email
3. Usar credenciales en satcfdi:
```python
from satcfdi.pacs import finkok
env = finkok.Environment(username='email', password='pass', environment='test')
```

### Servicios disponibles
- `stamp(cfdi)` — Timbrar CFDI
- `cancel(uuid, rfc, certificate, reason)` — Cancelar
- `get_receipt(uuid)` — Obtener acuse
- `query_pending(rfc)` — Consultar cancelaciones pendientes

---

## PAC Recomendado #2: SW Sapien (Smarter Web)

**URL**: sw.com.mx / developers.sw.com.mx
**API**: REST (nativa, más moderna que SOAP)
**Sandbox**: api.test.sw.com.mx (gratuito)
**Pricing**: Desde $250 MXN/año. Velocidad 70-100ms por timbre.

### Registro sandbox
1. Ir a developers.sw.com.mx
2. Registrar cuenta de desarrollo
3. Obtener token de autenticación:
```python
from satcfdi.pacs import sw_sapien
env = sw_sapien.Environment(username='email', password='pass', environment='test')
```

### Ventajas de SW Sapien
- API REST moderna (más fácil de debuggear que SOAP)
- SDK oficial Python: `pip install sw-sdk-python`
- Programa de distribuidores con margen de reventa
- Timbrado más rápido (70-100ms vs ~200ms de Finkok)

---

## PAC Alternativo #3: Facturama

**URL**: facturama.mx / apisandbox.facturama.mx
**API**: REST
**Sandbox**: 15 timbres gratuitos
**Pricing**: $1,500 MXN/año + timbres adicionales
**Nota**: NO integrado en satcfdi — requiere wrapper REST directo

### Integración directa
```python
import requests

class FacturamaPAC:
    BASE_URL = "https://apisandbox.facturama.mx"  # o api.facturama.mx
    
    def __init__(self, username, password):
        self.auth = (username, password)
    
    def stamp(self, xml_string):
        response = requests.post(
            f"{self.BASE_URL}/2/cfd",
            json={"Content": xml_string},
            auth=self.auth
        )
        return response.json()
```

---

## Diseño Multi-PAC (Strategy Pattern)

```python
# erpnext_mexico/cfdi/pac_interface.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class StampResult:
    uuid: str
    xml_stamped: str
    fecha_timbrado: str
    sello_sat: str
    no_certificado_sat: str
    cadena_original_tfd: str

@dataclass
class CancelResult:
    success: bool
    acuse_xml: str
    status: str  # "Cancelado", "EnProceso", "Rechazado"

class PACInterface(ABC):
    @abstractmethod
    def stamp(self, xml_signed: str) -> StampResult:
        """Enviar XML firmado al PAC para timbrado."""
        ...
    
    @abstractmethod
    def cancel(self, uuid: str, rfc: str, certificate: bytes,
               key: bytes, password: str, reason: str,
               substitute_uuid: Optional[str] = None) -> CancelResult:
        """Cancelar un CFDI timbrado."""
        ...
    
    @abstractmethod
    def get_status(self, uuid: str, rfc_emisor: str, rfc_receptor: str,
                   total: str) -> str:
        """Consultar estado de un CFDI ante el SAT."""
        ...

# erpnext_mexico/cfdi/pac_dispatcher.py
import frappe
from .pac_interface import PACInterface

class PACDispatcher:
    _registry: dict[str, type[PACInterface]] = {}
    
    @classmethod
    def register(cls, name: str, pac_class: type[PACInterface]):
        cls._registry[name] = pac_class
    
    @classmethod
    def get_pac(cls, company: str) -> PACInterface:
        settings = frappe.get_cached_doc("MX CFDI Settings", {"company": company})
        pac_name = settings.pac_provider
        if pac_name not in cls._registry:
            frappe.throw(f"PAC '{pac_name}' no está registrado")
        credentials = frappe.get_doc("MX PAC Credentials", settings.pac_credentials)
        return cls._registry[pac_name](
            username=credentials.username,
            password=credentials.get_password("password"),
            environment=settings.pac_environment
        )

# erpnext_mexico/cfdi/pacs/finkok_pac.py
from satcfdi.pacs import finkok
from ..pac_interface import PACInterface, StampResult, CancelResult

class FinkokPAC(PACInterface):
    def __init__(self, username, password, environment):
        self.env = finkok.Environment(
            username=username, password=password,
            environment='test' if environment == 'Test' else 'production'
        )
    
    def stamp(self, xml_signed: str) -> StampResult:
        result = self.env.stamp(xml_signed)
        return StampResult(
            uuid=result.uuid,
            xml_stamped=result.xml,
            fecha_timbrado=str(result.fecha_timbrado),
            sello_sat=result.sello_sat,
            no_certificado_sat=result.no_certificado_sat,
            cadena_original_tfd=result.cadena_original,
        )
    
    def cancel(self, uuid, rfc, certificate, key, password, reason,
               substitute_uuid=None):
        # ... implementación via satcfdi
        ...

# Registro en hooks o __init__.py
PACDispatcher.register("Finkok", FinkokPAC)
PACDispatcher.register("SW Sapien", SWSapienPAC)
PACDispatcher.register("Facturama", FacturamaPAC)
```

---

## CSD de Prueba del SAT

### Persona Moral (para desarrollo/testing)
- **RFC**: EKU9003173C9
- **Nombre**: ESCUELA KEMPER URGATE
- **Contraseña CSD**: 12345678a
- Descargar de: portalsat.plataforma.sat.gob.mx (ambiente de pruebas)
- Archivos: `CSD001_EKU9003173C9.cer` + `CSD001_EKU9003173C9.key`

### Persona Física (para desarrollo/testing)
- **RFC**: CACX7605101P8
- **Nombre**: XOCHILT CASAS CHAVEZ
- **Contraseña CSD**: 12345678a

### Notas importantes
- Los CSD de prueba SOLO funcionan en sandbox de PACs
- En producción, cada empresa debe usar su propio CSD emitido por el SAT
- Los CSD expiran (vigencia 4 años) — implementar alerta de expiración
- La contraseña del .key NUNCA debe almacenarse en texto plano
  → usar `frappe.utils.password.get_decrypted_password()`
