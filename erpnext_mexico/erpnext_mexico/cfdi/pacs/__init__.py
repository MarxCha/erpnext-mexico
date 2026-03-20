"""PAC adapters — auto-register on import."""
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.pacs.finkok_pac import FinkokPAC
from erpnext_mexico.cfdi.pacs.sw_sapien_pac import SWSapienPAC

PACDispatcher.register("Finkok", FinkokPAC)
PACDispatcher.register("SW Sapien", SWSapienPAC)
