"""
utils/encryption.py
-------------------
Person 2 – Encryption + Security Module

WHY AES?
--------
AES (Advanced Encryption Standard) is a symmetric-key algorithm used worldwide
by governments and banks. We use AES-256 in CBC mode:
  - 256-bit key = extremely strong (2^256 combinations)
  - CBC mode = each block depends on the previous, so identical plaintext
    blocks produce different ciphertext (no patterns leak)

HOW IT WORKS (TCP/IP analogy):
  Like how data travels in encrypted HTTPS packets, we encrypt the file bytes
  before they "leave the server" to storage — so even if storage is compromised,
  data is unreadable without the key.
"""

import os
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# ── Key store (in production: use a real KMS / HSM) ──────────────────────────
KEY_STORE_PATH = "models/keys.json"


def _load_keys() -> dict:
    """Load the key store from disk."""
    if not os.path.exists(KEY_STORE_PATH):
        return {}
    with open(KEY_STORE_PATH, "r") as f:
        return json.load(f)


def _save_keys(keys: dict) -> None:
    """Persist the key store to disk."""
    os.makedirs(os.path.dirname(KEY_STORE_PATH), exist_ok=True)
    with open(KEY_STORE_PATH, "w") as f:
        json.dump(keys, f, indent=2)


def generate_key() -> bytes:
    """
    Generate a cryptographically secure 256-bit (32-byte) AES key.
    os.urandom uses the OS entropy pool — truly random, not pseudo-random.
    """
    return os.urandom(32)


def encrypt_file(input_path: str, output_path: str, filename: str) -> str:
    """
    Encrypt a file using AES-256-CBC and save the encrypted bytes.

    Steps:
    1. Generate a fresh key + IV (Initialization Vector) for this file.
       IV is 16 random bytes; it ensures the same plaintext → different ciphertext each time.
    2. Pad the plaintext to a multiple of 16 bytes (AES block size).
    3. Encrypt using AES-CBC.
    4. Prepend IV to ciphertext so we can decrypt later (IV is not secret).
    5. Store key in our key store mapped to the filename.

    Returns the key_id (filename) for later retrieval.
    """
    # Step 1 – Read plaintext
    with open(input_path, "rb") as f:
        plaintext = f.read()

    # Step 2 – Generate key & IV
    key = generate_key()
    iv = os.urandom(16)  # AES block size = 16 bytes

    # Step 3 – Pad plaintext (PKCS7 padding)
    padder = padding.PKCS7(128).padder()        # 128 bits = 16 bytes block
    padded_data = padder.update(plaintext) + padder.finalize()

    # Step 4 – Encrypt
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Step 5 – Write IV + ciphertext to output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(iv + ciphertext)  # first 16 bytes = IV, rest = ciphertext

    # Step 6 – Store key (base64-encoded for JSON serialisation)
    keys = _load_keys()
    keys[filename] = base64.b64encode(key).decode("utf-8")
    _save_keys(keys)

    print(f"[ENCRYPTION] ✅ File '{filename}' encrypted → '{output_path}'")
    print(f"[ENCRYPTION]    Key stored. IV length: {len(iv)} bytes | Ciphertext length: {len(ciphertext)} bytes")
    return filename


def decrypt_file(encrypted_path: str, output_path: str, filename: str) -> bool:
    """
    Decrypt a file encrypted by encrypt_file().

    Steps:
    1. Retrieve key from key store.
    2. Read IV (first 16 bytes) + ciphertext from file.
    3. Decrypt using AES-CBC.
    4. Remove PKCS7 padding.
    5. Write plaintext to output_path.

    Returns True on success, False on failure.
    """
    # Step 1 – Get key
    keys = _load_keys()
    if filename not in keys:
        print(f"[ENCRYPTION] ❌ Key not found for '{filename}'")
        return False

    key = base64.b64decode(keys[filename])

    # Step 2 – Read encrypted file
    with open(encrypted_path, "rb") as f:
        data = f.read()

    iv = data[:16]          # first 16 bytes
    ciphertext = data[16:]  # rest

    # Step 3 – Decrypt
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Step 4 – Remove padding
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    # Step 5 – Write decrypted file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(plaintext)

    print(f"[ENCRYPTION] ✅ File '{filename}' decrypted → '{output_path}'")
    return True
