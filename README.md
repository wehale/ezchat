# ezchat

A peer-to-peer, end-to-end encrypted terminal chat with built-in AI integration.

- **Private by design** — messages are encrypted between peers; no server ever sees content
- **No accounts** — identity is an Ed25519 keypair generated on first run
- **Works anywhere** — direct LAN connections or through a relay server for internet use
- **Local AI** — `/ai` command talks to a local Ollama instance; AI context is shared between peers
- **Retro terminal UI** — five built-in themes, channel support, scratch pad

---

## Install

```bash
git clone https://github.com/wehale/ezchat.git
cd ezchat
pip install -e .
```

Requires Python 3.11+. If using [uv](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/wehale/ezchat.git
cd ezchat
uv run ezchat --handle yourname
```

---

## Quick start (same network)

```bash
# Terminal 1 — listen
ezchat --handle alice --listen 9000

# Terminal 2 — connect
ezchat --handle bob --connect localhost:9000
```

---

## Internet use (via relay server)

One person runs `ezchat-server` on a machine with a public IP (VPS, home machine with port forwarding, etc.). Everyone else points `--server` at it.

### Run the server

```bash
ezchat-server
# Rendezvous API: port 8000
# TCP relay:      port 9001
```

Open ports **8000** and **9001** in your firewall.

Optional config (`server.toml`):

```toml
[server]
host       = "0.0.0.0"
api_port   = 8000
relay_port = 9001
ttl        = 60        # seconds before a peer registration expires
log_level  = "info"
```

```bash
ezchat-server --config server.toml
```

### Connect from anywhere

Everyone just runs the same command — no separate "listener" and "connector" roles needed:

```bash
ezchat --server http://SERVER_IP:8000 --handle alice
ezchat --server http://SERVER_IP:8000 --handle bob
ezchat --server http://SERVER_IP:8000 --handle carol
```

On startup each client:
1. Registers with the rendezvous server
2. Fetches the list of everyone already online
3. Connects to all of them (direct TCP first, relay fallback)
4. Polls every 20 seconds for new arrivals and connects automatically

Everyone ends up connected to everyone else. The server never sees messages — it only knows who is currently online (forgotten after 60 seconds).

If you want to accept direct TCP connections (faster than relay), add `--listen PORT`:

```bash
ezchat --server http://SERVER_IP:8000 --handle alice --listen 9000
```

### Save your server URL

Add to `~/.ezchat/config.toml` so you don't need `--server` every time:

```toml
[ui]
theme  = "phosphor_green"
handle = "alice"
server = "http://SERVER_IP:8000"
```

---

## Configuration

`~/.ezchat/config.toml` — created automatically on first run.

```toml
[ui]
theme  = "phosphor_green"   # phosphor_green | amber_terminal | c64 | ansi_bbs | paper_white
handle = "you"              # your default display name
server = ""                 # ezchat-server URL (leave blank for LAN-only use)

[ai]
provider = "openai-compat"
model    = "gemma3:4b"
base_url = "http://localhost:11434/v1"
api_key  = ""               # not needed for local Ollama
```

Multiple identities use `EZCHAT_HOME`:

```bash
EZCHAT_HOME=~/.ezchat-work ezchat --handle workme --listen 9000
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/ai <prompt>` | Ask the AI; response shown to all peers in the current conversation |
| `/ai-peer` | Forward the last peer message to your local AI |
| `/theme <name>` | Switch theme |
| `/themes` | List available themes |
| `/channel create <name>` | Create a channel |
| `/channel join <name>` | Join a channel |
| `/channel invite <peer> [channel]` | Invite a peer to a channel |
| `/channel leave <name>` | Leave a channel |
| `/clear` | Clear chat history |
| `/quit` | Exit |

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Tab` | Focus peer list |
| `↑` / `↓` | Navigate peers (when peer list focused) or command history (when input focused) |
| `Enter` | Select peer / send message |
| `Esc` | Return focus to input |
| `PgUp` / `PgDn` | Scroll chat |
| Mouse wheel | Scroll chat |

---

## AI integration

ezchat uses [Ollama](https://ollama.com) for local AI.

```bash
# Install Ollama, then pull a model
ollama pull gemma3:4b

# Ask the AI in any conversation
/ai what's the capital of France?
```

AI context is shared between peers — if alice asks a question and bob follows up, the AI sees the full conversation history.

`/ai-peer` is a shortcut that grabs the last message from your peer and forwards it to your AI automatically — useful for getting a quick response to something they said without retyping it.

Each person's `/ai` runs against their own local model. If a peer doesn't have Ollama set up, `/ai` won't work for them — but they can still see your AI responses in the conversation.

For cloud AI, point `base_url` at any OpenAI-compatible endpoint and set `api_key`.

**WSL2 note:** if Ollama is running on Windows, set `OLLAMA_HOST=0.0.0.0` before starting it and point `base_url` at the Windows host IP (find it with `ip route | grep default | awk '{print $3}'`).

---

## Verify message signatures

Every message is signed with the sender's Ed25519 key and stored in `~/.ezchat/history/`.

```bash
ezchat --verify-log @alice
ezchat --verify-log '#general'
ezchat --verify-log scratch
```

---

## Test mode

Try the UI without any network setup:

```bash
ezchat --test
```

Simulated peers (alice, bob, carol, dave) come online, join channels, and respond to messages.

---

## Security model

- **Identity** — Ed25519 keypair, generated locally, never leaves your machine
- **Key exchange** — X25519 ECDH ephemeral keys per session
- **Encryption** — AES-256-GCM with HKDF-derived keys
- **Message signing** — every message signed by sender's Ed25519 key
- **Relay** — the relay server pipes opaque ciphertext; it cannot read messages or identify who is talking to whom (it sees IP addresses and handle names used for routing)
- **Rendezvous** — registrations are signed; the server stores handle → IP:port for 60 seconds then discards

Self-host the server for full sovereignty.
