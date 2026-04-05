"""
client.py — Jupyter Server REST API client.

This is used by the WEB APP path only. The VS Code extension uses
its own Jupyter kernel directly (via the VS Code Jupyter extension).

Jupyter Server exposes REST endpoints:
  - POST /api/kernels         → start a kernel
  - DELETE /api/kernels/{id}  → stop a kernel
  - GET /api/contents/{path}  → read a notebook file
  - PUT /api/contents/{path}  → save a notebook file

Code execution uses the Jupyter WebSocket protocol:
  - WS /api/kernels/{id}/channels → send execute_request, receive results
"""

import json
import asyncio
from typing import Any

import httpx


class JupyterClient:
    """HTTP + WebSocket client for Jupyter Server."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {"Authorization": f"token {token}"}

    async def start_kernel(self, kernel_name: str = "python3") -> str:
        """
        Start a new Jupyter kernel.

        Returns the kernel ID.
        A kernel is an isolated Python process that executes code.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/kernels",
                headers=self.headers,
                json={"name": kernel_name},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def stop_kernel(self, kernel_id: str) -> None:
        """Stop a running kernel."""
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{self.base_url}/api/kernels/{kernel_id}",
                headers=self.headers,
            )

    async def execute_code(self, kernel_id: str, code: str, timeout: float = 30.0) -> dict:
        """
        Execute code in a Jupyter kernel via WebSocket.

        The Jupyter kernel protocol:
        1. Connect to WS /api/kernels/{id}/channels
        2. Send an execute_request message
        3. Receive stream/execute_result/error messages
        4. Receive execute_reply (marks completion)

        Returns: {"stdout": str, "stderr": str, "result": str, "error": str|None}
        """
        import websockets

        ws_url = self.base_url.replace("http", "ws")
        url = f"{ws_url}/api/kernels/{kernel_id}/channels?token={self.token}"

        output = {"stdout": "", "stderr": "", "result": "", "error": None}

        # Build execute_request message (Jupyter messaging protocol)
        msg_id = f"datapilot-{id(code)}"
        execute_request = {
            "header": {
                "msg_id": msg_id,
                "msg_type": "execute_request",
                "username": "datapilot",
                "session": msg_id,
                "version": "5.3",
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "buffers": [],
            "channel": "shell",
        }

        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(execute_request))

                # Listen for responses until we get execute_reply
                start = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start < timeout:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw)
                    except asyncio.TimeoutError:
                        continue

                    msg_type = msg.get("msg_type", msg.get("header", {}).get("msg_type", ""))
                    content = msg.get("content", {})

                    if msg_type == "stream":
                        if content.get("name") == "stdout":
                            output["stdout"] += content.get("text", "")
                        elif content.get("name") == "stderr":
                            output["stderr"] += content.get("text", "")

                    elif msg_type == "execute_result":
                        data = content.get("data", {})
                        output["result"] = data.get("text/plain", "")

                    elif msg_type == "error":
                        output["error"] = "\n".join(content.get("traceback", []))

                    elif msg_type == "execute_reply":
                        if content.get("status") == "error":
                            output["error"] = content.get("evalue", "Unknown error")
                        break

        except Exception as e:
            output["error"] = str(e)

        return output

    async def get_notebook(self, path: str) -> dict:
        """Read a notebook file from Jupyter Server."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/contents/{path}",
                headers=self.headers,
                params={"content": 1},
            )
            resp.raise_for_status()
            return resp.json()

    async def save_notebook(self, path: str, content: dict) -> None:
        """Save a notebook file to Jupyter Server."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/api/contents/{path}",
                headers=self.headers,
                json={
                    "type": "notebook",
                    "content": content,
                },
            )
            resp.raise_for_status()
