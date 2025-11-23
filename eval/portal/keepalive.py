"""
Keepalive service for the DroidRun accessibility overlay.

This module provides functionality to continuously disable the overlay of the
DroidRun accessibility service, which is necessary for some tasks.
"""

import logging
from async_adbutils import adb
from droidrun.portal import toggle_overlay
import threading

logger = logging.getLogger(__name__)


class KeepOverlayDisabled:
    def __init__(self, device_serial: str, interval: int = 5):
        self.device = adb.device(device_serial)
        self.interval = interval
        self.thread = None
        self.stop_event = threading.Event()

    def disable_loop(self):
        """Continuously disable overlay until stop event is set."""
        while not self.stop_event.is_set():
            try:
                toggle_overlay(self.device, False)
            except Exception as e:
                logger.warning(f"Failed to disable overlay: {e}")

            self.stop_event.wait(self.interval)

    def start(self):
        """Start the background thread to disable overlay."""
        if self.thread and self.thread.is_alive():
            logger.warning("KeepOverlayDisabled thread is already running")
            return

        self.stop_event.clear()
        self.thread = threading.Thread(target=self.disable_loop, daemon=True)
        self.thread.start()
        logger.info(
            f"Started KeepOverlayDisabled thread with {self.interval}s interval"
        )

    def stop(self):
        """Stop the background thread."""
        if self.thread and self.thread.is_alive():
            logger.info("Stopping KeepOverlayDisabled thread")
            self.stop_event.set()
            self.thread.join(timeout=10)  # Wait up to 10 seconds for thread to stop
            if self.thread.is_alive():
                logger.warning("KeepOverlayDisabled thread did not stop gracefully")
            else:
                logger.info("KeepOverlayDisabled thread stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
