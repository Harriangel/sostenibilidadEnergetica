"""Configuración provisional: permite importar los módulos de scripts/ (estructura v3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
