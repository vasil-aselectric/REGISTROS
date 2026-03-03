# app/sim/plc_sim.py
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class SimState:
    cloro: float = 1.2
    turbidez: float = 0.8
    temperatura: float = 24.0
    ts: str = ""  # timestamp ISO, lo ponemos al leer


class PlcSim:
    """
    Simulador simple para 3 variables (cloro, turbidez, temperatura).
    - Mantiene valores en memoria (thread-safe)
    - Opcional: "suaviza" hacia un setpoint para que no sea un salto brusco (look&feel real)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = SimState()
        self._targets = {
            "cloro": self._state.cloro,
            "turbidez": self._state.turbidez,
            "temperatura": self._state.temperatura,
        }
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        # Pequeña dinámica: converge suavemente hacia el target
        # (si quieres que sea “instantáneo”, te lo quito)
        while self._running:
            with self._lock:
                self._state.cloro = self._approach(self._state.cloro, self._targets["cloro"], step=0.05)
                self._state.turbidez = self._approach(self._state.turbidez, self._targets["turbidez"], step=0.05)
                self._state.temperatura = self._approach(self._state.temperatura, self._targets["temperatura"], step=0.10)
            time.sleep(0.5)

    @staticmethod
    def _approach(current: float, target: float, step: float) -> float:
        if current < target:
            return min(current + step, target)
        if current > target:
            return max(current - step, target)
        return current

    def get_state(self) -> Dict[str, float]:
        with self._lock:
            return {
                "cloro": float(self._state.cloro),
                "turbidez": float(self._state.turbidez),
                "temperatura": float(self._state.temperatura),
            }

    def set_value(self, key: str, value: float) -> None:
        key = key.strip().lower()
        if key not in self._targets:
            raise ValueError(f"Unknown key: {key}")

        # Validaciones básicas (ajústalas a tu rango real)
        if key == "cloro" and not (0.0 <= value <= 5.0):
            raise ValueError("Cloro fuera de rango (0..5)")
        if key == "turbidez" and not (0.0 <= value <= 10.0):
            raise ValueError("Turbidez fuera de rango (0..10)")
        if key == "temperatura" and not (0.0 <= value <= 60.0):
            raise ValueError("Temperatura fuera de rango (0..60)")

        with self._lock:
            self._targets[key] = float(value)