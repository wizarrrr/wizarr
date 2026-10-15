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
