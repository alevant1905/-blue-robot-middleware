"""
Blue Robot LLM Client
=====================
Handles communication with LM Studio (local LLM).
"""

# Future imports
from __future__ import annotations

# Standard library
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Third-party
import requests

# Local imports
from .utils import log

# ================================================================================
# CONFIGURATION
# ================================================================================

LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "local-model")
LM_STUDIO_RAG_URL = "http://127.0.0.1:1234/v1/rag"


# ================================================================================
# SETTINGS
# ================================================================================

@dataclass
class Settings:
    """Application settings."""
    LOG_LEVEL: str = "INFO"
    MAX_ITERATIONS: int = 6  # Balanced: allows tool use + response (was 10, too many; 4 was too few)
    TOOL_TIMEOUT_SECS: float = 15.0
    TOOL_RETRIES: int = 2
    MAX_CONTEXT_MESSAGES: int = 20
    AUTO_DOCSEARCH_MODE: str = "opt_in"
    USE_SMART_TOOL_FILTERING: bool = True   # Enable intelligent tool filtering
    USE_STRICT_TOOL_FORCING: bool = False   # Disabled: qwen3-vl doesn't support strict tool_choice (uses 'required' instead)


settings = Settings()


# ================================================================================
# LM STUDIO CLIENT
# ================================================================================

class LMStudioClient:
    """
    Enhanced client for local LM Studio (OpenAI-compatible) chat completions.
    Features:
    - Auto-retry with exponential backoff
    - Connection health checks
    - Request/response logging
    - Timeout management
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3
    ):
        self.base_url = base_url or LM_STUDIO_URL
        self.model = model or LM_STUDIO_MODEL
        self.timeout = float(timeout or os.environ.get("LM_STUDIO_TIMEOUT", "120"))
        self.max_retries = max_retries
        self._healthy = None
        self._last_health_check = 0

    def is_healthy(self, force_check: bool = False) -> bool:
        """Check if LM Studio is responding (cached for 60s)."""
        now = time.time()
        if not force_check and self._healthy is not None and (now - self._last_health_check) < 60:
            return self._healthy

        try:
            health_url = self.base_url.replace('/chat/completions', '/models')
            resp = requests.get(health_url, timeout=5)
            self._healthy = resp.status_code == 200
        except Exception:
            self._healthy = False

        self._last_health_check = now
        return self._healthy

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Send a chat completion request to LM Studio."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if extra and isinstance(extra, dict):
            payload.update(extra)
        if kwargs:
            payload.update(kwargs)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(self.base_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                result = resp.json()

                if 'choices' not in result and 'error' not in result:
                    raise ValueError(f"Unexpected response structure: {list(result.keys())}")

                return result

            except requests.exceptions.Timeout as e:
                last_error = e
                wait_time = 2 ** attempt
                log.warning(f"[LLM] Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)

            except requests.exceptions.ConnectionError as e:
                last_error = e
                wait_time = 2 ** attempt
                log.warning(f"[LLM] Connection error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code < 500:
                    return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
                last_error = e
                wait_time = 2 ** attempt
                log.warning(f"[LLM] Server error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)

            except Exception as e:
                last_error = e
                log.error(f"[LLM] Unexpected error: {e}")
                break

        return {"error": f"LLM request failed after {self.max_retries} attempts: {last_error}"}


# ================================================================================
# GLOBAL CLIENT
# ================================================================================

_lm_client: Optional[LMStudioClient] = None


def get_lm_client() -> Optional[LMStudioClient]:
    """Get or create the global LM Studio client."""
    global _lm_client
    if _lm_client is None:
        try:
            _lm_client = LMStudioClient()
        except Exception as e:
            log.warning(f"Failed to init LM Studio client: {e}")
    return _lm_client


def call_llm(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    include_tools: bool = True,
    tool_choice: Any = "auto",  # Can be string or dict for strict forcing
    force_tool: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Unified LLM entrypoint: always uses local LM Studio.

    Args:
        messages: List of conversation messages
        tools: List of tool definitions (optional)
        include_tools: Whether to include tools in the request
        tool_choice: Tool selection mode ("auto", "none", or dict for strict forcing)
                    Examples:
                    - "auto": Let model decide
                    - "none": Don't use tools
                    - {"type": "function", "function": {"name": "play_music"}}: Force specific tool
        force_tool: If set, STRICTLY force the model to use this specific tool (legacy param)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        extra: Additional parameters to pass to the API
        **kwargs: Additional keyword arguments

    Returns:
        API response dictionary
    """
    client = get_lm_client()
    if client is None:
        return {"error": "LM Studio client not available"}

    # Convert legacy force_tool parameter to strict tool_choice
    if force_tool and isinstance(tool_choice, str):
        # Use strict forcing instead of just nudging
        tool_choice = {
            "type": "function",
            "function": {"name": force_tool}
        }
        print(f"   [TOOL_CHOICE] Strict forcing enabled for: {force_tool}")

    tools_payload = tools if include_tools and tools else None

    try:
        return client.chat(
            messages,
            tools=tools_payload,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
            **kwargs
        )
    except Exception as e:
        return {"error": f"LM Studio request failed: {e}"}


# Initialize client on import
_lm_client = get_lm_client()
