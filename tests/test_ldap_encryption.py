import pytest

from app.services.ldap.encryption import decrypt_credential, encrypt_credential


def test_encrypt_decrypt_roundtrip():
    plaintext = "my_secure_password"
    encrypted = encrypt_credential(plaintext)

    # Encrypted should be different from plaintext
    assert encrypted != plaintext
    assert len(encrypted) > 0

    # Decrypt should return original
    decrypted = decrypt_credential(encrypted)
    assert decrypted == plaintext


def test_encrypt_empty_string():
    encrypted = encrypt_credential("")
    assert encrypted == ""

    decrypted = decrypt_credential("")
    assert decrypted == ""


def test_encrypt_unicode():
    plaintext = "pässwörd123!@#$%^&*()"
    encrypted = encrypt_credential(plaintext)
    decrypted = decrypt_credential(encrypted)
    assert decrypted == plaintext


def test_encryption_produces_different_results():
    plaintext = "password"
    encrypted1 = encrypt_credential(plaintext)
    encrypted2 = encrypt_credential(plaintext)

    # Should be different ciphertexts
    assert encrypted1 != encrypted2

    # But both should decrypt to same plaintext
    assert decrypt_credential(encrypted1) == plaintext
    assert decrypt_credential(encrypted2) == plaintext


def test_decrypt_invalid_data():
    from cryptography.fernet import InvalidToken

    with pytest.raises(InvalidToken):
        decrypt_credential("not_valid_encrypted_data")
