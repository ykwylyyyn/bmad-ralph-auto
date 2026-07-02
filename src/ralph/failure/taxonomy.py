from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re


class FailureCategory(StrEnum):
  COMPILE_ERROR = "compile_error"
  TEST_FAILURE = "test_failure"
  LINT_FAILURE = "lint_failure"
  LOGIC_BUG = "logic_bug"
  DEPENDENCY_MISSING = "dependency_missing"
  HALLUCINATION = "hallucination"
  TIMEOUT = "timeout"
  SPAWN_ERROR = "spawn_error"
  VERIFICATION_FAILED = "verification_failed"
  UNKNOWN = "unknown"


_RETRYABLE = frozenset(
  {
    FailureCategory.COMPILE_ERROR,
    FailureCategory.TEST_FAILURE,
    FailureCategory.LINT_FAILURE,
    FailureCategory.LOGIC_BUG,
    FailureCategory.DEPENDENCY_MISSING,
    FailureCategory.TIMEOUT,
  }
)

_RESTART_PREFERRED = frozenset(
  {
    FailureCategory.SPAWN_ERROR,
    FailureCategory.HALLUCINATION,
  }
)


@dataclass(frozen=True, slots=True)
class FailureClassification:
  category: FailureCategory
  confidence: float
  retryable: bool
  prefer_worker_restart: bool
  signals: tuple[str, ...] = ()


_COMPILE_PATTERNS = (
  re.compile(r"\b(error|syntaxerror|cannot find symbol|undefined reference)\b", re.I),
  re.compile(r"\b(compilation failed|build failed|cargo check)\b", re.I),
)

_TEST_PATTERNS = (
  re.compile(r"\b(test failed|assertionerror|pytest|unittest\.fail)\b", re.I),
  re.compile(r"\b\d+ failed\b", re.I),
)

_LINT_PATTERNS = (
  re.compile(r"\b(clippy|eslint|ruff|pylint|lint)\b", re.I),
  re.compile(r"\bwarning.*treated as error\b", re.I),
)

_DEPENDENCY_PATTERNS = (
  re.compile(r"\b(module not found|no module named|cannot resolve|import error)\b", re.I),
  re.compile(r"\b(package not found|dependency.*not found)\b", re.I),
)

_HALLUCINATION_PATTERNS = (
  re.compile(r"\b(file not found|no such file|path does not exist)\b", re.I),
  re.compile(r"\b(hallucinat|invented|nonexistent)\b", re.I),
)

_TIMEOUT_PATTERNS = (
  re.compile(r"\b(timeout|timed out|deadline exceeded)\b", re.I),
)

_SPAWN_PATTERNS = (
  re.compile(r"\b(spawn|executable not found|command not found|enoent)\b", re.I),
)

_VERIFY_PATTERNS = (
  re.compile(r"\b(verif(y|ication) failed|verify-failed)\b", re.I),
  re.compile(r"\bmake test|pytest.*exit code [1-9]\b", re.I),
)


def classify_failure(
  reason: str,
  *,
  log_excerpt: list[str] | None = None,
  exit_code: int | None = None,
) -> FailureClassification:
  """Classify a worker/verifier failure into a taxonomy category."""

  text = reason.lower()
  if log_excerpt:
    text = f"{text}\n" + "\n".join(line.lower() for line in log_excerpt)

  signals: list[str] = []
  category = FailureCategory.UNKNOWN

  checks: list[tuple[FailureCategory, tuple[re.Pattern[str], ...]]] = [
    (FailureCategory.SPAWN_ERROR, _SPAWN_PATTERNS),
    (FailureCategory.TIMEOUT, _TIMEOUT_PATTERNS),
    (FailureCategory.VERIFICATION_FAILED, _VERIFY_PATTERNS),
    (FailureCategory.COMPILE_ERROR, _COMPILE_PATTERNS),
    (FailureCategory.TEST_FAILURE, _TEST_PATTERNS),
    (FailureCategory.LINT_FAILURE, _LINT_PATTERNS),
    (FailureCategory.DEPENDENCY_MISSING, _DEPENDENCY_PATTERNS),
    (FailureCategory.HALLUCINATION, _HALLUCINATION_PATTERNS),
  ]

  for candidate, patterns in checks:
    for pattern in patterns:
      if pattern.search(text):
        category = candidate
        signals.append(pattern.pattern)
        break
    if category != FailureCategory.UNKNOWN:
      break

  if category == FailureCategory.UNKNOWN and exit_code is not None and exit_code != 0:
    if "test" in text:
      category = FailureCategory.TEST_FAILURE
    elif "lint" in text or "clippy" in text:
      category = FailureCategory.LINT_FAILURE
    else:
      category = FailureCategory.LOGIC_BUG
    signals.append(f"exit_code={exit_code}")

  confidence = 0.9 if signals else 0.3
  return FailureClassification(
    category=category,
    confidence=confidence,
    retryable=category in _RETRYABLE,
    prefer_worker_restart=category in _RESTART_PREFERRED,
    signals=tuple(signals),
  )
