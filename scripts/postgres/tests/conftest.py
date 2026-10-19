"""Configuracao local dos testes PostgreSQL F0.66C."""

from pathlib import Path
import sys

POSTGRES_SCRIPTS = Path(__file__).resolve().parents[1]

if str(POSTGRES_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(POSTGRES_SCRIPTS))
