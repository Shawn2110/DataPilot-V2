"""
Local IPython kernel wrapper using jupyter_client.

State persists across executions, so the user can upload a CSV once and
keep referring to `df` in later turns. No Jupyter Server needed — the
kernel runs as a child process of the CLI.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass, field

from jupyter_client.manager import KernelManager


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    result: str = ""
    error: str | None = None
    images: list[str] = field(default_factory=list)


class LocalKernel:
    def __init__(self) -> None:
        self._km: KernelManager | None = None
        self._kc = None

    def start(self) -> None:
        if self._km is not None:
            return
        self._km = KernelManager(kernel_name="python3")
        self._km.start_kernel()
        self._kc = self._km.client()
        self._kc.start_channels()
        self._kc.wait_for_ready(timeout=30)

    def stop(self) -> None:
        if self._kc is not None:
            self._kc.stop_channels()
            self._kc = None
        if self._km is not None:
            self._km.shutdown_kernel(now=True)
            self._km = None

    def execute(self, code: str, timeout: float = 60.0) -> ExecutionResult:
        if self._kc is None:
            raise RuntimeError("Kernel not started — call start() first.")

        msg_id = self._kc.execute(code, store_history=True, allow_stdin=False)
        out = ExecutionResult()

        while True:
            try:
                msg = self._kc.get_iopub_msg(timeout=timeout)
            except queue.Empty:
                out.error = f"Execution timed out after {timeout}s"
                break

            parent = msg.get("parent_header", {}).get("msg_id")
            if parent != msg_id:
                continue

            msg_type = msg.get("msg_type", "")
            content = msg.get("content", {})

            if msg_type == "stream":
                if content.get("name") == "stdout":
                    out.stdout += content.get("text", "")
                elif content.get("name") == "stderr":
                    out.stderr += content.get("text", "")

            elif msg_type in ("execute_result", "display_data"):
                data = content.get("data", {})
                if "text/plain" in data:
                    if out.result:
                        out.result += "\n"
                    out.result += data["text/plain"]
                if "image/png" in data:
                    out.images.append(data["image/png"])

            elif msg_type == "error":
                out.error = "\n".join(content.get("traceback", []))

            elif msg_type == "status" and content.get("execution_state") == "idle":
                break

        return out
