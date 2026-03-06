from __future__ import annotations

from typing import Any, Dict, List

from app.automation.timer_engine import TimerEngine
from app.core.opcodes.output import build_output_command
from app.services.device_manager import device_manager


class ActionExecutor:
    def __init__(self, timer_engine: TimerEngine):
        self.timer_engine = timer_engine

    def execute_actions(self, actions: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
        if not actions:
            return
        self._execute_sequence(actions, 0, context)

    def _execute_sequence(
        self,
        actions: List[Dict[str, Any]],
        index: int,
        context: Dict[str, Any],
    ) -> None:
        if index >= len(actions):
            return

        action = actions[index]
        atype = action.get("type")

        if atype == "delay":
            delay_ms = int(action.get("duration_ms", action.get("delay_ms", 0)))
            self.timer_engine.schedule(
                delay_ms=delay_ms,
                callback=self._execute_sequence,
                args=(actions, index + 1, context),
            )
            return

        if atype == "output":
            self._execute_output(action)
        elif atype == "log":
            message = str(action.get("message", f"Rule log: {context.get('rule_name', '')}"))
            print(f"[AUTOMATION] {message}")
        elif atype == "timer":
            self._execute_timer_action(action)

        self._execute_sequence(actions, index + 1, context)

    def _execute_output(self, action: Dict[str, Any]) -> None:
        output_id = int(action.get("output", action.get("channel", 0)))
        if output_id <= 0:
            return

        desired_action = str(action.get("action", "on")).lower()
        if desired_action == "on":
            cmd = 1
        elif desired_action == "off":
            cmd = 0
        else:
            cmd = 2

        self._send_output(output_id, cmd)

        duration_ms = int(action.get("duration_ms", 0))
        if desired_action == "on" and duration_ms > 0:
            self.timer_engine.schedule(
                delay_ms=duration_ms,
                callback=self._send_output,
                args=(output_id, 0),
            )

    def _execute_timer_action(self, action: Dict[str, Any]) -> None:
        mode = str(action.get("mode", "pulse")).lower()
        output_id = int(action.get("output", 0))
        duration_ms = int(action.get("duration_ms", 0))
        if output_id <= 0 or duration_ms <= 0:
            return

        if mode == "ton":
            self.timer_engine.schedule(
                delay_ms=duration_ms,
                callback=self._send_output,
                args=(output_id, 1),
            )
            return

        if mode == "toff":
            self._send_output(output_id, 1)
            self.timer_engine.schedule(
                delay_ms=duration_ms,
                callback=self._send_output,
                args=(output_id, 0),
            )
            return

        # pulse
        self._send_output(output_id, 1)
        self.timer_engine.schedule(
            delay_ms=duration_ms,
            callback=self._send_output,
            args=(output_id, 0),
        )

    @staticmethod
    def _send_output(output_id: int, command: int) -> None:
        try:
            client = device_manager.get_client()
        except RuntimeError as exc:
            print(f"[AUTOMATION] Device not configured: {exc}")
            return

        payload = build_output_command(
            component_addr=output_id,
            action=command,
            total_time=0,
            memory=0,
        )
        response = client.send(opcode=1, application_data=payload)
        if response.get("status") != "ack":
            print(f"[AUTOMATION] Output command failed: {response}")
