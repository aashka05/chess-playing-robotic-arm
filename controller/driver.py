"""Low-level arm drivers: real serial port or a mock for development."""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

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
            log.info("Opening arm serial port %s @ %d", self.port, self.baud)
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)  # the Arduino resets when the port opens
        return self._serial

    def _send_blocking(self, command: str) -> ArmReply:
        import serial

        with self._lock:
            try:
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
                    if line.startswith("ERROR"):
                        return ArmReply(False, line)
                return ArmReply(False, f"Timed out after {self.timeout_sec:.0f}s waiting for the arm")
            except serial.SerialException as exc:
                self.close()
                return ArmReply(False, f"Serial error: {exc}")

    async def send(self, command: str) -> ArmReply:
        return await asyncio.to_thread(self._send_blocking, command)

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None


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
