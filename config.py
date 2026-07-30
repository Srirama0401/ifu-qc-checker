"""
CONFIG — edit this file with your organization's approved master data.
This is the ONLY file you should need to touch to adapt the checker
to a different product / manufacturer / symbol set.
"""

CONFIG = {
    # ---- 2. Manufacturer Information ----
    "manufacturer_name": "Acme Medical Devices Inc.",
    "manufacturer_address": "123 Industrial Way, Springfield, USA",
    "ec_rep_address": "45 Regulatory Lane, Dublin, Ireland",
    "importer_address": None,  # set to a string if applicable, else None

    # ---- 1. Page Number Verification ----
    # Pattern used to find "Page X of Y" style footers/headers.
    "page_number_pattern": r"Page\s+(\d+)\s+of\s+(\d+)",

    # ---- 3. Regulatory Symbols ----
    # Text labels/captions expected near each required symbol.
    # (True graphical shape-matching is available as an optional
    # extension — see src/ifu_qc_checker.py:check_regulatory_symbols_by_image)
    "required_symbol_labels": [
        "Manufacturer",
        "Authorized Representative",
        "Date of manufacture",
        "Consult instructions for use",
        "Caution",
        "Temperature limit",
        "Keep dry",
        "CE",
    ],

    # ---- 4. Date Verification ----
    "required_date_labels": [
        "Manufacturing date",
        "Revision date",
        "Effective date",
        "Version date",
    ],
    # Expected display format, e.g. "01 Jan 2026"
    "date_display_regex": r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
}
