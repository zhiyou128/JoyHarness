"""Short Joy-Con rumble feedback for button presses."""

from __future__ import annotations

import logging
import queue
import threading
import time

import hid

logger = logging.getLogger(__name__)

_VID = 0x057E  # Nintendo
_PID_L = 0x2006  # Joy-Con L
_PID_R = 0x2007  # Joy-Con R

_STOP = bytes([0x00, 0x01, 0x40, 0x40])

# Gentle, short Joy-Con rumble packet used as tactile feedback.
_BUTTON_PULSE = bytes([0x28, 0x88, 0x60, 0x61])
_OVERLAY_PULSE = bytes([0x28, 0x88, 0x80, 0x61])


class HapticFeedbackManager:
    """Runs short Joy-Con rumble pulses without blocking input polling."""

    def __init__(self, stop_event: threading.Event, enabled: bool = True) -> None:
        self._stop_event = stop_event
        self._enabled = enabled
        self._queue: queue.Queue[tuple[bytes, float]] = queue.Queue()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._counter = 0
        self._last_pulse = 0.0
        self._min_interval = 0.08
        self._thread.start()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        self._enabled = value
        logger.info("Haptic feedback %s", "enabled" if value else "disabled")

    def pulse(self, kind: str = "button") -> None:
        """Queue a short rumble pulse."""
        if not self._enabled or self._stop_event.is_set():
            return

        now = time.monotonic()
        if now - self._last_pulse < self._min_interval:
            return
        self._last_pulse = now

        if kind == "overlay":
            self._queue.put((_OVERLAY_PULSE, 0.07))
        else:
            self._queue.put((_BUTTON_PULSE, 0.045))

    def join(self, timeout: float = 2.0) -> None:
        """Wait for the background worker to finish."""
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                rumble_data, duration = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._send_pulse(rumble_data, duration)

    def _send_pulse(self, rumble_data: bytes, duration: float) -> None:
        devices = []
        try:
            for d in hid.enumerate(_VID, _PID_L):
                devices.append(("L", d))
            for d in hid.enumerate(_VID, _PID_R):
                devices.append(("R", d))
        except Exception:
            logger.debug("Haptic HID enumerate failed", exc_info=True)
            return

        for side, dev_info in devices:
            dev = hid.device()
            try:
                dev.open_path(dev_info["path"])
                self._write_rumble(dev, side, rumble_data)
                time.sleep(duration)
                self._write_rumble(dev, side, _STOP)
            except OSError as e:
                logger.debug("Haptic HID write failed (%s): %s", side, e)
            finally:
                try:
                    dev.close()
                except OSError:
                    pass

    def _write_rumble(self, dev, side: str, data: bytes) -> None:
        if side == "L":
            report = bytes([0x10, self._counter & 0xFF]) + data + _STOP
        else:
            report = bytes([0x10, self._counter & 0xFF]) + _STOP + data
        dev.write(report)
        self._counter = (self._counter + 1) & 0xFF
