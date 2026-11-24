"""Bounded public diagnostics for operation validation (DEV-075)."""

from __future__ import annotations

import difflib
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

_MAX_ERRORS = 8
_MAX_MESSAGE = 600


class OperationValidationError(ValidationError):
    """Keep the ValidationError interface while giving users a small message."""

    def __str__(self) -> str:
        errors = self.errors(include_url=False, include_context=False, include_input=False)
        lines = []
        for error in errors[:_MAX_ERRORS]:
            loc = list(error["loc"])
            path = ""
            if (
                len(loc) >= 3
                and loc[0] == "operations"
                and type(loc[1]) is int
                and isinstance(loc[2], str)
            ):
                loc.pop(2)
            if loc and type(loc[0]) is int:
                index = loc.pop(0)
                if self.title != "operation":
                    path = f"operations[{index}]"
                # Discriminated-union branch names are internal, not parameters.
                if loc and isinstance(loc[0], str):
                    loc.pop(0)
            for part in loc:
                if type(part) is int:
                    path += f"[{part}]"
                else:
                    path += ("." if path else "") + str(part)[:80]
            kind = error["type"]
            if kind == "union_tag_invalid":
                message = "Unknown operation; see creo_capabilities for enabled op names"
            elif kind == "union_tag_not_found":
                message = "An op field is required"
            else:
                message = error["msg"].removeprefix("Value error, ")
            message = " ".join(message.split())
            if len(message) > _MAX_MESSAGE:
                message = message[:_MAX_MESSAGE] + "..."
            lines.append(f"{path or 'parameters'}: {message}")
        if len(errors) > _MAX_ERRORS:
            lines.append(f"{len(errors) - _MAX_ERRORS} more validation errors; fix these first")
        return "\n".join(lines)


def operation_validation_error(
    error: ValidationError, *, single_operation: bool | None
) -> OperationValidationError:
    """Preserve structured errors without rendering inputs or the union title.

    Custom errors also occur in nested validators. Rewrap their already formatted
    messages with a fixed template so arbitrary braces in a diagnostic cannot be
    interpreted as template fields. Original inputs remain available to internal
    ``errors()`` callers; public ``str()`` never requests them.
    """
    lines = [
        {
            "type": PydanticCustomError(
                item["type"], "{message}", {**item.get("ctx", {}), "message": item["msg"]}
            ),
            "loc": item["loc"],
            "input": item.get("input"),
        }
        for item in error.errors(include_url=False)
    ]
    return OperationValidationError.from_exception_data(
        "arguments" if single_operation is None else "operation" if single_operation else "plan",
        lines,
        hide_input=True,
    )


class ValidationMCPServer(MCPServer):
    """Sanitize argument-validation failures through the public call hook.

    The SDK validates typed tool arguments before invoking their bodies. This
    hook handles that boundary as well, while retaining the registered schemas,
    resolver behavior, and all non-validation error handling in the SDK.
    """

    async def call_tool(self, name: str, arguments: dict[str, Any], context: Any = None) -> Any:
        # BUG-189: reject unknown tool arguments instead of silently dropping them.
        if isinstance(arguments, dict) and arguments:
            tool = self._tool_manager.get_tool(name)
            params = getattr(tool, "parameters", None) if tool is not None else None
            properties = params.get("properties") if isinstance(params, dict) else None
            if isinstance(properties, dict) and params.get("additionalProperties") is not True:
                allowed = sorted(properties.keys())
                unknown = sorted(k for k in arguments if k not in properties)
                if unknown:
                    hints = []
                    for key in unknown[:5]:
                        close = difflib.get_close_matches(key, allowed, n=1, cutoff=0.6)
                        if close:
                            hints.append(f"unknown argument '{key}'; did you mean '{close[0]}'?")
                        else:
                            hints.append(f"unknown argument '{key}'")
                    valid_list = ", ".join(allowed[:20])
                    if len(allowed) > 20:
                        valid_list += f", ... ({len(allowed)} total)"
                    raise ToolError(
                        f"Error executing tool {name}: {'; '.join(hints)}. "
                        f"Valid arguments: {valid_list}"
                    ) from None
        try:
            return await super().call_tool(name, arguments, context)
        except UnexpectedToolError:
            # Output conversion failures and validator crashes keep SDK masking.
            raise
        except ToolError as exc:
            if isinstance(exc.__cause__, ValidationError):
                safe = operation_validation_error(exc.__cause__, single_operation=None)
                raise ToolError(f"Error executing tool {name}: {safe}") from None
            raise
