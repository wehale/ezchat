"""Home agent — smart home control via kirbus.

Presents IoT devices as a menu. Selecting a device starts a session
where you can send commands (on/off, dim, set temp, lock/unlock, etc.).

Behind the scenes, commands are sent to a Matter bridge-app via chip-tool.
For now, uses a simulated backend until Matter is wired up.

Run with:
    kirbus --agent home --server http://SERVER:8000 --handle my-house
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field

from kirbus.agent.menu import MenuAgent, MenuEntry
from kirbus.net.connection import Connection

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device definitions
# ---------------------------------------------------------------------------
@dataclass
class Device:
    key: str
    name: str
    type: str          # "light" | "thermostat" | "lock" | "garage" | "switch"
    endpoint: int = 0  # Matter endpoint ID (for chip-tool)
    state: dict = field(default_factory=dict)

    def default_state(self) -> None:
        if self.type == "light":
            self.state = {"on": False, "brightness": 100}
        elif self.type == "thermostat":
            self.state = {"mode": "auto", "target": 72, "current": 71}
        elif self.type == "lock":
            self.state = {"locked": True}
        elif self.type == "garage":
            self.state = {"open": False}
        elif self.type == "switch":
            self.state = {"on": False}


# The house
DEVICES = [
    Device("living_light",  "Living Room Light", "light",      endpoint=2),
    Device("kitchen_light", "Kitchen Light",     "light",      endpoint=3),
    Device("bedroom_light", "Bedroom Light",     "light",      endpoint=4),
    Device("thermostat",    "Thermostat",        "thermostat", endpoint=5),
    Device("front_lock",    "Front Door Lock",   "lock",       endpoint=6),
    Device("garage",        "Garage Door",       "garage",     endpoint=7),
    Device("porch_light",   "Porch Light",       "light",      endpoint=8),
]


# ---------------------------------------------------------------------------
# Matter backend (swappable — simulated for now)
# ---------------------------------------------------------------------------
class MatterBackend:
    """Interface for controlling Matter devices. Subclass for real chip-tool."""

    def send_command(self, device: Device, command: str, args: dict) -> str:
        """Send a command to a device. Returns status message."""
        # Simulated — will be replaced with chip-tool calls
        if device.type == "light":
            return self._handle_light(device, command, args)
        elif device.type == "thermostat":
            return self._handle_thermostat(device, command, args)
        elif device.type == "lock":
            return self._handle_lock(device, command, args)
        elif device.type == "garage":
            return self._handle_garage(device, command, args)
        elif device.type == "switch":
            return self._handle_switch(device, command, args)
        return "Unknown device type."

    def _handle_light(self, dev: Device, cmd: str, args: dict) -> str:
        if cmd == "on":
            dev.state["on"] = True
            return f"{dev.name}: ON (brightness {dev.state['brightness']}%)"
        elif cmd == "off":
            dev.state["on"] = False
            return f"{dev.name}: OFF"
        elif cmd == "dim":
            level = args.get("level", 50)
            dev.state["brightness"] = max(0, min(100, level))
            dev.state["on"] = level > 0
            return f"{dev.name}: brightness set to {dev.state['brightness']}%"
        elif cmd == "status":
            on = "ON" if dev.state["on"] else "OFF"
            return f"{dev.name}: {on}, brightness {dev.state['brightness']}%"
        return f"Unknown command for light: {cmd}"

    def _handle_thermostat(self, dev: Device, cmd: str, args: dict) -> str:
        if cmd == "set":
            temp = args.get("temp", 72)
            dev.state["target"] = max(60, min(85, temp))
            return f"{dev.name}: target set to {dev.state['target']}F (current: {dev.state['current']}F)"
        elif cmd == "mode":
            mode = args.get("mode", "auto")
            if mode in ("heat", "cool", "auto", "off"):
                dev.state["mode"] = mode
                return f"{dev.name}: mode set to {mode}"
            return f"Invalid mode. Options: heat, cool, auto, off"
        elif cmd == "status":
            return (
                f"{dev.name}: {dev.state['mode']} mode\n"
                f"  Target: {dev.state['target']}F\n"
                f"  Current: {dev.state['current']}F"
            )
        return f"Unknown command for thermostat: {cmd}"

    def _handle_lock(self, dev: Device, cmd: str, args: dict) -> str:
        if cmd == "lock":
            dev.state["locked"] = True
            return f"{dev.name}: LOCKED"
        elif cmd == "unlock":
            dev.state["locked"] = False
            return f"{dev.name}: UNLOCKED"
        elif cmd == "status":
            status = "LOCKED" if dev.state["locked"] else "UNLOCKED"
            return f"{dev.name}: {status}"
        return f"Unknown command for lock: {cmd}"

    def _handle_garage(self, dev: Device, cmd: str, args: dict) -> str:
        if cmd == "open":
            dev.state["open"] = True
            return f"{dev.name}: OPENING..."
        elif cmd == "close":
            dev.state["open"] = False
            return f"{dev.name}: CLOSING..."
        elif cmd == "status":
            status = "OPEN" if dev.state["open"] else "CLOSED"
            return f"{dev.name}: {status}"
        return f"Unknown command for garage: {cmd}"

    def _handle_switch(self, dev: Device, cmd: str, args: dict) -> str:
        if cmd == "on":
            dev.state["on"] = True
            return f"{dev.name}: ON"
        elif cmd == "off":
            dev.state["on"] = False
            return f"{dev.name}: OFF"
        elif cmd == "status":
            status = "ON" if dev.state["on"] else "OFF"
            return f"{dev.name}: {status}"
        return f"Unknown command for switch: {cmd}"


class ChipToolBackend(MatterBackend):
    """Real Matter backend using chip-tool. TODO: wire up when Matter is compiled."""

    def __init__(self, chip_tool_path: str = "chip-tool", node_id: int = 1):
        self._chip_tool = chip_tool_path
        self._node_id = node_id

    def send_command(self, device: Device, command: str, args: dict) -> str:
        # TODO: implement real chip-tool calls
        # Example: chip-tool onoff on <node-id> <endpoint>
        # For now, fall back to simulated
        return super().send_command(device, command, args)


# ---------------------------------------------------------------------------
# Home agent
# ---------------------------------------------------------------------------
class HomeAgent(MenuAgent):
    """Presents smart home devices as a menu with interactive control."""

    def __init__(self, backend: MatterBackend | None = None) -> None:
        super().__init__()
        self._backend = backend or MatterBackend()
        self._devices: dict[str, Device] = {}
        for dev in DEVICES:
            d = Device(dev.key, dev.name, dev.type, dev.endpoint)
            d.default_state()
            self._devices[d.key] = d
        self._active: dict[str, str] = {}  # handle → device key

    def get_title(self) -> str:
        return "my-house"

    def get_entries(self) -> list[MenuEntry]:
        entries = []
        for dev in self._devices.values():
            entries.append(MenuEntry(key=dev.key, label=dev.name, type="single"))
        return entries

    def on_select(self, sender: str, key: str, opponent: str | None = None) -> str:
        dev = self._devices.get(key)
        if not dev:
            return "Device not found."
        self._active[sender] = key
        return self._device_prompt(dev)

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        dev_key = self._active.get(sender)
        if not dev_key:
            return [(sender, "No device selected.")]
        dev = self._devices[dev_key]
        result = self._handle_command(dev, text.strip())
        return [(sender, result)]

    def on_back(self, sender: str) -> str | None:
        self._active.pop(sender, None)
        return None

    def _device_prompt(self, dev: Device) -> str:
        lines = [f"=== {dev.name} ===", ""]
        if dev.type == "light":
            on = "ON" if dev.state["on"] else "OFF"
            lines.append(f"Status: {on}, brightness {dev.state['brightness']}%")
            lines.append("")
            lines.append("Commands: on, off, dim <0-100>, status")
        elif dev.type == "thermostat":
            lines.append(f"Mode: {dev.state['mode']}")
            lines.append(f"Target: {dev.state['target']}F  Current: {dev.state['current']}F")
            lines.append("")
            lines.append("Commands: set <temp>, mode <heat|cool|auto|off>, status")
        elif dev.type == "lock":
            status = "LOCKED" if dev.state["locked"] else "UNLOCKED"
            lines.append(f"Status: {status}")
            lines.append("")
            lines.append("Commands: lock, unlock, status")
        elif dev.type == "garage":
            status = "OPEN" if dev.state["open"] else "CLOSED"
            lines.append(f"Status: {status}")
            lines.append("")
            lines.append("Commands: open, close, status")
        elif dev.type == "switch":
            status = "ON" if dev.state["on"] else "OFF"
            lines.append(f"Status: {status}")
            lines.append("")
            lines.append("Commands: on, off, status")
        return "\n".join(lines)

    def _handle_command(self, dev: Device, text: str) -> str:
        parts = text.lower().split()
        if not parts:
            return self._device_prompt(dev)
        cmd = parts[0]

        if cmd == "help":
            return self._device_prompt(dev)

        args: dict = {}
        if cmd == "dim" and len(parts) > 1 and parts[1].isdigit():
            args["level"] = int(parts[1])
        elif cmd == "set" and len(parts) > 1 and parts[1].isdigit():
            args["temp"] = int(parts[1])
        elif cmd == "mode" and len(parts) > 1:
            args["mode"] = parts[1]

        return self._backend.send_command(dev, cmd, args)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def run_home_agent(identity, server: str) -> None:
    """Connect to the mesh and handle home control sessions."""
    from kirbus.net.rendezvous_client import RendezvousClient
    from kirbus.net.connection import accept_peer
    from urllib.parse import urlparse

    agent = HomeAgent()

    rdv        = RendezvousClient(server, identity)
    relay_host = urlparse(server).hostname or "127.0.0.1"
    info = await rdv.server_info()
    relay_port = info.get("relay_port", 9001)

    # Register with rendezvous
    pub_ip   = await rdv.my_public_ip() or "127.0.0.1"
    endpoint = f"{pub_ip}:0"
    await rdv.register(endpoint)
    rdv.start_keepalive(endpoint)
    _log.info("home agent registered as %s", identity.handle)

    # Register menu with server
    entries = agent.get_entries()
    menu_data = {
        "title": agent.get_title(),
        "entries": [{"key": e.key, "label": e.label, "type": e.type} for e in entries],
    }
    await rdv.register_agent_menu(identity.handle, menu_data)

    print(f"home agent online as @{identity.handle}")

    async def _relay_loop() -> None:
        import json
        while True:
            try:
                reader, writer = await asyncio.open_connection(relay_host, relay_port)
                writer.write(
                    (json.dumps({"role": "wait", "handle": identity.handle}) + "\n").encode()
                )
                await writer.drain()
                line = await reader.readline()
                if not line or not line.strip():
                    writer.close()
                    continue
                resp = json.loads(line.decode().strip())
                if not resp.get("ok"):
                    writer.close()
                    continue
                conn = await accept_peer(reader, writer, identity)
                asyncio.create_task(agent.handle_conn(conn))
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(1)

    await _relay_loop()
