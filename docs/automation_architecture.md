# Automation Architecture

## System Overview

This project runs automation logic entirely on the server side, acting as a PLC-like logical programmer for Commbox MIO devices.

Core flow:

```text
Input Event
  |
  v
SocketListener
  |
  v
StateManager
  |
  v
AutomationEngine
  |
  v
ConditionEvaluator
  |
  v
ActionExecutor
  |
  v
DeviceManager -> CommboxClient -> MIO Relay Output
```

## Components

- `SocketListener`
  - Receives async device frames/events (opcode 30/92).
  - Updates `StateManager`.
  - Calls `automation_engine.process_input_event(...)` for digital input events.

- `StateManager`
  - Thread-safe runtime state for input/output masks.
  - Supplies current state for condition evaluation.

- `AutomationEngine`
  - Central orchestrator.
  - Handles event triggers, while/state triggers, and scheduled time triggers.
  - Evaluates rule conditions and dispatches actions.
  - Runs a background scan loop for `while` and `time` triggers.

- `ConditionEvaluator`
  - Evaluates:
    - input conditions
    - state conditions
    - time range conditions
    - logical AND/OR/NOT conditions

- `ActionExecutor`
  - Executes rule actions:
    - output control (on/off/toggle)
    - delay sequencing
    - logging
    - timer actions (TON/TOFF/PULSE style behavior)

- `TimerEngine`
  - Background scheduler for delayed callbacks.
  - Used by `ActionExecutor` to run delayed and pulse operations.

- `RuleManager`
  - CRUD for automation rules.
  - Enable/disable state.
  - I/O naming map management.
  - Persists state through JSON storage.

## Storage

Rules and names are persisted in:

- `app/automation/data/automation_rules.json`
- `app/automation/data/io_names.json`

Storage is thread-safe and writes atomically with temp-file replacement.

## Rule Structure

```json
{
  "id": 1,
  "name": "Alarm While Door Open",
  "trigger": {
    "type": "while",
    "input": 1,
    "state": true
  },
  "conditions": [
    {
      "type": "time_range",
      "start": "18:00",
      "end": "06:00"
    },
    {
      "type": "logical",
      "operator": "AND",
      "conditions": [
        {"type": "input", "input": 2, "state": false},
        {"type": "state", "scope": "output", "channel": 3, "state": false}
      ]
    }
  ],
  "actions": [
    {"type": "log", "message": "Rule fired"},
    {"type": "output", "output": 2, "action": "on", "duration_ms": 3000}
  ],
  "enabled": true
}
```

## API Surface

- Rule APIs (`routes_automation.py`)
  - `GET /automation/rules`
  - `POST /automation/rules`
  - `PUT /automation/rules/{id}`
  - `DELETE /automation/rules/{id}`
  - `PUT /automation/rules/{id}/enable`
  - `PUT /automation/rules/{id}/disable`

- I/O naming APIs
  - `GET /io/names`
  - `POST /io/names`

## GUI Integration

- New `Automation` tab:
  - rule table
  - Add/Edit/Delete
  - Enable/Disable
  - Save/refresh sync
- Rule editor dialog supports trigger, conditions, and actions.
- Main I/O screen shows configured I/O names from `/io/names`.

