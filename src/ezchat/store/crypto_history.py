"""Passphrase-based encryption for history files at rest.

Uses Argon2id for key derivation and AES-256-GCM for encryption.
Each log line is independently encrypted so the file stays append-only.

Encrypted line format:
    ENC:<base64(12-byte-nonce + ciphertext + 16-byte-tag)>
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Module-level encryption key — set once at startup, held in memory.
_key: bytes | None = None
_enabled: bool = False

# Argon2id would be ideal but cryptography lib doesn't expose it directly.
# Use scrypt which is also memory-hard and available everywhere.
_SCRYPT_N = 2**17   # CPU/memory cost
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_LEN = 16
_KEY_LEN = 32        # AES-256
_NONCE_LEN = 12      # GCM standard


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from passphrase + salt using scrypt."""
    kdf = Scrypt(salt=salt, length=_KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def salt_path(home: Path) -> Path:
    """Return the path to the salt file."""
    return home / "history" / ".salt"


def load_or_create_salt(home: Path) -> bytes:
    """Load existing salt or generate a new one."""
    sp = salt_path(home)
    if sp.exists():
        return sp.read_bytes()
    salt = os.urandom(_SALT_LEN)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_bytes(salt)
    return salt


_VERIFY_TOKEN = "ezchat-history-ok"


def _verify_path(home: Path) -> Path:
    return home / "history" / ".verify"


def init_encryption(passphrase: str, home: Path) -> bool:
    """Initialize encryption with a passphrase. Call once at startup.

    Returns True if passphrase is correct (or first time), False if wrong.
    """
    global _key, _enabled
    salt = load_or_create_salt(home)
    _key = derive_key(passphrase, salt)

    vp = _verify_path(home)
    if vp.exists():
        # Verify passphrase against stored token
        encrypted_token = vp.read_text(encoding="utf-8").strip()
        result = decrypt_line(encrypted_token)
        if result != _VERIFY_TOKEN:
            _key = None
            _enabled = False
            return False
    else:
        # First time — write verification token
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(encrypt_line(_VERIFY_TOKEN) + "\n", encoding="utf-8")

    _enabled = True
    return True


def is_enabled() -> bool:
    """Return True if history encryption is active."""
    return _enabled


def encrypt_line(plaintext: str) -> str:
    """Encrypt a log line. Returns 'ENC:<base64>'."""
    if not _key:
        raise RuntimeError("encryption not initialized")
    nonce = os.urandom(_NONCE_LEN)
    aesgcm = AESGCM(_key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return "ENC:" + base64.b64encode(nonce + ct).decode()


def decrypt_line(encoded: str) -> str | None:
    """Decrypt an 'ENC:...' line. Returns plaintext or None on failure."""
    if not _key or not encoded.startswith("ENC:"):
        return None
    try:
        raw = base64.b64decode(encoded[4:])
        nonce = raw[:_NONCE_LEN]
        ct = raw[_NONCE_LEN:]
        aesgcm = AESGCM(_key)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except Exception:
        return None


def is_encrypted_line(line: str) -> bool:
    """Check if a line is encrypted."""
    return line.startswith("ENC:")


def encrypt_file(path: Path) -> None:
    """Encrypt a plaintext log file in place."""
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    encrypted = []
    for line in lines:
        if not line.strip():
            continue
        if is_encrypted_line(line):
            encrypted.append(line)  # already encrypted
        else:
            encrypted.append(encrypt_line(line))
    path.write_text("\n".join(encrypted) + "\n" if encrypted else "", encoding="utf-8")


def decrypt_file(path: Path) -> None:
    """Decrypt an encrypted log file back to plaintext in place."""
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    decrypted = []
    for line in lines:
        if not line.strip():
            continue
        if is_encrypted_line(line):
            pt = decrypt_line(line)
            if pt:
                decrypted.append(pt)
            else:
                decrypted.append(line)  # can't decrypt, leave as-is
        else:
            decrypted.append(line)  # already plaintext
    path.write_text("\n".join(decrypted) + "\n" if decrypted else "", encoding="utf-8")
