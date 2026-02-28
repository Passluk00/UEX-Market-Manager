# bot/tests/conftest.py
"""
Shared fixtures per i test del bot.
Nessuna connessione reale a DB o Discord — tutto viene mockato.
"""
import sys
import os
import pytest

# Aggiunge bot/ al path Python così i moduli si trovano
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Stub per ENCRYPTION_KEY richiesto da utils/cryptography.py all'import
os.environ.setdefault("ENCRYPTION_KEY", "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU=")
