"""Base agent class with typed input/output and tracing."""

from __future__ import annotations

import abc
import time
from typing import Generic, TypeVar

from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentTrace(BaseModel):
    agent_name: str
    started_at: float
    finished_at: float
    duration_ms: float
    llm_calls: int = 0
    error: str | None = None


class BaseAgent(abc.ABC, Generic[InputT, OutputT]):
    name: str = "base"

    @abc.abstractmethod
    def run(self, input_msg: InputT) -> OutputT: ...

    def run_traced(self, input_msg: InputT) -> tuple[OutputT, AgentTrace]:
        start = time.time()
        error = None
        try:
            result = self.run(input_msg)
        except Exception as e:
            error = str(e)
            raise
        finally:
            end = time.time()
        trace = AgentTrace(
            agent_name=self.name,
            started_at=start,
            finished_at=end,
            duration_ms=(end - start) * 1000,
            error=error,
        )
        return result, trace
