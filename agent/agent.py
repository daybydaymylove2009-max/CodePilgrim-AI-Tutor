"""
CodePilgrim Local Agent - 本地代码执行代理

功能:
- WebSocket 服务监听浏览器连接
- HTTP 健康检查接口
- Docker 容器执行 (优先) / 本地子进程执行 (回退)
- 执行超时控制与资源限制

启动方式:
  python agent.py [--port 18765] [--host 127.0.0.1]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import shutil
import sys
import uuid

from aiohttp import web, WSMsgType

try:
    import docker
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False


class CodeExecutor:
    def __init__(self, timeout: int = 10, memory_mb: int = 128):
        self.timeout = timeout
        self.memory_mb = memory_mb
        self._docker_client = None
        self._docker_available: bool | None = None

    def _check_docker(self) -> bool:
        if self._docker_available is not None:
            return self._docker_available
        if not HAS_DOCKER:
            self._docker_available = False
            return False
        try:
            client = docker.from_env()
            client.ping()
            self._docker_client = client
            self._docker_available = True
        except Exception:
            self._docker_available = False
        return self._docker_available

    async def execute(self, code: str, language: str = "python") -> dict:
        if self._check_docker():
            return await self._execute_docker(code, language)
        return await self._execute_local(code, language)

    async def _execute_docker(self, code: str, language: str) -> dict:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._docker_run_sync, code, language)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _docker_run_sync(self, code: str, language: str) -> dict:
        if language == "python":
            cmd = ["python3", "-c", code]
        elif language == "javascript":
            cmd = ["node", "-e", code]
        else:
            return {"success": False, "error": f"Unsupported language: {language}"}

        try:
            container = self._docker_client.containers.run(
                image="codepilgrim-sandbox:latest",
                command=cmd,
                mem_limit=f"{self.memory_mb}m",
                network_disabled=True,
                read_only=True,
                tmpfs={"/tmp": "size=10m"},
                detach=True,
            )
            result = container.wait(timeout=self.timeout)
            exit_code = result.get("StatusCode", -1)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            container.remove(force=True)
            return {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_local(self, code: str, language: str) -> dict:
        start = time.monotonic()
        if language == "python":
            cmd = [sys.executable, "-c", code]
        elif language == "javascript":
            node_path = shutil.which("node")
            if not node_path:
                return {"success": False, "error": "Node.js not installed"}
            cmd = [node_path, "-e", code]
        else:
            return {"success": False, "error": f"Unsupported language: {language}"}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": stderr_bytes.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode or 0,
                "execution_time_ms": elapsed,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"success": False, "error": f"Timeout ({self.timeout}s)", "exit_code": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "exit_code": -1}


executor = CodeExecutor()


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "docker": executor._check_docker(),
        "version": "0.1.0",
    })


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            msg_id = data.get("id", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong", "id": msg_id})
            elif msg_type == "execute":
                payload = data.get("payload", {})
                code = payload.get("code", "")
                language = payload.get("language", "python")

                result = await executor.execute(code, language)
                result["execution_time_ms"] = result.get("execution_time_ms", 0)
                result["memory_used_mb"] = result.get("memory_used_mb", 0)
                result["error_type"] = result.get("error_type", None)
                result["error_message"] = result.get("error_message", None)

                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "payload": result,
                })
        elif msg.type == WSMsgType.ERROR:
            break

    return ws


def main():
    parser = argparse.ArgumentParser(description="CodePilgrim Local Agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()

    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ws", ws_handler)

    print(f"CodePilgrim Agent starting on ws://{args.host}:{args.port}")
    print(f"Docker available: {executor._check_docker()}")
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
