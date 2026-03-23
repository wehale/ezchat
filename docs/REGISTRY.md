# kirbus Registry — Architecture

## Overview

The registry is a standalone service (`kirbus-registry`) that acts as a
directory of kirbus servers. It is the single stable URL users need to
know. Servers register themselves with the registry when they come online
and send periodic heartbeats to stay listed.

```
  Users                    Registry                     Servers
  ─────                    ────────                     ───────
    │  --registry URL  ──▶  │                             │
    │  ◀── server list ───  │  ◀── register/heartbeat ──  │
    │                       │                             │
    │  (select server)      │                             │
    │  --server URL  ─────────────────────────────────▶   │
    │  (normal P2P mesh)                                  │
```

The registry never touches chat traffic. It is purely a directory.

## Registry Service (`kirbus-registry`)

### API

All endpoints are simple HTTP/JSON.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/servers` | List all servers (filtered by visibility) |
| `POST` | `/servers` | Register or update a server (called by servers) |
| `DELETE` | `/servers/{name}` | Deregister a server |
| `POST` | `/servers/{name}/verify` | Verify access credentials for a protected server |

### `GET /servers`

Returns the public directory.

```json
[
  {
    "name": "kirbus-public",
    "description": "Open chat for everyone",
    "url": "http://100.0.197.245:8000",
    "access": "open",
    "online_count": 5
  },
  {
    "name": "dev-team",
    "description": "Internal dev discussions",
    "url": "http://10.0.1.50:8000",
    "access": "password",
    "online_count": 3
  },
  {
    "name": "secret-club",
    "description": "(unlisted)",
    "url": null,
    "access": "unlisted",
    "online_count": null
  }
]
```

### `POST /servers` (server → registry)

Called by `kirbus-server` on startup and periodically as a heartbeat.

```json
{
  "name": "kirbus-public",
  "description": "Open chat for everyone",
  "url": "http://100.0.197.245:8000",
  "access": "open",
  "secret": "registry-token-for-admin",
  "online_count": 5
}
```

- `secret` — a shared token between the server and registry so that
  only authorized servers can register/update their listing. Never
  returned in `GET /servers`.
- `access` — one of: `open`, `password`, `unlisted`

### `POST /servers/{name}/verify`

For `password`-protected servers. The client sends credentials before
being told the server URL.

```json
{ "password": "hunter2" }
```

Response (success):
```json
{ "url": "http://10.0.1.50:8000" }
```

Response (failure): `403`

This means password-protected servers never expose their URL in the
public listing — you must verify first.

### Heartbeat & expiry

- Servers POST to `/servers` every 60 seconds as a keepalive.
- Registry expires servers that haven't heartbeated in 3 minutes.
- `online_count` is updated with each heartbeat.

## Server-side changes (`kirbus-server`)

Add a `[registry]` section to `server.toml`:

```toml
[registry]
url = "https://ezchat.kirbus.ai"
name = "kirbus-public"
description = "Open chat for everyone"
secret = "my-registry-token"
access = "open"
# password = "hunter2"   # only needed if access = "password"
```

When configured, the server:
1. Registers with the registry on startup
2. Sends heartbeats every 60s with current `online_count`
3. Deregisters on clean shutdown

## Client-side changes

### Default registry

A default registry URL is compiled into the client:

```python
DEFAULT_REGISTRY = "https://ezchat.kirbus.ai"
```

This means a first-time user only needs:

```bash
kirbus --handle alice
```

No `--server`, no `--registry` — the client contacts the default
registry, fetches the server list, and presents it in the sidebar.

### Flag: `--registry`

Overrides the default registry:

```bash
kirbus --registry https://custom.example.com --handle alice
```

Use `--registry none` to disable registry and run in direct/LAN mode.

### Flag: `--server` (unchanged)

Bypasses the registry entirely and connects directly to a known server:

```bash
kirbus --server http://10.0.1.50:8000 --handle alice
```

### Startup flow

```
1. --server given?       → connect directly (skip registry)
2. --registry given?     → use that registry
3. neither given?        → use DEFAULT_REGISTRY
4. fetch GET /servers    → display server list in sidebar
5. last_server saved?    → auto-connect if still listed
6. otherwise             → wait for user to select a server
```

### Persisting choice

Save the last-used server in `config.toml`:

```toml
[ui]
registry = "https://ezchat.kirbus.ai"
last_server = "kirbus-public"
```

On next launch, auto-connect to `last_server` if it's still listed
in the registry. User can `/servers` to switch.

## Access model summary

| Access | Listed in `/servers`? | URL in listing? | How to join |
|--------|-----------------------|-----------------|-------------|
| `open` | Yes | Yes | Select it |
| `password` | Yes (name + description only) | No — must verify | Enter password |
| `unlisted` | No | No | Direct `--server` URL only |

## New commands

| Command | Description |
|---------|-------------|
| `/servers` | Show the server list from the registry |
| `/connect <name>` | Connect to a server by name |

## Config & deployment

```toml
# registry.toml
[registry]
host = "0.0.0.0"
port = 443
```

The registry is stateless — server listings live in memory and are
rebuilt from heartbeats. No database needed. A single registry can
serve many servers.

## Server-level authentication

The registry controls **discovery** (who can find the server URL).
The server itself controls **access** (who can join the mesh).

### Auth model: password + pubkey allowlist

Two layers that work together:

1. **Password gate** — for first-time entry
2. **Pubkey allowlist** — for ongoing access after first entry

### Flow

```
First connection:
  Client ──POST /register {handle, pubkey, password}──▶ Server
  Server: password valid? → add pubkey to allowlist → 200 OK
  Server: password invalid? → 403

