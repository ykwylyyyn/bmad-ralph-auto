#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    mode = os.environ.get("FAKE_CLAUDE_MODE", "success")
    if mode == "failure":
        print(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "error_max_turns",
                    "result": "Max turns reached.",
                    "is_error": True,
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": "Task completed.",
                "is_error": False,
                "session_id": "fake-session",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
