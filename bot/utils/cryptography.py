import os
from cryptography.fernet import Fernet


_key = os.getenv("ENCRYPTION_KEY")
if not _key:
    raise ValueError("ENCRYPTION_KEY non trovata nel file .env!")

_cipher_suite = Fernet(_key.encode())

def encrypt(text: str) -> str:
    """Trasforma testo leggibile in una stringa criptata."""
    if not text: return None
    return _cipher_suite.encrypt(text.encode()).decode()

def decrypt(encrypted_text: str) -> str:
    """Trasforma una stringa criptata nel testo originale."""
    if not encrypted_text: return None
    try:
        return _cipher_suite.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return encrypted_text