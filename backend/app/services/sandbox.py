from __future__ import annotations

import asyncio
import tempfile
import os

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from app.core.config import settings
from app.schemas.learning import ExecutionResult


class CodeSandbox:
    """
    Docker 隔离的代码执行沙箱.

    安全约束：
    - 内存限制 (默认128MB)
    - 执行超时 (默认10秒)
    - 网络隔离
    - 只读文件系统（除 /tmp）
    - 无特权模式
    """

    def __init__(self):
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def _ensure_image(self):
        try:
            self.client.images.get(settings.SANDBOX_DOCKER_IMAGE)
        except ImageNotFound:
            self._build_sandbox_image()

    def _build_sandbox_image(self):
        dockerfile = """
FROM python:3.11-slim
RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            df_path = os.path.join(tmpdir, "Dockerfile")
            with open(df_path, "w") as f:
                f.write(dockerfile)
            self.client.images.build(path=tmpdir, tag=settings.SANDBOX_DOCKER_IMAGE, rm=True)

    async def execute(self, code: str, language: str = "python") -> ExecutionResult:
        self._ensure_image()

        if language == "python":
            return await self._execute_python(code)
        if language == "javascript":
            return await self._execute_javascript(code)
        return ExecutionResult(success=False, error_type="unsupported", error_message=f"Unsupported language: {language}")

    async def _execute_python(self, code: str) -> ExecutionResult:
        safe_code = self._sanitize_python(code)
        return await self._run_container(safe_code, "python3", "-c")

    async def _execute_javascript(self, code: str) -> ExecutionResult:
        safe_code = self._sanitize_javascript(code)
        return await self._run_container(safe_code, "node", "-e")

    async def _run_container(self, code: str, cmd: str, flag: str) -> ExecutionResult:
        loop = asyncio.get_event_loop()

        try:
            output = await loop.run_in_executor(
                None,
                self._run_container_sync,
                code,
                cmd,
                flag,
            )
            return output
        except ContainerError as e:
            return ExecutionResult(
                success=False,
                stderr=e.stderr.decode("utf-8", errors="replace") if e.stderr else "",
                exit_code=e.exit_status,
                error_type="runtime_error",
            )
        except APIError as e:
            return ExecutionResult(
                success=False,
                error_type="docker_error",
                error_message=str(e),
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_type="unknown_error",
                error_message=str(e),
            )

    def _run_container_sync(self, code: str, cmd: str, flag: str) -> ExecutionResult:
        container = self.client.containers.run(
            image=settings.SANDBOX_DOCKER_IMAGE,
            command=[cmd, flag, code],
            mem_limit=f"{settings.SANDBOX_MAX_MEMORY_MB}m",
            memswap_limit=f"{settings.SANDBOX_MAX_MEMORY_MB}m",
            cpu_period=100000,
            cpu_quota=50000,
            network_disabled=True,
            read_only=True,
            tmpfs={"/tmp": "size=10m"},
            security_opt=["no-new-privileges"],
            pids_limit=64,
            detach=True,
        )

        try:
            result = container.wait(timeout=settings.SANDBOX_TIMEOUT_SECONDS)
            exit_code = result.get("StatusCode", -1)
            logs = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            err_logs = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            return ExecutionResult(
                success=exit_code == 0,
                stdout=logs,
                stderr=err_logs,
                exit_code=exit_code,
            )
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass

    @staticmethod
    def _sanitize_python(code: str) -> str:
        dangerous_imports = [
            "os", "subprocess", "sys", "shutil", "signal",
            "socket", "http", "urllib", "requests",
            "ctypes", "multiprocessing", "threading",
            "importlib", "pickle", "eval", "exec",
            "compile", "open", "__import__",
        ]
        lines = code.split("\n")
        safe_lines = []
        for line in lines:
            stripped = line.strip()
            is_dangerous = False
            for dangerous in dangerous_imports:
                if f"import {dangerous}" in stripped or f"from {dangerous}" in stripped:
                    is_dangerous = True
                    break
            if not is_dangerous:
                safe_lines.append(line)
        return "\n".join(safe_lines)

    @staticmethod
    def _sanitize_javascript(code: str) -> str:
        dangerous_patterns = [
            "require(", "process.", "child_process",
            "fs.", "net.", "http.", "https.",
            "eval(", "Function(", "setTimeout(",
        ]
        lines = code.split("\n")
        safe_lines = []
        for line in lines:
            stripped = line.strip()
            is_dangerous = any(p in stripped for p in dangerous_patterns)
            if not is_dangerous:
                safe_lines.append(line)
        return "\n".join(safe_lines)


sandbox = CodeSandbox()
