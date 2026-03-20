"""Load ALL SAT test CSD certificates and try timbrado with each RFC."""
import os
import glob


# RFC -> (nombre, regimen, cp) from official SAT test data
TEST_RFCS = {
    "EKU9003173C9": ("ESCUELA KEMPER URGATE", "601", "42501"),
    "EWE1709045U0": ("EDGAR WALDO ERDMANN", "601", "42501"),
    "H&E951128469": ("HERRERIA & ELECTRICOS", "601", "06002"),
    "IIA040805DZ4": ("INDISTRIA ILUMINADORA DE ALMACENES", "601", "62661"),
    "IVD920810GU2": ("INNOVACION VALOR Y DESARROLLO", "601", "63901"),
    "IXS7607092R5": ("INTERNACIONAL XIMBO Y SABORES", "601", "23004"),
    "JES900109Q90": ("JIMENEZ ESTRADA SALAS", "601", "37161"),
    "KIJ0906199R1": ("KERNEL INDUSTIA JUGUETERA", "601", "28971"),
    "L&O950913MSA": ("LUCES & OBRAS", "601", "60922"),
    "S&S051221SE2": ("SUPER & SHAN", "601", "37800"),
    "URE180429TM6": ("UNIVERSIDAD ROBOTICA ESPAÑOLA", "601", "86991"),
    "XIA190128J61": ("XENON INDUSTRIAL ARTICLES", "601", "76343"),
}


def run():
    """Load all test CSD and attempt timbrado with each."""
    from satcfdi.pacs.finkok import Finkok
    from satcfdi.pacs import Environment
    from satcfdi.models import Signer
    from satcfdi.create.cfd import cfdi40

    pac = Finkok(
        username="marx_chavez@yahoo.com",
        password="fantok-cimde8-zofhyG",
        environment=Environment.TEST,
    )

    base_dir = "/tmp/all_csd_morales"
    results = []

    for rfc, (nombre, regimen, cp) in TEST_RFCS.items():
        # Find CSD files for this RFC
        rfc_dirs = glob.glob(os.path.join(base_dir, f"{rfc}_*"))
        if not rfc_dirs:
            results.append((rfc, "SKIP", "No directory found"))
            continue

        rfc_dir = rfc_dirs[0]
        csd_dirs = glob.glob(os.path.join(rfc_dir, "CSD_*"))
        if not csd_dirs:
            results.append((rfc, "SKIP", "No CSD directory"))
            continue

        csd_dir = csd_dirs[0]
        cer_files = glob.glob(os.path.join(csd_dir, "CSD_Sucursal_1_*.cer"))
        key_files = glob.glob(os.path.join(csd_dir, "CSD_Sucursal_1_*.key"))

        if not cer_files or not key_files:
            results.append((rfc, "SKIP", "No CSD cer/key files"))
            continue

        try:
            signer = Signer.load(
                certificate=open(cer_files[0], "rb").read(),
                key=open(key_files[0], "rb").read(),
                password="12345678a",
            )

            comprobante = cfdi40.Comprobante(
                emisor=cfdi40.Emisor(rfc=rfc, nombre=nombre, regimen_fiscal=regimen),
                lugar_expedicion=cp,
                receptor=cfdi40.Receptor(
                    rfc=rfc, nombre=nombre,
                    domicilio_fiscal_receptor=cp,
                    regimen_fiscal_receptor=regimen,
                    uso_cfdi="G03",
                ),
                metodo_pago="PUE", forma_pago="03", moneda="MXN", exportacion="01",
                conceptos=[cfdi40.Concepto(
                    clave_prod_serv="84111506", cantidad=1, clave_unidad="E48",
                    descripcion="Servicio de consultoria", valor_unitario=10000,
                    objeto_imp="02",
                    impuestos=cfdi40.Impuestos(traslados=[cfdi40.Traslado(
                        base=10000, impuesto="002", tipo_factor="Tasa",
                        tasa_o_cuota="0.160000", importe=1600,
                    )]),
                )],
            )
            comprobante.sign(signer)
            result = pac.stamp(comprobante)
            results.append((rfc, "SUCCESS", f"UUID={result.document_id}"))

        except Exception as e:
            error = str(e)[:80]
            results.append((rfc, "FAIL", error))

    # Print results
    print("\n" + "=" * 70)
    print("  TIMBRADO TEST RESULTS — ALL RFCs")
    print("=" * 70)
    for rfc, status, detail in results:
        icon = "OK" if status == "SUCCESS" else "XX" if status == "FAIL" else "--"
        print(f"  [{icon}] {rfc:16s} {status:8s} {detail}")
    print("=" * 70)

    successes = [r for r in results if r[1] == "SUCCESS"]
    if successes:
        print(f"\n  *** {len(successes)} RFC(s) TIMBRADOS EXITOSAMENTE ***")
        for rfc, _, uuid in successes:
            print(f"  {rfc}: {uuid}")
    else:
        print("\n  Ningun RFC logro timbrarse en este ambiente.")
