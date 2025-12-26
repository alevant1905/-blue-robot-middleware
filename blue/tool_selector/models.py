"""
Data models for tool selection.

Defines the core data structures used throughout the tool selector.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolIntent:
    """Represents a detected intent to use a specific tool."""

    tool_name: str
    confidence: float  # 0.0 to 1.0
    priority: int  # Lower number = higher priority
    reason: str  # Why this tool was selected
    extracted_params: Dict[str, Any] = field(default_factory=dict)
    negative_signals: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"ToolIntent(tool={self.tool_name}, "
            f"conf={self.confidence:.2f}, "
            f"priority={self.priority}, "
            f"params={len(self.extracted_params)} items)"
        )


@dataclass
class ToolSelectionResult:
    """Result of tool selection analysis."""

    primary_tool: Optional[ToolIntent]
    alternative_tools: List[ToolIntent]
    needs_disambiguation: bool
    disambiguation_prompt: Optional[str]
    compound_request: bool  # True if multiple tools needed

    def __repr__(self) -> str:
        primary = self.primary_tool.tool_name if self.primary_tool else "None"
        alts = len(self.alternative_tools)
        return (
            f"ToolSelectionResult(primary={primary}, "
            f"alternatives={alts}, "
            f"disambiguation={self.needs_disambiguation})"
        )
