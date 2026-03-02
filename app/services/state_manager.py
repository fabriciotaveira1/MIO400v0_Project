# services/state_manager.py

import threading
import time
from typing import Dict


class StateManager:

    def __init__(self):
        self._lock = threading.Lock()

        self._inputs_mask = 0
        self._outputs_mask = 0
        self._last_update = None
        self.last_heartbeat = time.time()

    # =========================
    # UPDATE METHODS
    # =========================

    def update_inputs(self, mask: int):
        with self._lock:
            self._inputs_mask = mask
            self._last_update = time.time()

    def update_outputs(self, mask: int):
        with self._lock:
            self._outputs_mask = mask
            self._last_update = time.time()

    def update_both(self, input_mask: int, output_mask: int):
        with self._lock:
            self._inputs_mask = input_mask
            self._outputs_mask = output_mask
            self._last_update = time.time()

    def is_online(self, timeout=10):
        return (time.time() - self.last_heartbeat) < timeout

    # =========================
    # GET METHODS
    # =========================

    def get_inputs_mask(self) -> int:
        with self._lock:
            return self._inputs_mask

    def get_outputs_mask(self) -> int:
        with self._lock:
            return self._outputs_mask

    def get_inputs_dict(self) -> Dict[int, bool]:
        with self._lock:
            return {
                i + 1: bool(self._inputs_mask & (1 << i))
                for i in range(32)
            }

    def get_outputs_dict(self) -> Dict[int, bool]:
        with self._lock:
            return {
                i + 1: bool(self._outputs_mask & (1 << i))
                for i in range(32)
            }

    def get_full_state(self) -> dict:
        with self._lock:
            return {
                "inputs_mask": self._inputs_mask,
                "outputs_mask": self._outputs_mask,
                "inputs": {
                    i + 1: bool(self._inputs_mask & (1 << i))
                    for i in range(32)
                },
                "outputs": {
                    i + 1: bool(self._outputs_mask & (1 << i))
                    for i in range(32)
                },
                "last_update": self._last_update
            }