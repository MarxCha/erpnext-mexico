# -*- coding: utf-8 -*-
"""
Entrypoint for ERPNext seed data pipeline.

Usage:
  bench --site erpnext-mexico.localhost execute erpnext_mexico.seed.run.run
  bench --site erpnext-mexico.localhost execute erpnext_mexico.seed.run.run --kwargs '{"phase":"master_data"}'
  bench --site erpnext-mexico.localhost execute erpnext_mexico.seed.run.run --kwargs '{"phase":"transactions"}'
  bench --site erpnext-mexico.localhost execute erpnext_mexico.seed.run.run --kwargs '{"phase":"verify"}'
"""


def run(phase="all"):
    print("\n" + "#" * 60)
    print("  ERPNext Mexico — Seed Data Pipeline")
    print("#" * 60)

    if phase in ("all", "master_data"):
        from erpnext_mexico.seed.master_data import run as run_master
        run_master()

    if phase in ("all", "transactions"):
        from erpnext_mexico.seed.transactions import run as run_txn
        run_txn()

    if phase in ("all", "verify"):
        from erpnext_mexico.seed.verify import run as run_verify
        run_verify()

    print("\n" + "#" * 60)
    print("  Pipeline complete.")
    print("#" * 60)
