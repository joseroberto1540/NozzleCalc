# src/config.py
import os
import sys

# Esta variável será atualizada pelo seu script release.py
CURRENT_VERSION = "3.4.8"

# Dados de Propelentes (Global)
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
    """Obtém o caminho absoluto para recursos (funciona no PyInstaller)."""
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)