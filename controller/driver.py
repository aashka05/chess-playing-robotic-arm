"""Low-level arm drivers: real serial port or a mock for development."""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

try:
    import termios
    _PORT_ERRORS: tuple = (OSError, termios.error)
except ImportError:  # Windows
    _PORT_ERRORS = (OSError,)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArmReply:
    ok: bool
    message: str


class ArmDriver(Protocol):
    async def send(self, command: str) -> ArmReply: ...

    def close(self) -> None: ...


class SerialArmDriver:
    """One command per line; the Arduino replies 'SEQ DONE' or 'ERROR...'."""

    def __init__(self, port: str, baud: int, timeout_sec: float):
        self.port = port
        self.baud = baud
        self.timeout_sec = timeout_sec
        self._serial = None
        self._lock = threading.Lock()

    def _open(self):
        import serial

        if self._serial is None or not self._serial.is_open:
            # Warn if another process already owns the port (e.g. Serial Monitor)
            self._check_port_conflict()
            log.info("Opening arm serial port %s @ %d", self.port, self.baud)
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)  # the Arduino resets when the port opens
        return self._serial

    def _check_port_conflict(self):
        """Log a warning if another process holds this serial port."""
        import os
        import subprocess

        if not os.path.exists(self.port):
            return
        try:
            result = subprocess.run(
                ["lsof", self.port],
                capture_output=True, text=True, timeout=3,
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) > 1:  # header + at least one owner
                owners = [l.split()[0] for l in lines[1:]]
                log.warning(
                    "Port %s is already held by: %s — this will likely cause "
                    "'Device not configured' errors. Close the other program "
                    "(e.g. Arduino Serial Monitor) first.",
                    self.port, ", ".join(owners),
                )
        except Exception:
            pass  # best-effort check; don't block on failure

    def _transact(self, command: str) -> ArmReply:
        ser = self._open()
        ser.reset_input_buffer()
        ser.write((command + "\n").encode())
        deadline = time.monotonic() + self.timeout_sec
        while time.monotonic() < deadline:
            line = ser.readline().decode(errors="replace").strip()
            if not line:
                continue
            log.debug("Arduino: %s", line)
            if line == "SEQ DONE":
                return ArmReply(True, line)
            if line.startswith("ERR"):
                return ArmReply(False, line)
        return ArmReply(False, f"Timed out after {self.timeout_sec:.0f}s waiting for the arm")

    def _send_blocking(self, command: str) -> ArmReply:
        import os
        import serial

        errors = (serial.SerialException, *_PORT_ERRORS)
        max_attempts = 3
        with self._lock:
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return self._transact(command)
                except errors as exc:
                    last_exc = exc
                    log.warning("Arm serial error (attempt %d/%d): %s", attempt + 1, max_attempts, exc)
                    self.close()  # drop the stale handle so _open() reconnects
                    # Exponential backoff: give macOS time to re-enumerate the USB device
                    backoff = 1.0 * (2 ** attempt)  # 1s, 2s, 4s
                    # Wait until the device node actually reappears (or timeout)
                    waited = 0.0
                    while waited < backoff:
                        if os.path.exists(self.port):
                            # Device node is back; give the Arduino bootloader a moment
                            time.sleep(0.5)
                            break
                        time.sleep(0.25)
                        waited += 0.25
                    else:
                        log.warning("Device %s not found after %.1fs; retrying anyway", self.port, backoff)
            return ArmReply(False, f"Arm disconnected after {max_attempts} attempts: {last_exc}")

    async def send(self, command: str) -> ArmReply:
        return await asyncio.to_thread(self._send_blocking, command)

    def close(self) -> None:
        ser, self._serial = self._serial, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                log.debug("Ignoring error while closing serial port", exc_info=True)


class MockArmDriver:
    """Pretends to move; always succeeds unless told to fail."""

    def __init__(self, delay_sec: float = 0.3):
        self.delay_sec = delay_sec
        self.sent: list[str] = []
        self.fail_next: str | None = None

    async def send(self, command: str) -> ArmReply:
        self.sent.append(command)
        log.info("[mock arm] %s", command)
        await asyncio.sleep(self.delay_sec)
        if self.fail_next is not None:
            reason, self.fail_next = self.fail_next, None
            return ArmReply(False, f"ERROR {reason}")
        return ArmReply(True, "SEQ DONE")

    def close(self) -> None:
        pass
