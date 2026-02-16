---
name: app-automation
description: This skill should be used when users want to automate any macOS application using homerow-style navigation. It can scan UI elements, click by hints, copy text, and run multi-step workflows on any app (LINE, Safari, Finder, etc.).
---

# App Automation Skill

This skill automates any macOS application using homerow-style keyboard navigation.

## Capabilities

1. **Scan** - Detect clickable elements in any app
2. **Click** - Click elements by hint
3. **Copy** - Drag-select and copy text to file
4. **Workflow** - Run multi-step automation sequences

## Usage

### Scan App Elements

```bash
python3 scripts/auto_app.py <APP_NAME> scan
```

Examples:
```bash
python3 scripts/auto_app.py LINE scan
python3 scripts/auto_app.py Safari scan
python3 scripts/auto_app.py Finder scan
```

### Click Element

```bash
python3 scripts/auto_app.py <APP_NAME> click <HINT>
python3 scripts/auto_app.py <APP_NAME> click <HINT> right  # Right click
```

### Copy Text

```bash
python3 scripts/auto_app.py <APP_NAME> copy <HINT>
python3 scripts/auto_app.py <APP_NAME> copy <HINT> output.txt
```

### Run Workflow

```bash
python3 scripts/auto_app.py <APP_NAME> workflow workflow.json
```

## Workflow JSON Format

Create a JSON file to automate multi-step operations:

```json
{
  "name": "LINE Message Extraction",
  "steps": [
    {"action": "activate", "app": "LINE"},
    {"action": "scan"},
    {"action": "click", "hint": "AH", "delay": 0.5},
    {"action": "scan"},
    {"action": "copy", "hint": "SA", "output": "message.txt"},
    {"action": "wait", "seconds": 1},
    {"action": "click", "hint": "SG"}
  ]
}
```

### Available Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `activate` | `app` | Activate the app |
| `scan` | `app` | Scan UI elements |
| `click` | `hint`, `right`, `delay` | Click element |
| `copy` | `hint`, `output` | Drag-copy to file |
| `wait` | `seconds` | Wait specified time |

## Output

- JSON: `homerow_output/<app>_elements.json`
- Text: `homerow_output/<app>_YYYYMMDD_HHMMSS.txt`

## Example Workflows

### Extract LINE Messages

```json
{
  "name": "Extract LINE chats",
  "steps": [
    {"action": "scan"},
    {"action": "click", "hint": "AH"},
    {"action": "wait", "seconds": 0.5},
    {"action": "scan"},
    {"action": "copy", "hint": "SA"},
    {"action": "copy", "hint": "AL"}
  ]
}
```

### Safari Automation

```bash
python3 scripts/auto_app.py Safari scan
python3 scripts/auto_app.py Safari click AS   # URL bar
python3 scripts/auto_app.py Safari copy FG    # Copy content
```
