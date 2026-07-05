import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import git
import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from models import ExplainRequest, RepoReport
from scanner import RepoScanner

logger = structlog.get_logger()
TEMP_ROOT = Path("./temp_clones")
TEMP_ROOT.mkdir(exist_ok=True)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Repo Explainer")
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MAX_REPO_MB = 50


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


@app.post("/explain", response_model=RepoReport)
@limiter.limit("5/minute")
async def explain(req: ExplainRequest, request: Request) -> RepoReport:
    job_id = uuid.uuid4().hex
    clone_dir = TEMP_ROOT / job_id
    client_ip = request.client.host if request.client else "unknown"
    log = logger.bind(url=req.repo_url, ip=client_ip, job_id=job_id)

    try:
        async with asyncio.timeout(60):
            await asyncio.to_thread(
                git.Repo.clone_from,
                req.repo_url, str(clone_dir),
                depth=1,
                allow_unsafe_protocols=False,
                allow_unsafe_options=False,
            )

        # ponytail: du via pathlib instead of subprocess to avoid injection surface
        total_bytes = sum(f.stat().st_size for f in clone_dir.rglob("*") if f.is_file())
        if total_bytes > MAX_REPO_MB * 1024 * 1024:
            raise HTTPException(413, f"Repo exceeds {MAX_REPO_MB}MB limit")

        scanner = RepoScanner(clone_dir)
        tree = scanner.tree()
        deps = scanner.dep_files()
        main_src = scanner.main_file()

        py_files = {k: scanner.parse_python(clone_dir / k) for k in tree if k.endswith(".py")}
        js_files = {k: scanner.parse_js_ts(clone_dir / k) for k in tree if k.endswith((".js", ".jsx", ".ts", ".tsx"))}

        prompt = _build_prompt(tree, deps, main_src, py_files, js_files)
        report = await _call_ollama(prompt)

        log.info("explain_success", size_mb=round(total_bytes / 1024 / 1024, 1))
        return report

    except asyncio.TimeoutError:
        log.warning("clone_timeout")
        raise HTTPException(504, "Cloning timed out (60s)")
    except HTTPException:
        raise
    except git.GitCommandError as e:
        log.error("git_error", detail=str(e))
        raise HTTPException(400, f"Clone failed: {e.stderr[:500] if e.stderr else str(e)[:500]}")
    except Exception as e:
        log.error("unexpected_error", detail=str(e))
        raise HTTPException(500, str(e)[:500])
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)


def _build_prompt(tree: dict[str, Any], deps: dict[str, Any], main_src: str | None, py_files: dict[str, Any], js_files: dict[str, Any]) -> str:
    return f"""You are a codebase analysis tool. Analyze this GitHub repository and return ONLY valid JSON matching this schema:
{RepoReport.model_json_schema()}

Repository tree:
{json.dumps(tree, indent=2)}

Dependency files:
{json.dumps(deps, indent=2)}

Main entry file (first 50 lines):
{main_src or 'N/A'}

Python AST summaries:
{json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "imports"} for k, v in py_files.items()}, indent=2)}

JS/TS AST summaries:
{json.dumps(js_files, indent=2)}

Respond with valid JSON only, no markdown, no explanation."""


async def _call_ollama(prompt: str) -> RepoReport:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_ollama_url()}/api/generate",
            json={"model": "gemma2:latest", "prompt": prompt, "stream": False, "format": "json"},
        )
        resp.raise_for_status()
        body = resp.json()
        raw = body.get("response", "")
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        return RepoReport.model_validate_json(raw)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # nosec - dev server