Subsequent connections:
  Client ──POST /register {handle, pubkey, signature}──▶ Server
  Server: pubkey in allowlist? → verify signature → 200 OK
  Server: pubkey unknown? → 403 (need password)
```

### Challenge-response for returning clients

1. Client sends `POST /register` with handle + pubkey
2. Server recognizes the pubkey, responds with a random challenge nonce
3. Client signs the nonce with their Ed25519 private key
4. Server verifies the signature → registration complete

This proves the client holds the private key, not just a copied pubkey.

### Server config (`server.toml`)

```toml
[auth]
mode = "open"           # "open" | "password" | "allowlist"
password = "hunter2"    # required if mode = "password"
# allowlist is managed automatically — first connect with password
# adds the pubkey, subsequent connects are key-based
```

Modes:
- `open` — no auth, anyone can join (current behavior)
- `password` — password required on first connect, pubkey saved
- `allowlist` — pubkey-only, no password gate (admin manually adds keys)

### Server-side storage

```toml
# ~/.kirbus-server/allowlist.toml
[allowed.alice]
ed25519_pub = "veqjN53Zc3uItFAxBO9e2YLU7U6SziQpv2cZ2KryniI="
added = "2026-03-22T10:30:00"
added_via = "password"    # or "manual"

[allowed.bob]
ed25519_pub = "R8d2E+f3kLm9pQxYz1nOvW4aBcDeFgHiJkLmNoPqRsT="
added = "2026-03-22T11:00:00"
added_via = "password"
```

### Superuser (su) — server-local admin

The server operator gets admin powers by connecting from the same
machine the server runs on. No special credentials needed — localhost
access *is* the credential.

#### How it works

```bash
kirbus --handle kirbus --su
```

1. Client connects with `--su` flag, which adds `"su": true` to the
   registration request
2. Server checks: source IP is `127.0.0.1` (or `::1`) **AND** client
   requested su
3. Both conditions met → grant `su` role
4. Either condition missing → normal user (no error, just no admin)
5. The `su` role is visible in the sidebar (e.g. handle shows as
   `kirbus [su]`)
6. `su` users get access to admin commands within the chat UI

#### su commands (in-chat)

| Command | Description |
|---------|-------------|
| `/kick <handle>` | Disconnect a peer and remove from mesh |
| `/ban <handle>` | Kick + revoke pubkey from allowlist |
| `/unban <handle>` | Re-add a previously banned pubkey |
| `/allow <handle>` | Pre-approve a pubkey (allowlist mode) |
| `/who` | List all connected peers with IPs and pubkey fingerprints |
| `/server-password <new>` | Rotate the server password |
| `/server-mode <mode>` | Switch auth mode (open/password/allowlist) |

#### Implementation

- Server tags the connection with `role: "su"` during registration
  when source IP is loopback
- Admin commands are sent as regular messages prefixed with `/` — the
  server intercepts them before relay
- Server responds with system messages back to the su client only
- Non-su clients sending admin commands get a "permission denied" error

#### Why localhost = admin

- If you have shell access to the server, you already have full control
  (could edit config, kill processes, read logs)
- No passwords or tokens to manage for admin access
- Cannot be phished or leaked — you must be on the machine
- Requires explicit `--su` flag — no accidental admin grants on shared machines
- Simple to reason about: physical access + intent = authority

### CLI admin commands (non-interactive)

For scripting and automation, the same operations are available via CLI:

| Command | Description |
|---------|-------------|
| `kirbus-server allow <pubkey> [handle]` | Manually add a key to the allowlist |
| `kirbus-server revoke <handle>` | Remove a key from the allowlist |
| `kirbus-server list-allowed` | Show all allowed keys |
| `kirbus-server rotate-password` | Change the server password |

### Client-side changes

When connecting to a password-protected server:

1. Client tries `POST /register` with handle + pubkey
2. If `403` with `{"reason": "password_required"}`:
   - Prompt user: `Server requires a password:`
   - Retry with password included
3. On success, the server remembers the pubkey — no password needed next time

The password prompt happens inline in the chat UI as a system message.

### Interaction with registry access types

| Registry access | Server auth | User experience |
|----------------|-------------|-----------------|
| `open` | `open` | Select server, join immediately |
| `open` | `password` | Select server, enter server password on first connect |
| `password` | `password` | Enter registry password to get URL, then server password on first connect |
| `password` | `open` | Enter registry password to get URL, then join freely |
| `unlisted` | `allowlist` | Must know URL directly, must have key pre-approved |

The two layers are independent — registry auth gates discovery, server
auth gates access.

## Security considerations

- Registry ↔ server authentication uses a shared `secret` token
- Password-protected server URLs are never exposed without verification
- The registry itself should run behind TLS in production
- Unlisted servers bypass the registry entirely — defense in depth
- Server passwords are for initial entry only — ongoing auth is pubkey-based
- Pubkey allowlist means a compromised password can be rotated without
  disrupting existing users
- Revoked keys are immediately denied on next connect attempt

## Out of scope (for now)

- User accounts on the registry
- OAuth / SSO integration
- Server rating or search
- Federation between registries
- Registry replication / HA
- Role-based access control beyond su (e.g. moderators)
