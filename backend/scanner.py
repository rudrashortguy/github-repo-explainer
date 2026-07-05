import ast
import json
import subprocess  # nosec
from pathlib import Path
from typing import Any


class RepoScanner:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def tree(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for p in sorted(self.repo_path.rglob("*")):
            if p.is_file() and not any(
                part.startswith(".") or part == "node_modules" or part == "__pycache__"
                for part in p.relative_to(self.repo_path).parts
            ):
                rel = str(p.relative_to(self.repo_path))
                result[rel] = {"size": p.stat().st_size, "ext": p.suffix}
        return result

    def parse_python(self, path: Path) -> dict[str, Any]:
        try:
            tree = ast.parse(path.read_text())
            return {
                "functions": [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                "classes": [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)],
                "imports": [
                    (n.names[0].name if hasattr(n, "names") and n.names else getattr(n, "module", ""))
                    for n in ast.walk(tree)
                    if isinstance(n, (ast.Import, ast.ImportFrom))
                ],
            }
        except SyntaxError:
            return {"error": "parse_error"}

    def parse_js_ts(self, path: Path) -> dict[str, Any] | None:
        ext = path.suffix.lower()
        if ext not in (".js", ".jsx", ".ts", ".tsx"):
            return None
        try:
            # bandit: subprocess with list args = no shell injection
            r = subprocess.run(  # nosec
                ["npx", "--yes", "esprima", "--format", "json", str(path)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                return {"error": r.stderr.strip()}
            data = json.loads(r.stdout)
            return {
                "functions": [
                    n.get("key", {}).get("name", "")
                    for n in _walk(data)
                    if n.get("type") in ("FunctionDeclaration", "ArrowFunctionExpression")
                ],
                "classes": [
                    n.get("id", {}).get("name", "")
                    for n in _walk(data)
                    if n.get("type") == "ClassDeclaration"
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    def dep_files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        for name in ("package.json", "requirements.txt", "Cargo.toml", "Dockerfile"):
            p = self.repo_path / name
            if p.exists():
                files[name] = p.read_text(encoding="utf-8", errors="replace")[:2000]
        for p in self.repo_path.rglob("package.json"):
            if p.parent != self.repo_path:
                files[str(p.relative_to(self.repo_path))] = p.read_text(encoding="utf-8", errors="replace")[:2000]
        return files

    def main_file(self) -> str | None:
        for name in ("main.py", "index.py", "app.py", "app.js", "index.js", "main.js", "main.ts", "app.ts"):
            p = self.repo_path / name
            if p.exists():
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[:50])
            for p in self.repo_path.rglob(name):
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[:50])
        return None


def _walk(node: Any, depth: int = 0) -> Any:
    if depth > 20:
        return
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v, depth + 1)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item, depth + 1)
