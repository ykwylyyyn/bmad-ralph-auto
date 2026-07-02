#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    mode = os.environ.get("FAKE_GEMINI_MODE", "success")
    if mode == "failure":
        print(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "error",
                    "result": "Gemini request failed.",
                    "is_error": True,
                    "model": "gemini-test",
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "result": "Gemini task completed.",
                "is_error": False,
                "model": "gemini-test",
                "cost_usd": 0.12,
                "session_id": "fake-gemini-session",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
