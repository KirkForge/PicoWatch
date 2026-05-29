"""PicoWatch HTTP server — FastAPI daemon for L5/L6/L7.

Provides POST endpoints for prompt scanning and output validation,
plus GET endpoints for health, metrics, and rules listing.

Architecture (ADR-007):
  - Main port (8766): API endpoints (scan, validate)
  - Admin port (9091): Health, metrics, rules (read-only)

Auth: API key via X-API-Key header or Bearer token on write endpoints.
Rate limiting: Per-IP sliding window (ADR-008).
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from picowatch import __version__
from picowatch.config import PicoWatchConfig
from picowatch.health import health_check
from picowatch.output_guard import OutputGuard
from picowatch.prompt_guard import PromptGuard
from picowatch.ratelimit import RateLimiter
from picowatch.telemetry import TelemetrySink
from picowatch.types import PromptScanResult

# ─── Request/Response Models ──────────────────────────────────────────────


class PromptScanRequest(BaseModel):
    """Request body for POST /v1/scan/prompt."""

    text: str = Field(..., min_length=1, description="Prompt text to scan")
    context: dict[str, Any] | None = Field(default=None, description="Optional context (user_id, model, etc.)")
    request_id: str | None = Field(default=None, description="Optional request ID for telemetry correlation")


class OutputScanRequest(BaseModel):
    """Request body for POST /v1/scan/output."""

    model_config = {"populate_by_name": True}

    output: str = Field(..., min_length=1, description="LLM output text to validate")
    json_schema: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        description="Optional JSON Schema for structural validation",
    )
    prompt_result: dict[str, Any] | None = Field(default=None, description="Optional L5 scan result for feedback loop")
    request_id: str | None = Field(default=None, description="Optional request ID for telemetry correlation")


# ─── App Factory ──────────────────────────────────────────────────────────


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def create_app(config: PicoWatchConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Returns the app instance. Call uvicorn separately to run.
    """
    config = config or PicoWatchConfig.from_env()

    # Initialize guards, telemetry, and rate limiter
    prompt_guard = PromptGuard(config=config)
    output_guard = OutputGuard(config=config)
    sink = TelemetrySink()
    limiter = RateLimiter(max_requests=config.rate_limit, window_seconds=config.rate_limit_window)

    # API key for write endpoints
    api_key = config.api_key or ""

    app = FastAPI(
        title="PicoWatch",
        version=__version__,
        description="LLM defender with telemetry — prompt injection detection, output validation, and observability",
    )

    # ─── Rate limiting middleware ────────────────────────────────────────

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Any) -> Any:
        """Per-IP rate limiting on POST endpoints (ADR-008)."""
        if request.method == "POST":
            client_ip = _get_client_ip(request)
            if not limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(config.rate_limit_window)},
                )
        return await call_next(request)

    # ─── Auth dependency ────────────────────────────────────────────────

    async def verify_api_key(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
        authorization: str | None = Header(None),
    ) -> None:
        """Verify API key for write endpoints.

        If no PICOWATCH_API_KEY is configured, all requests are allowed.
        If PICOWATCH_API_KEY is set, require X-API-Key or Bearer token.
        """
        if not api_key:
            return  # No auth required

        provided_key = ""
        if x_api_key:
            provided_key = x_api_key
        elif authorization and authorization.lower().startswith("bearer "):
            provided_key = authorization[7:].strip()

        if not provided_key or not secrets.compare_digest(provided_key, api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # ─── GET endpoints (unauthenticated, admin port eligible) ───────────

    @app.get("/v1/health")
    async def get_health() -> dict[str, Any]:
        """Health check endpoint."""
        h = health_check(
            rules_loaded=len(prompt_guard.rules),
            corpus_hash=prompt_guard.corpus_hash,
            corpus_version=prompt_guard.corpus_version,
        )
        return {
            "healthy": h.healthy,
            "version": h.version,
            "rules_loaded": h.rules_loaded,
            "corpus_hash": h.corpus_hash,
            "corpus_version": h.corpus_version,
            "uptime_seconds": h.uptime_seconds,
        }

    @app.get("/metrics")
    async def get_metrics() -> PlainTextResponse:
        """Prometheus metrics endpoint."""
        return PlainTextResponse(
            content=sink.render_prometheus(),
            media_type="text/plain",
        )

    @app.get("/v1/rules")
    async def get_rules() -> list[dict[str, Any]]:
        """List all active defense rules."""
        return [
            {
                "id": r.id,
                "category": r.category,
                "weight": r.weight,
                "description": r.description,
            }
            for r in prompt_guard.rules
        ]

    @app.get("/v1/rules/{rule_id}")
    async def get_rule(rule_id: str) -> dict[str, Any]:
        """Get detail for a specific rule."""
        for r in prompt_guard.rules:
            if r.id == rule_id:
                return {
                    "id": r.id,
                    "category": r.category,
                    "weight": r.weight,
                    "pattern": r.pattern,
                    "description": r.description,
                    "normalization": r.normalization,
                }
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    # ─── POST endpoints (authenticated, rate limited) ────────────────────

    @app.post("/v1/scan/prompt")
    async def scan_prompt(
        body: PromptScanRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict[str, Any]:
        """Scan a prompt for injection patterns."""
        text = body.text

        # Enforce size limit
        if len(text) > config.max_prompt_size:
            return JSONResponse(
                status_code=413,
                content={
                    "blocked": True,
                    "score": 1.0,
                    "verdict": "block",
                    "rules_matched": ["input_oversized"],
                    "corpus_hash": prompt_guard.corpus_hash,
                    "corpus_version": config.corpus_version,
                    "duration_ms": 0.0,
                    "error": f"Input exceeds maximum size ({config.max_prompt_size} bytes)",
                },
            )

        result = prompt_guard.check(text, context=body.context)

        # Record telemetry
        sink.record_prompt_scan(result, request_id=body.request_id)

        response: dict[str, Any] = {
            "blocked": result.blocked,
            "score": result.score,
            "verdict": result.verdict.value,
            "rules_matched": result.rules_matched,
            "corpus_hash": result.corpus_hash,
            "corpus_version": result.corpus_version,
            "duration_ms": result.duration_ms,
        }

        if result.normalized_input:
            response["normalized_input"] = result.normalized_input
        if result.details:
            response["details"] = result.details
        if body.request_id:
            response["request_id"] = body.request_id

        return response

    @app.post("/v1/scan/output")
    async def scan_output(
        body: OutputScanRequest,
        _auth: None = Depends(verify_api_key),
    ) -> dict[str, Any]:
        """Validate an LLM output against a schema and content policy."""
        # Reconstruct PromptScanResult if provided (feedback loop)
        prompt_result = None
        if body.prompt_result and isinstance(body.prompt_result, dict):
            pr = body.prompt_result
            prompt_result = PromptScanResult(
                blocked=pr.get("blocked", False),
                score=pr.get("score", 0.0),
                rules_matched=pr.get("rules_matched", []),
                corpus_hash=pr.get("corpus_hash", ""),
                corpus_version=pr.get("corpus_version", ""),
                duration_ms=pr.get("duration_ms", 0.0),
            )

        result = output_guard.validate(body.output, schema=body.json_schema, prompt_result=prompt_result)

        # Record telemetry
        sink.record_validation(result, request_id=body.request_id)

        response: dict[str, Any] = {
            "valid": result.valid,
            "score": result.score,
            "verdict": result.verdict.value,
            "violations": result.violations,
            "corpus_hash": result.corpus_hash,
            "corpus_version": result.corpus_version,
            "duration_ms": result.duration_ms,
        }

        if result.redacted:
            response["redacted"] = result.redacted
        if result.details:
            response["details"] = result.details
        if body.request_id:
            response["request_id"] = body.request_id

        return response

    return app


def create_admin_app(config: PicoWatchConfig | None = None) -> FastAPI:
    """Create a read-only admin app for the admin port (ADR-007).

    Exposes health, metrics, and rules on a separate port (default 9091).
    No auth required. No POST endpoints.
    """
    config = config or PicoWatchConfig.from_env()
    prompt_guard = PromptGuard(config=config)
    sink = TelemetrySink()

    app = FastAPI(
        title="PicoWatch Admin",
        version=__version__,
        description="Read-only admin endpoints for health, metrics, and rules",
    )

    @app.get("/v1/health")
    async def admin_health() -> dict[str, Any]:
        """Health check (admin)."""
        h = health_check(
            rules_loaded=len(prompt_guard.rules),
            corpus_hash=prompt_guard.corpus_hash,
            corpus_version=prompt_guard.corpus_version,
        )
        return {
            "healthy": h.healthy,
            "version": h.version,
            "rules_loaded": h.rules_loaded,
            "corpus_hash": h.corpus_hash,
            "corpus_version": h.corpus_version,
            "uptime_seconds": h.uptime_seconds,
        }

    @app.get("/metrics")
    async def admin_metrics() -> PlainTextResponse:
        """Prometheus metrics (admin)."""
        return PlainTextResponse(
            content=sink.render_prometheus(),
            media_type="text/plain",
        )

    @app.get("/v1/rules")
    async def admin_rules() -> list[dict[str, Any]]:
        """List active rules (admin)."""
        return [
            {"id": r.id, "category": r.category, "weight": r.weight, "description": r.description}
            for r in prompt_guard.rules
        ]

    @app.get("/v1/rules/{rule_id}")
    async def admin_rule(rule_id: str) -> dict[str, Any]:
        """Get rule detail (admin)."""
        for r in prompt_guard.rules:
            if r.id == rule_id:
                return {
                    "id": r.id,
                    "category": r.category,
                    "weight": r.weight,
                    "pattern": r.pattern,
                    "description": r.description,
                    "normalization": r.normalization,
                }
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    return app


def run_server(config: PicoWatchConfig | None = None, host: str = "0.0.0.0", port: int = 8766) -> None:
    """Run the PicoWatch HTTP server with admin port (ADR-007).

    Main port serves API endpoints. Admin port serves health/metrics/rules.
    """
    import uvicorn

    config = config or PicoWatchConfig.from_env()
    app = create_app(config)

    # Log admin port availability
    print(f"PicoWatch admin endpoints on port {config.admin_port}", file=__import__("sys").stderr)

    uvicorn.run(app, host=host, port=port, log_level="info")
