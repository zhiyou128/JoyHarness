#!/bin/bash
# JoyHarness macOS launcher.
# Double-click this file to start JoyHarness.
cd "$(dirname "$0")" || exit 1

if [ -x ".venv311/bin/python" ]; then
  PYTHON=".venv311/bin/python"
elif [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" -m src "$@"
