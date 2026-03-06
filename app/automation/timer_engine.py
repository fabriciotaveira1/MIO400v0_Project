from __future__ import annotations

import heapq
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class TimerEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._timers: List[Tuple[float, str, Callable[..., Any], tuple, dict]] = []
        self._cancelled: Dict[str, bool] = {}
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def schedule(
        self,
        delay_ms: int,
        callback: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        timer_id: Optional[str] = None,
    ) -> str:
        if kwargs is None:
            kwargs = {}
        if timer_id is None:
            timer_id = f"timer-{time.time_ns()}"
        execute_at = time.time() + max(0, delay_ms) / 1000.0
        with self._cv:
            self._cancelled[timer_id] = False
            heapq.heappush(self._timers, (execute_at, timer_id, callback, args, kwargs))
            self._cv.notify()
        return timer_id

    def cancel(self, timer_id: str) -> None:
        with self._cv:
            self._cancelled[timer_id] = True
            self._cv.notify()

    def stop(self) -> None:
        with self._cv:
            self._running = False
            self._cv.notify_all()

    def _run(self) -> None:
        while True:
            with self._cv:
                while self._running and not self._timers:
                    self._cv.wait()
                if not self._running:
                    return

                execute_at, timer_id, callback, args, kwargs = self._timers[0]
                now = time.time()
                wait_for = execute_at - now
                if wait_for > 0:
                    self._cv.wait(timeout=wait_for)
                    continue

                heapq.heappop(self._timers)
                if self._cancelled.pop(timer_id, False):
                    continue

            try:
                callback(*args, **kwargs)
            except Exception as exc:
                print(f"[TimerEngine] Callback error: {exc}")
