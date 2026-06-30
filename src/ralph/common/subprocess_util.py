from __future__ import annotations

import subprocess
from typing import Any

# Windows locales (e.g. zh-CN) default subprocess text decoding to GBK, which
# crashes on UTF-8 output from tools like npx/npm. Always decode as UTF-8.
TEXT_CAPTURE_KWARGS: dict[str, Any] = {
    "capture_output": True,
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}


def run_text_capture(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    merged = {**TEXT_CAPTURE_KWARGS, **kwargs}
    return subprocess.run(*popenargs, **merged)
