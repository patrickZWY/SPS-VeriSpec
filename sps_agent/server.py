from __future__ import annotations

import argparse
from typing import Any

from .cases import (
    PUBLIC_DIR,
    CaseNotFound,
    LiveRunRejected,
    artifact_text,
    case_detail,
    list_cases,
    run_live_case,
)

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_local_request(client_host: str, host_header: str | None) -> bool:
    raw_host = (host_header or "").strip().lower()
    if raw_host.startswith("[") and "]" in raw_host:
        request_host = raw_host[1 : raw_host.index("]")]
    else:
        request_host = raw_host.split(":", 1)[0]
    return client_host in LOCAL_HOSTS and request_host in LOCAL_HOSTS


def create_app() -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import FileResponse, PlainTextResponse
        from fastapi.staticfiles import StaticFiles
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI demo dependencies are not installed. Install them with "
            "`python3 -m pip install -r requirements-demo.txt`."
        ) from exc

    app = FastAPI(title="SPS-VeriSpec Agent Workbench", version="0.1.0")
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "index.html")

    @app.head("/")
    def index_head() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "index.html")

    @app.get("/pipeline")
    def pipeline() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "pipeline.html")

    @app.head("/pipeline")
    def pipeline_head() -> FileResponse:
        return FileResponse(PUBLIC_DIR / "pipeline.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        cases = list_cases()
        return {
            "status": "ok",
            "service": "SPS-VeriSpec Agent Workbench",
            "mode": "replay-default/live-allowlisted",
            "cases": len(cases),
            "live_targets": [case["id"] for case in cases if case["live_enabled"]],
        }

    @app.get("/api/cases")
    def cases() -> list[dict[str, Any]]:
        return list_cases()

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: str) -> dict[str, Any]:
        try:
            return case_detail(case_id)
        except CaseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/cases/{case_id}/artifacts/{artifact_id}")
    def get_artifact(case_id: str, artifact_id: str) -> PlainTextResponse:
        try:
            path, text = artifact_text(case_id, artifact_id)
        except CaseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return PlainTextResponse(
            text,
            headers={
                "x-sps-artifact-path": path,
                "cache-control": "no-store",
            },
        )

    @app.post("/api/run")
    async def run_case(request: Request) -> dict[str, Any]:
        client_host = request.client.host if request.client else ""
        if not is_local_request(client_host, request.headers.get("host")):
            raise HTTPException(status_code=403, detail="live runs are local-only")
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=422, detail="JSON body with case_id is required") from exc
        case_id = payload.get("case_id")
        if not isinstance(case_id, str):
            raise HTTPException(status_code=422, detail="case_id is required")
        timeout = int(payload.get("timeout_seconds", 120))
        timeout = max(1, min(timeout, 600))
        try:
            return run_live_case(case_id, timeout_seconds=timeout)
        except LiveRunRejected as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local SPS-VeriSpec Agent Workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Uvicorn is not installed. Install demo dependencies with "
            "`python3 -m pip install -r requirements-demo.txt`."
        ) from exc

    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
