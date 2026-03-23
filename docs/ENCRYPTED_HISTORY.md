# Encrypted History at Rest

## Problem

Chat history is stored as plaintext `.log` files in
`~/.ezchat-{handle}/history/`. Anyone with filesystem access can
read all past conversations.

## Solution

Opt-in passphrase-based encryption of history files. A passphrase
entered at startup derives an AES-256-GCM key that encrypts log
entries before they hit disk.

## User experience

### First time

```bash
ezchat --handle kirbus --encrypt-history
```

Prompts:
```
Set a passphrase for history encryption: ********
Confirm passphrase: ********
```

Any existing plaintext history is encrypted in place. A salt file
is created at `~/.ezchat-{handle}/history/.salt`. The preference
`encrypt_history = true` is saved to `config.toml`.

### Subsequent launches

```bash
ezchat --handle kirbus
```

Detects `encrypt_history = true` in config (or the presence of
`.salt`). Prompts:
```
History passphrase: ********
```

Decrypts history for scrollback, continues encrypting new entries.

### Wrong passphrase

Decryption fails → warns "wrong passphrase, history unavailable"
and starts with empty scrollback. New messages are NOT written to
avoid corrupting the log with a different key.

### Disabling

```bash
ezchat --handle kirbus --no-encrypt-history
```

Prompts for passphrase, decrypts all history back to plaintext,
removes `.salt`, updates config.

## Crypto design

```
passphrase  ──►  Argon2id(salt, passphrase)  ──►  256-bit key
                      │
                      ▼
              AES-256-GCM encrypt/decrypt
```

- **KDF:** Argon2id (memory-hard, resists GPU/ASIC attacks)
  - Salt: 16 random bytes, stored in `.salt`
  - Parameters: time=3, memory=65536 KB, parallelism=1
- **Cipher:** AES-256-GCM (authenticated encryption)
  - Each log line gets a unique 12-byte random nonce
  - Nonce prepended to ciphertext

## File format

### Plaintext (current)

```
[2026-03-22 14:06:44] bob: hello  sig:Ft_Y6...
```

### Encrypted

```
ENC:base64(nonce + ciphertext)
```

Each line is independently encrypted. This preserves the append-only
nature — new messages are encrypted and appended without re-encrypting
the entire file.

The `ENC:` prefix distinguishes encrypted lines from plaintext,
enabling mixed-mode detection and migration.

## Implementation

### Files to modify

| File | Change |
|------|--------|
| `store/log.py` | Encrypt on `append_message()`, decrypt on `read_recent()` |
| `store/crypto_history.py` | **New** — key derivation, encrypt/decrypt helpers |
| `ai/config.py` | Add `encrypt_history` to `UIConfig` |
| `__main__.py` | Add `--encrypt-history` / `--no-encrypt-history` flags |
| `ui/app.py` | Passphrase prompt at startup, pass key to log module |

### Key lifecycle

1. Passphrase prompted via `getpass()` before curses starts
2. Key derived via Argon2id
3. Key held in memory for the session
4. Key passed to `store/log.py` via module-level setter
5. On exit, key is not persisted

### Migration

When `--encrypt-history` is first set:
1. Derive key from new passphrase
2. Read each `.log` file line by line
3. Encrypt each line and rewrite the file
4. Write `.salt`

When `--no-encrypt-history` is set:
1. Derive key from passphrase
2. Read each encrypted `.log` file
3. Decrypt and rewrite as plaintext
4. Remove `.salt`

## What this does NOT protect

- Messages in memory during a running session
- The identity key (`identity.json`) — a separate feature
- Metadata (filenames reveal who you talked to)
- An attacker who installs a keylogger before you type your passphrase
