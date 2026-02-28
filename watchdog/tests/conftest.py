# watchdog/tests/conftest.py
"""
Shared fixtures per i test del watchdog.
Nessuna connessione reale a DB, Docker o GitHub — tutto viene mockato.
"""
import sys
import os
import pytest

# Aggiunge la directory watchdog al path Python così i moduli si trovano
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
