#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
python orchestrator.py --cron >> logs/cron_stdout.log 2>&1
