from cryptography.fernet import Fernet

from app.config import get_or_create_secret


def _get_encryption_key() -> bytes:
    key_str = get_or_create_secret(
        "LDAP_OIDC_ENCRYPTION_KEY", lambda: Fernet.generate_key().decode()
    )
    return key_str.encode()


def encrypt_credential(plaintext: str) -> str:
    if not plaintext:
        return ""

    fernet = Fernet(_get_encryption_key())
    encrypted_bytes = fernet.encrypt(plaintext.encode())
    return encrypted_bytes.decode()


def decrypt_credential(ciphertext: str) -> str:
    if not ciphertext:
        return ""

    fernet = Fernet(_get_encryption_key())
    decrypted_bytes = fernet.decrypt(ciphertext.encode())
    return decrypted_bytes.decode()
