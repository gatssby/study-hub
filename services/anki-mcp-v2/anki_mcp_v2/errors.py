from __future__ import annotations

from typing import Any


class McpApiError(RuntimeError):
    """A sanitized error suitable for returning from an MCP tool."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details

    def as_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": str(self)}
        if self.status is not None:
            error["status"] = self.status
        if self.details:
            error["details"] = self.details
        return {"error": error}
