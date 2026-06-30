from __future__ import annotations

from ralph.common.errors import RalphError


class ArtifactError(RalphError):
    """Base exception for BMAD artifact parsing errors."""


class SprintPlanNotFoundError(ArtifactError):
    def __init__(self, project_dir: str) -> None:
        super().__init__("No sprint plan found in project")
        self.project_dir = project_dir
        self.guidance = "Run BMAD sprint planning first, then try ralph start again."


class ArtifactParseError(ArtifactError):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"failed to parse artifact {path}: {message}")
        self.path = path
        self.detail = message
