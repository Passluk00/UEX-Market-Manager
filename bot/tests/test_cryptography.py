# bot/tests/test_cryptography.py
"""
Tests per bot/utils/cryptography.py

Copre:
- encrypt()  — testo normale, None, stringa vuota, output diverso dall'input
- decrypt()  — testo cifrato valido, None, stringa non cifrata (fallback), testo vuoto
- roundtrip  — encrypt → decrypt restituisce il testo originale
"""

import os
import pytest
from cryptography.fernet import Fernet


# Genera una chiave di test fissa (non viene usata quella di produzione)
_TEST_KEY = Fernet.generate_key().decode()
os.environ["ENCRYPTION_KEY"] = _TEST_KEY


class TestEncrypt:

    def test_returns_non_empty_string(self):
        """encrypt() ritorna una stringa non vuota."""
        from utils.cryptography import encrypt
        result = encrypt("hello")
        assert result is not None
        assert len(result) > 0

    def test_output_differs_from_input(self):
        """L'output è diverso dall'input originale (è cifrato)."""
        from utils.cryptography import encrypt
        plaintext = "my_secret_token"
        result = encrypt(plaintext)
        assert result != plaintext

    def test_returns_none_on_empty_string(self):
        """Stringa vuota / falsy → None."""
        from utils.cryptography import encrypt
        assert encrypt("") is None
        assert encrypt(None) is None

    def test_produces_different_ciphertexts_for_same_input(self):
        """Fernet usa un nonce casuale, quindi lo stesso testo → output diverso ogni volta."""
        from utils.cryptography import encrypt
        r1 = encrypt("same_text")
        r2 = encrypt("same_text")
        # Non devono essere uguali (Fernet usa random IV)
        assert r1 != r2


class TestDecrypt:

    def test_decrypts_valid_ciphertext(self):
        """Testo cifrato con la stessa chiave → testo originale."""
        from utils.cryptography import encrypt, decrypt
        original = "super_secret_key"
        ciphertext = encrypt(original)
        result = decrypt(ciphertext)
        assert result == original

    def test_returns_none_on_none_input(self):
        """None → None."""
        from utils.cryptography import decrypt
        assert decrypt(None) is None

    def test_returns_none_on_empty_string(self):
        """Stringa vuota → None."""
        from utils.cryptography import decrypt
        assert decrypt("") is None

    def test_returns_input_unchanged_on_invalid_token(self):
        """Stringa non cifrata → ritorna l'originale (non solleva)."""
        from utils.cryptography import decrypt
        result = decrypt("not_encrypted_at_all")
        assert result == "not_encrypted_at_all"


class TestRoundtrip:

    def test_encrypt_then_decrypt_returns_original(self):
        """encrypt(decrypt(x)) == x per vari tipi di input."""
        from utils.cryptography import encrypt, decrypt
        for text in ["simple", "with spaces", "special!@#$%", "1234567890"]:
            assert decrypt(encrypt(text)) == text

    def test_unicode_roundtrip(self):
        """Testo Unicode/emoji sopravvive al roundtrip."""
        from utils.cryptography import encrypt, decrypt
        text = "ciao! 🚀 中文"
        assert decrypt(encrypt(text)) == text
