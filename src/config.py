# src/config.py
import os
import sys

CURRENT_VERSION = "3.4.12"

PROPELLANTS = {
    "Custom / Outro": None,
    "KNDX / KNSu (Sugar)": 1.137,
    "KNSB (Sorbitol)": 1.135,
    "Epoxy / KNO3": 1.160,
    "PVC / KNO3": 1.180,
    "Black Powder": 1.210,
    "APCP (Average)": 1.240,
    "Ethanol / LOX": 1.220,
    "Paraffin / N2O": 1.260
}

def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)