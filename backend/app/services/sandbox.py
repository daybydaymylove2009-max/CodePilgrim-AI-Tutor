from __future__ import annotations

import ast
import asyncio
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger

from app.core.config import settings
from app.schemas.learning import ExecutionResult


REACT_BOILERPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  .error-boundary {{ padding: 16px; color: #ef4444; background: #1a1a2e; border: 1px solid #ef4444; border-radius: 8px; margin: 8px; }}
  .error-boundary h3 {{ margin-bottom: 8px; }}
  .error-boundary pre {{ white-space: pre-wrap; font-size: 12px; opacity: 0.8; }}
</style>
<script src="/static/vendor/react.development.js"><\/script>
<script src="/static/vendor/react-dom.development.js"><\/script>
<script src="/static/vendor/babel.min.js"><\/script>
</head><body><div id="root"></div>
<script type="text/babel">
class ErrorBoundary extends React.Component {{
  constructor(props) {{ super(props); this.state = {{ hasError: false, error: null }}; }}
  static getDerivedStateFromError(error) {{ return {{ hasError: true, error }}; }}
  render() {{
    if (this.state.hasError) {{
      return (
        <div className="error-boundary">
          <h3>\u26a0\ufe0f \u8fd0\u884c\u65f6\u9519\u8bef</h3>
          <pre>{{this.state.error && this.state.error.toString()}}</pre>
        </div>
      );
    }}
    return this.props.children;
  }}
}}
try {{
  {code}
  ReactDOM.createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
}} catch(e) {{
  document.getElementById('root').innerHTML = '<div class="error-boundary"><h3>\u26a0\ufe0f \u7f16\u8bd1\u9519\u8bef</h3><pre>' + e.toString() + '</pre></div>';
}}
</script></body></html>"""

VUE_BOILERPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  .error-boundary {{ padding: 16px; color: #ef4444; background: #1a1a2e; border: 1px solid #ef4444; border-radius: 8px; margin: 8px; }}
  .error-boundary h3 {{ margin-bottom: 8px; }}
  .error-boundary pre {{ white-space: pre-wrap; font-size: 12px; opacity: 0.8; }}
</style>
<script src="/static/vendor/vue.global.js"><\/script>
</head><body><div id="app"></div>
<script>
const {{ createApp, ref, computed, watch, onMounted, onUnmounted }} = Vue;
try {{
  {code}
  if (typeof app !== 'undefined') {{
    app.mount('#app');
  }}
}} catch(e) {{
  document.getElementById('app').innerHTML = '<div class="error-boundary"><h3>\u26a0\ufe0f \u8fd0\u884c\u65f6\u9519\u8bef</h3><pre>' + e.toString() + '</pre></div>';
}}
</script></body></html>"""


class SecurityAnalyzer(ast.NodeVisitor):
    DANGEROUS_MODULES = {
        "os", "subprocess", "sys", "shutil", "signal",
        "socket", "http", "urllib", "requests",
        "ctypes", "multiprocessing", "threading",
        "importlib", "pickle",
    }
    DANGEROUS_BUILTINS = {"eval", "exec", "compile", "__import__", "open"}

    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node):
        for alias in node.names:
            root_module = alias.name.split('.')[0]
            if root_module in self.DANGEROUS_MODULES:
                self.violations.append(f"Line {node.lineno}: \u7981\u6b62\u5bfc\u5165 '{alias.name}' \u6a21\u5757")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            root_module = node.module.split('.')[0]
            if root_module in self.DANGEROUS_MODULES:
                self.violations.append(f"Line {node.lineno}: \u7981\u6b62\u4ece '{node.module}' \u5bfc\u5165")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.DANGEROUS_BUILTINS:
            self.violations.append(f"Line {node.lineno}: \u7981\u6b62\u8c03\u7528 '{node.func.id}()'")
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "__import__":
                self.violations.append(f"Line {node.lineno}: \u7981\u6b62\u8c03\u7528 '__import__()'")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__" and node.attr in self.DANGEROUS_BUILTINS:
                self.violations.append(f"Line {node.lineno}: \u7981\u6b62\u8bbf\u95ee __builtins__.{node.attr}")
        self.generic_visit(node)


def analyze_python_security(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        return analyzer.violations
    except SyntaxError as e:
        return [f"\u8bed\u6cd5\u9519\u8bef (\u884c {e.lineno}): {e.msg}"]


def analyze_javascript_security(code: str) -> list[str]:
    violations: list[str] = []
    dangerous_patterns = [
        (r'\brequire\s*\(\s*["\'](?:child_process|fs|net|http|https|os|cluster|dgram|dns|readline|tls|vm|path|crypto|stream)["\']', "\u7981\u6b62\u5bfc\u5165\u7cfb\u7edf/\u7f51\u7edc\u6a21\u5757"),
        (r'\bprocess\.', "\u7981\u6b62\u8bbf\u95ee process \u5bf9\u8c61"),
        (r'\beval\s*\(', "\u7981\u6b62\u8c03\u7528 eval()"),
        (r'\bFunction\s*\(', "\u7981\u6b62\u8c03\u7528 Function() \u6784\u9020\u5668"),
        (r'\b__dirname\b', "\u7981\u6b62\u8bbf\u95ee __dirname"),
        (r'\b__filename\b', "\u7981\u6b62\u8bbf\u95ee __filename"),
    ]
    for i, line in enumerate(code.split('\n'), 1):
        for pattern, msg in dangerous_patterns:
            if re.search(pattern, line):
                violations.append(f"Line {i}: {msg}")
                break
    return violations


@dataclass
class StructuredError:
    error_type: str
    message: str
    file_path: str | None = None
    line_number: int | None = None
    column: int | None = None
    traceback_lines: list[str] = field(default_factory=list)
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "traceback_lines": self.traceback_lines,
            "suggestion": self.suggestion,
        }


_PYTHON_ERROR_SUGGESTIONS: dict[str, str] = {
    "NameError": "\u68c0\u67e5\u53d8\u91cf\u540d\u662f\u5426\u62fc\u5199\u6b63\u786e\uff0c\u6216\u662f\u5426\u5728\u4f7f\u7528\u524d\u5df2\u5b9a\u4e49",
    "TypeError": "\u68c0\u67e5\u6570\u636e\u7c7b\u578b\u662f\u5426\u5339\u914d\uff0c\u4f8b\u5982\u662f\u5426\u5c06\u5b57\u7b26\u4e32\u4e0e\u6570\u5b57\u76f4\u63a5\u8fd0\u7b97",
    "IndexError": "\u68c0\u67e5\u7d22\u5f15\u662f\u5426\u8d85\u51fa\u5e8f\u5217\u8303\u56f4\uff0c\u8bb0\u5f97\u7d22\u5f15\u4ece 0 \u5f00\u59cb",
    "KeyError": "\u68c0\u67e5\u5b57\u5178\u7684\u952e\u662f\u5426\u5b58\u5728\uff0c\u53ef\u4f7f\u7528 dict.get() \u63d0\u4f9b\u9ed8\u8ba4\u503c",
    "ValueError": "\u68c0\u67e5\u503c\u662f\u5426\u7b26\u5408\u9884\u671f\u683c\u5f0f\uff0c\u4f8b\u5982\u5c06\u5b57\u7b26\u4e32\u8f6c\u4e3a\u6570\u5b57\u65f6\u683c\u5f0f\u662f\u5426\u6b63\u786e",
    "AttributeError": "\u68c0\u67e5\u5bf9\u8c61\u662f\u5426\u62e5\u6709\u8be5\u5c5e\u6027/\u65b9\u6cd5\uff0c\u53ef\u7528 dir() \u67e5\u770b\u53ef\u7528\u5c5e\u6027",
    "IndentationError": "\u68c0\u67e5\u7f29\u8fdb\u662f\u5426\u4e00\u81f4\uff0c\u5efa\u8bae\u7edf\u4e00\u4f7f\u7528 4 \u4e2a\u7a7a\u683c\u7f29\u8fdb",
    "SyntaxError": "\u68c0\u67e5\u8bed\u6cd5\u662f\u5426\u6b63\u786e\uff0c\u5982\u662f\u5426\u7f3a\u5c11\u5192\u53f7\u3001\u62ec\u53f7\u6216\u5f15\u53f7",
    "ZeroDivisionError": "\u5728\u9664\u6cd5\u524d\u68c0\u67e5\u9664\u6570\u662f\u5426\u4e3a 0",
    "ImportError": "\u68c0\u67e5\u6a21\u5757\u540d\u662f\u5426\u6b63\u786e\uff0c\u6216\u662f\u5426\u5df2\u5b89\u88c5\u8be5\u5305",
    "FileNotFoundError": "\u68c0\u67e5\u6587\u4ef6\u8def\u5f84\u662f\u5426\u6b63\u786e",
    "RecursionError": "\u68c0\u67e5\u9012\u5f52\u662f\u5426\u6709\u6b63\u786e\u7684\u7ec8\u6b62\u6761\u4ef6",
    "StopIteration": "\u68c0\u67e5\u8fed\u4ee3\u5668\u662f\u5426\u5df2\u7ecf\u8017\u5c3d",
    "OverflowError": "\u8ba1\u7b97\u7ed3\u679c\u8d85\u51fa\u4e86\u6570\u503c\u8303\u56f4",
    "MemoryError": "\u7a0b\u5e8f\u4f7f\u7528\u4e86\u8fc7\u591a\u5185\u5b58\uff0c\u5c1d\u8bd5\u51cf\u5c0f\u6570\u636e\u89c4\u6a21\u6216\u4f7f\u7528\u751f\u6210\u5668",
    "TimeoutError": "\u64cd\u4f5c\u8d85\u65f6\uff0c\u68c0\u67e5\u662f\u5426\u5b58\u5728\u65e0\u9650\u5faa\u73af\u6216\u7f51\u7edc\u8bf7\u6c42",
}

_JS_ERROR_SUGGESTIONS: dict[str, str] = {
    "ReferenceError": "\u68c0\u67e5\u53d8\u91cf\u540d\u662f\u5426\u62fc\u5199\u6b63\u786e\uff0c\u4ee5\u53ca\u662f\u5426\u5728\u4f7f\u7528\u524d\u5df2\u58f0\u660e",
    "TypeError": "\u68c0\u67e5\u6570\u636e\u7c7b\u578b\u662f\u5426\u5339\u914d\uff0c\u4f8b\u5982\u662f\u5426\u5bf9 null/undefined \u8c03\u7528\u65b9\u6cd5",
    "SyntaxError": "\u68c0\u67e5\u8bed\u6cd5\u662f\u5426\u6b63\u786e\uff0c\u5982\u662f\u5426\u7f3a\u5c11\u62ec\u53f7\u6216\u5f15\u53f7",
    "RangeError": "\u68c0\u67e5\u503c\u662f\u5426\u5728\u5408\u7406\u8303\u56f4\u5185",
}


def parse_python_error(stderr: str) -> StructuredError:
    lines = stderr.strip().split('\n')
    error_type = "UnknownError"
    message = stderr.strip()
    line_number = None
    column = None
    file_path = None
    traceback_lines = []

    tb_section = False
    for line in lines:
        if line.startswith("Traceback (most recent call last)"):
            tb_section = True
            traceback_lines.append(line)
            continue
        if tb_section:
            traceback_lines.append(line)

        file_match = re.match(r'\s*File "(.+?)", line (\d+)', line)
        if file_match:
            file_path = file_match.group(1)
            line_number = int(file_match.group(2))
            col_match = re.search(r'column\s+(\d+)', line)
            if col_match:
                column = int(col_match.group(1))

    error_line = lines[-1] if lines else ""
    if ':' in error_line:
        parts = error_line.split(':', 1)
        error_type = parts[0].strip()
        message = parts[1].strip()
    elif error_line:
        error_type = error_line.strip()

    suggestion = _PYTHON_ERROR_SUGGESTIONS.get(error_type)

    return StructuredError(
        error_type=error_type,
        message=message,
        file_path=file_path,
        line_number=line_number,
        column=column,
        traceback_lines=traceback_lines,
        suggestion=suggestion,
    )


def parse_javascript_error(stderr: str) -> StructuredError:
    lines = stderr.strip().split('\n')
    error_type = "UnknownError"
    message = stderr.strip()
    line_number = None
    column = None
    file_path = None
    traceback_lines = []

    for line in lines:
        match = re.match(r'(.+?):(\d+)(?::(\d+))?\s*$', line)
        if not match:
            match = re.match(r'\s*at\s+.+?\((.+?):(\d+):(\d+)\)', line)
        if match:
            file_path = match.group(1)
            line_number = int(match.group(2))
            if match.lastindex and match.lastindex >= 3:
                try:
                    column = int(match.group(3))
                except (ValueError, IndexError):
                    pass

    error_match = re.match(r'^(\w+Error):\s*(.+)', lines[0] if lines else "")
    if error_match:
        error_type = error_match.group(1)
        message = error_match.group(2)
    else:
        syntax_match = re.search(r'SyntaxError:\s*(.+)', stderr)
        if syntax_match:
            error_type = "SyntaxError"
            message = syntax_match.group(1)

    suggestion = _JS_ERROR_SUGGESTIONS.get(error_type)

    return StructuredError(
        error_type=error_type,
        message=message,
        file_path=file_path,
        line_number=line_number,
        column=column,
        traceback_lines=lines,
        suggestion=suggestion,
    )


def parse_rust_error(stderr: str) -> StructuredError:
    lines = stderr.strip().split('\n')
    error_type = "CompileError"
    message = stderr.strip()
    line_number = None
    column = None
    file_path = None
    traceback_lines = []

    error_match = re.match(r'^error\[(E\d+)\]:\s*(.+)', lines[0] if lines else "")
    if error_match:
        error_type = error_match.group(1)
        message = error_match.group(2)
    elif lines and lines[0].startswith("error: "):
        error_type = "CompileError"
        message = lines[0][7:]

    for line in lines:
        loc_match = re.match(r'\s*-->\s*(.+?):(\d+):(\d+)', line)
        if loc_match:
            file_path = loc_match.group(1)
            line_number = int(loc_match.group(2))
            column = int(loc_match.group(3))
            break

    suggestion = None
    for i, line in enumerate(lines):
        if '=' in line and 'help' in line.lower():
            suggestion = line.strip()
            break
        if line.strip().startswith("help:"):
            suggestion = line.strip()
            break

    return StructuredError(
        error_type=error_type,
        message=message,
        file_path=file_path,
        line_number=line_number,
        column=column,
        traceback_lines=lines,
        suggestion=suggestion,
    )


def _parse_error(stderr: str, language: str) -> StructuredError:
    if not stderr.strip():
        return StructuredError(error_type="UnknownError", message="")
    if language == "python":
        return parse_python_error(stderr)
    elif language == "javascript":
        return parse_javascript_error(stderr)
    elif language == "rust":
        return parse_rust_error(stderr)
    return StructuredError(error_type="UnknownError", message=stderr.strip())


PYTHON_STDLIB = {
    "abc", "argparse", "array", "ast", "asyncio", "atexit", "base64",
    "binascii", "bisect", "calendar", "cmath", "collections", "colorsys",
    "configparser", "contextlib", "copy", "csv", "dataclasses", "datetime",
    "decimal", "difflib", "enum", "fileinput", "fractions", "functools",
    "glob", "hashlib", "heapq", "html", "inspect", "io", "itertools",
    "json", "keyword", "linecache", "locale", "logging", "math",
    "mimetypes", "numbers", "operator", "pathlib", "pprint", "queue",
    "random", "re", "secrets", "statistics", "string", "struct",
    "textwrap", "time", "timeit", "traceback", "typing", "unicodedata",
    "uuid", "warnings", "weakref", "xml", "zipfile", "zlib",
}

PIP_WHITELIST: set[str] = {
    "numpy", "pandas", "matplotlib", "scipy", "sympy", "pillow",
    "requests", "beautifulsoup4", "flask", "django", "sqlalchemy",
    "pydantic", "rich", "click", "typer", "httpx", "polars",
    "seaborn", "plotly", "bokeh", "altair", "scikit-learn",
    "sklearn", "networkx", "lxml", "tqdm", "pyyaml", "toml",
    "jinja2", "markupsafe", "python-dateutil", "pytz",
    "tabulate", "colorama", "termcolor", "more-itertools",
}

NPM_WHITELIST: set[str] = {
    "lodash", "axios", "dayjs", "moment", "uuid",
    "chalk", "express", "underscore", "rxjs", "immutable",
}


def _detect_missing_python_packages(code: str) -> list[str]:
    missing: list[str] = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split('.')[0]
                    if root not in PYTHON_STDLIB and root not in SecurityAnalyzer.DANGEROUS_MODULES:
                        missing.append(root)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split('.')[0]
                    if root not in PYTHON_STDLIB and root not in SecurityAnalyzer.DANGEROUS_MODULES:
                        missing.append(root)
    except SyntaxError:
        pass
    return list(dict.fromkeys(missing))


def _detect_missing_js_packages(code: str) -> list[str]:
    missing: list[str] = []
    for match in re.finditer(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)''', code):
        pkg = match.group(1)
        if not pkg.startswith('.') and not pkg.startswith('/'):
            missing.append(pkg)
    return list(dict.fromkeys(missing))


def _install_python_packages(packages: list[str]) -> tuple[bool, str]:
    installable = [p for p in packages if p in PIP_WHITELIST]
    if not installable:
        blocked = [p for p in packages if p not in PIP_WHITELIST]
        if blocked:
            return False, f"\u4ee5\u4e0b\u5305\u4e0d\u5728\u767d\u540d\u5355\u4e2d\uff0c\u65e0\u6cd5\u81ea\u52a8\u5b89\u88c5: {', '.join(blocked)}"
        return True, ""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + installable,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            return False, f"pip install \u5931\u8d25: {result.stderr.decode('utf-8', errors='replace')}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "pip install \u8d85\u65f6"
    except Exception as e:
        return False, f"pip install \u5f02\u5e38: {e}"


def _install_js_packages(packages: list[str]) -> tuple[bool, str]:
    installable = [p for p in packages if p in NPM_WHITELIST]
    if not installable:
        blocked = [p for p in packages if p not in NPM_WHITELIST]
        if blocked:
            return False, f"\u4ee5\u4e0b\u5305\u4e0d\u5728\u767d\u540d\u5355\u4e2d\uff0c\u65e0\u6cd5\u81ea\u52a8\u5b89\u88c5: {', '.join(blocked)}"
        return True, ""
    try:
        result = subprocess.run(
            ["npm", "install", "--no-save", "--no-package-lock"] + installable,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            return False, f"npm install \u5931\u8d25: {result.stderr.decode('utf-8', errors='replace')}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "npm install \u8d85\u65f6"
    except Exception as e:
        return False, f"npm install \u5f02\u5e38: {e}"


def _detect_python_stdin_usage(code: str) -> bool:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "input":
                    return True
    except SyntaxError:
        if "input(" in code:
            return True
    return False


def _track_memory_windows(proc: subprocess.Popen) -> float:
    try:
        import psutil
        p = psutil.Process(proc.pid)
        peak = p.memory_info().rss / (1024 * 1024)
        return round(peak, 2)
    except Exception:
        return 0.0


def _track_memory_posix(rusage) -> float:
    return round(rusage.ru_maxrss / 1024, 2)


class ExecutionHistory:
    def __init__(self, max_entries: int = 50):
        self._entries: dict[str, list[dict]] = {}
        self._max = max_entries

    def add(self, user_id: str, entry: dict):
        if user_id not in self._entries:
            self._entries[user_id] = []
        self._entries[user_id].append(entry)
        if len(self._entries[user_id]) > self._max:
            self._entries[user_id] = self._entries[user_id][-self._max:]

    def get(self, user_id: str, limit: int = 20) -> list[dict]:
        entries = self._entries.get(user_id, [])
        return entries[-limit:]


class CodeSandbox:

    def __init__(self):
        self._client = None
        self._docker_available: bool | None = None
        self._history = ExecutionHistory(max_entries=50)
        self._running_processes: dict[str, subprocess.Popen] = {}

    def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        return self._history.get(user_id, limit)

    def stop_execution(self, execution_id: str) -> bool:
        proc = self._running_processes.pop(execution_id, None)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            return True
        return False

    async def execute(
        self,
        code: str,
        language: str = "python",
        stdin: str | None = None,
        user_id: str | None = None,
    ) -> ExecutionResult:
        if language == "python":
            violations = analyze_python_security(code)
            if violations:
                return ExecutionResult(
                    success=False,
                    error_type="security_violation",
                    error_message="\u4ee3\u7801\u5b89\u5168\u68c0\u67e5\u672a\u901a\u8fc7",
                    security_violations=violations,
                )
            missing = _detect_missing_python_packages(code)
            if missing:
                ok, msg = _install_python_packages(missing)
                if not ok:
                    return ExecutionResult(
                        success=False,
                        error_type="package_error",
                        error_message=msg,
                    )
        elif language == "javascript":
            violations = analyze_javascript_security(code)
            if violations:
                return ExecutionResult(
                    success=False,
                    error_type="security_violation",
                    error_message="\u4ee3\u7801\u5b89\u5168\u68c0\u67e5\u672a\u901a\u8fc7",
                    security_violations=violations,
                )
            missing = _detect_missing_js_packages(code)
            if missing:
                ok, msg = _install_js_packages(missing)
                if not ok:
                    return ExecutionResult(
                        success=False,
                        error_type="package_error",
                        error_message=msg,
                    )

        if language == "rust":
            result = await self._execute_rust(code, stdin=stdin)
        elif language == "react":
            result = self._compile_frontend(code, "react")
        elif language == "vue":
            result = self._compile_frontend(code, "vue")
        elif language in ("python", "javascript"):
            if self._check_docker():
                result = await self._execute_docker(code, language, stdin=stdin)
            else:
                result = await self._execute_local(code, language, stdin=stdin)
        else:
            result = ExecutionResult(
                success=False,
                error_type="unsupported",
                error_message=f"Unsupported language: {language}",
            )

        if not result.success and result.stderr:
            structured = _parse_error(result.stderr, language)
            result.structured_error = structured.to_dict()

        if user_id:
            self._history.add(user_id, {
                "language": language,
                "code_preview": code[:200],
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "peak_memory_mb": result.peak_memory_mb,
                "error_type": result.error_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return result

    def _check_docker(self) -> bool:
        if self._docker_available is not None:
            return self._docker_available
        try:
            import docker
            client = docker.from_env()
            client.ping()
            self._client = client
            self._docker_available = True
            logger.info("Docker sandbox available")
        except Exception as e:
            self._docker_available = False
            logger.warning(f"Docker not available ({e}), using local process fallback")
        return self._docker_available

    async def _execute_rust(self, code: str, stdin: str | None = None) -> ExecutionResult:
        rustc = shutil.which("rustc")
        if not rustc:
            return ExecutionResult(
                success=False,
                error_type="runtime_error",
                error_message="Rust \u672a\u5b89\u88c5\uff0c\u8bf7\u5b89\u88c5 rustup (https://rustup.rs)",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_rust_sync, code, rustc, stdin)

    @staticmethod
    def _run_rust_sync(code: str, rustc: str, stdin: str | None = None) -> ExecutionResult:
        start_time = time.monotonic()
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "main.rs")
            bin_path = os.path.join(tmpdir, "main")

            with open(src_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                compile_result = subprocess.run(
                    [rustc, src_path, "-o", bin_path, "-A", "warnings"],
                    capture_output=True,
                    timeout=30,
                )
                if compile_result.returncode != 0:
                    elapsed = int((time.monotonic() - start_time) * 1000)
                    stderr = compile_result.stderr.decode("utf-8", errors="replace")
                    structured = parse_rust_error(stderr)
                    return ExecutionResult(
                        success=False,
                        stderr=stderr,
                        exit_code=compile_result.returncode,
                        execution_time_ms=elapsed,
                        error_type="compile_error",
                        structured_error=structured.to_dict(),
                    )

                stdin_bytes = stdin.encode("utf-8") if stdin else None
                run_result = subprocess.run(
                    [bin_path],
                    capture_output=True,
                    timeout=settings.SANDBOX_TIMEOUT_SECONDS,
                    input=stdin_bytes,
                )
                elapsed = int((time.monotonic() - start_time) * 1000)
                stdout = run_result.stdout.decode("utf-8", errors="replace")
                stderr = run_result.stderr.decode("utf-8", errors="replace")
                peak_memory = 0.0
                if platform.system() == "Windows":
                    try:
                        import psutil
                        peak_memory = round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
                    except Exception:
                        pass
                return ExecutionResult(
                    success=run_result.returncode == 0,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=run_result.returncode or 0,
                    execution_time_ms=elapsed,
                    peak_memory_mb=peak_memory,
                )
            except subprocess.TimeoutExpired:
                elapsed = int((time.monotonic() - start_time) * 1000)
                return ExecutionResult(
                    success=False,
                    stderr=f"\u6267\u884c\u8d85\u65f6 ({settings.SANDBOX_TIMEOUT_SECONDS}\u79d2)",
                    exit_code=-1,
                    execution_time_ms=elapsed,
                    error_type="timeout",
                )
            except Exception as e:
                elapsed = int((time.monotonic() - start_time) * 1000)
                return ExecutionResult(
                    success=False,
                    error_type="execution_error",
                    error_message=str(e) or type(e).__name__,
                    execution_time_ms=elapsed,
                )

    @staticmethod
    def _compile_frontend(code: str, framework: str) -> ExecutionResult:
        start_time = time.monotonic()
        try:
            if framework == "react":
                html = REACT_BOILERPLATE.replace("{code}", code)
            elif framework == "vue":
                html = VUE_BOILERPLATE.replace("{code}", code)
            else:
                return ExecutionResult(
                    success=False,
                    error_type="unsupported",
                    error_message=f"Unsupported framework: {framework}",
                )

            elapsed = int((time.monotonic() - start_time) * 1000)
            return ExecutionResult(
                success=True,
                stdout=html,
                exit_code=0,
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                error_type="compile_error",
                error_message=str(e),
                execution_time_ms=elapsed,
            )

    async def _execute_docker(self, code: str, language: str, stdin: str | None = None) -> ExecutionResult:
        try:
            import docker
            from docker.errors import ContainerError, ImageNotFound, APIError
        except ImportError:
            return await self._execute_local(code, language, stdin=stdin)

        try:
            self._ensure_image()
        except Exception as e:
            logger.warning(f"Docker image preparation failed: {e}, falling back to local")
            return await self._execute_local(code, language, stdin=stdin)

        if language == "python":
            cmd, flag = "python3", "-c"
        else:
            cmd, flag = "node", "-e"

        loop = asyncio.get_event_loop()
        try:
            output = await loop.run_in_executor(
                None, self._run_container_sync, code, cmd, flag, stdin,
            )
            return output
        except ContainerError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            structured = _parse_error(stderr, language)
            return ExecutionResult(
                success=False,
                stderr=stderr,
                exit_code=e.exit_status,
                error_type="runtime_error",
                structured_error=structured.to_dict(),
            )
        except APIError as e:
            return ExecutionResult(
                success=False, error_type="docker_error", error_message=str(e),
            )
        except Exception as e:
            return ExecutionResult(
                success=False, error_type="unknown_error", error_message=str(e),
            )

    def _ensure_image(self):
        from docker.errors import ImageNotFound
        try:
            self._client.images.get(settings.SANDBOX_DOCKER_IMAGE)
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
            self._client.images.build(path=tmpdir, tag=settings.SANDBOX_DOCKER_IMAGE, rm=True)

    def _run_container_sync(
        self,
        code: str,
        cmd: str,
        flag: str,
        stdin: str | None = None,
    ) -> ExecutionResult:
        stdin_data = stdin.encode("utf-8") if stdin else None
        container = self._client.containers.run(
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
            stdin_open=stdin_data is not None,
            detach=True,
        )
        try:
            if stdin_data:
                socket = container.attach_socket()
                try:
                    socket._sock.send(stdin_data)
                    socket._sock.shutdown(2)
                except Exception:
                    pass

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

    async def _execute_local(
        self,
        code: str,
        language: str,
        stdin: str | None = None,
    ) -> ExecutionResult:
        if language == "python":
            cmd = [sys.executable, "-c", code]
        elif language == "javascript":
            node_path = shutil.which("node")
            if not node_path:
                return ExecutionResult(
                    success=False,
                    error_type="runtime_error",
                    error_message="Node.js \u672a\u5b89\u88c5\uff0c\u65e0\u6cd5\u6267\u884c JavaScript \u4ee3\u7801",
                )
            cmd = [node_path, "-e", code]
        else:
            return ExecutionResult(
                success=False,
                error_type="unsupported",
                error_message=f"Unsupported language: {language}",
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._run_subprocess_sync, cmd, language, stdin,
        )

    @staticmethod
    def _run_subprocess_sync(
        cmd: list[str],
        language: str,
        stdin: str | None = None,
    ) -> ExecutionResult:
        start_time = time.monotonic()
        stdin_bytes = stdin.encode("utf-8") if stdin else None
        peak_memory = 0.0

        try:
            if platform.system() == "Windows":
                try:
                    import psutil
                    proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE if stdin_bytes else subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    stdout_bytes, stderr_bytes = proc.communicate(
                        input=stdin_bytes,
                        timeout=settings.SANDBOX_TIMEOUT_SECONDS,
                    )
                    try:
                        p = psutil.Process(proc.pid)
                        peak_memory = round(p.memory_info().rss / (1024 * 1024), 2)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    elapsed = int((time.monotonic() - start_time) * 1000)
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = proc.returncode if proc.returncode is not None else -1

                    return ExecutionResult(
                        success=exit_code == 0,
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=exit_code,
                        execution_time_ms=elapsed,
                        peak_memory_mb=peak_memory,
                    )
                except ImportError:
                    pass

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=settings.SANDBOX_TIMEOUT_SECONDS,
                input=stdin_bytes,
            )
            elapsed = int((time.monotonic() - start_time) * 1000)
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            exit_code = result.returncode if result.returncode is not None else -1

            if platform.system() != "Windows":
                try:
                    import resource
                    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    peak_memory = _track_memory_posix(usage)
                except Exception:
                    pass

            return ExecutionResult(
                success=exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=elapsed,
                peak_memory_mb=peak_memory,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                stderr=f"\u6267\u884c\u8d85\u65f6 ({settings.SANDBOX_TIMEOUT_SECONDS}\u79d2)",
                exit_code=-1,
                execution_time_ms=elapsed,
                error_type="timeout",
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start_time) * 1000)
            logger.error(f"Local execution error: type={type(e).__name__}, msg={e!r}, elapsed={elapsed}ms")
            return ExecutionResult(
                success=False,
                error_type="execution_error",
                error_message=str(e) or type(e).__name__,
                execution_time_ms=elapsed,
            )


sandbox = CodeSandbox()
