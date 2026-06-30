from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


RequestType = Literal["status", "stop", "diagnose", "retry"]
ResponseType = Literal["ok", "error"]


@dataclass(slots=True)
class Request:
    type: RequestType
    story_id: int | None = None
    graceful: bool | None = None

    def to_json_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        if self.story_id is not None:
            data["story_id"] = self.story_id
        if self.graceful is not None:
            data["graceful"] = self.graceful
        return data


@dataclass(slots=True)
class Response:
    type: ResponseType
    message: str
    data: dict[str, Any] | None = None

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type, "message": self.message}
        if self.data is not None:
            payload["data"] = self.data
        return payload
