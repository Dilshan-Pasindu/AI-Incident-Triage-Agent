"""
agent-client/cancellation.py

Cancellation Token implementation for the Incident Triage Agent.
Provides explicit checkpoint cancellation without abruptly killing shared MCPHub connections.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class CancelledError(asyncio.CancelledError):
    """Raised when an operation is cancelled via CancellationToken."""
    def __init__(self, reason: str = "Operation was cancelled"):
        super().__init__(reason)
        self.reason = reason


class CancellationToken:
    """
    Thread-safe / async cancellation token wrapping asyncio.Event.
    Checked at critical boundaries in the agent loop:
    1. Before every LLM call
    2. Immediately after every LLM response
    3. Before every tool call in a batch
    4. After every approval wait
    5. Immediately before tool dispatch
    """

    def __init__(self):
        self._event = asyncio.Event()
        self._reason: Optional[str] = None

    def cancel(self, reason: str = "cancelled") -> None:
        """Signal cancellation with a reason."""
        self._reason = reason
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._event.is_set()

    @property
    def reason(self) -> str:
        """Get the cancellation reason, if cancelled."""
        return self._reason or "cancelled"

    def raise_if_cancelled(self) -> None:
        """Raise CancelledError if cancellation was signaled."""
        if self.is_cancelled:
            raise CancelledError(f"Run cancelled: {self.reason}")

    async def wait_cancelled(self) -> None:
        """Await until cancellation is signaled."""
        await self._event.wait()
