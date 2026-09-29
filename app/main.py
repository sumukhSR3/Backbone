"""
Main FastAPI Application Entrypoint.
Exposes REST endpoints for Ingestion, FHIR R4, Principal Diagnosis Review, Health Check, and System Metrics.
"""

import os
import json
from typing import Dict, Any, Optional
from app.database import db
from app.api.ingestion import handle_ingestion
from app.api.fhir import get_fhir_resource, search_fhir_resources
from app.api.review import handle_review
from app.api.metrics import get_metrics

# Try importing FastAPI
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="Clinical Data & Principal Diagnosis Review System",
        version="1.0.0",
        description="End-to-end FHIR R4 Ingestion and ICD-10-CM Principal Diagnosis Review Service"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup_db():
        db.init_db()

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health_check():
        return {"status": "ok", "service": "Clinical Data & Principal Diagnosis Review System"}

    @app.get("/", response_class=HTMLResponse)
    def read_root():
        template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<h1>Clinical Data & Principal Diagnosis Review System</h1>"

    @app.post("/api/v1/ingest")
    async def api_ingest(request: Request):
        try:
            data = await request.json()
            return handle_ingestion(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ingestion Error: {str(e)}")

    @app.get("/fhir/{resource_type}/{resource_id}")
    def api_get_fhir(resource_type: str, resource_id: str):
        res = get_fhir_resource(resource_type, resource_id)
        if not res:
            raise HTTPException(status_code=404, detail=f"{resource_type}/{resource_id} not found")
        return res

    @app.get("/fhir/{resource_type}")
    def api_search_fhir(resource_type: str, encounter: Optional[str] = None, patient: Optional[str] = None):
        return search_fhir_resources(resource_type, encounter, patient)

    @app.post("/api/v1/review/principal-diagnosis")
    async def api_review(request: Request):
        try:
            data = await request.json()
            return handle_review(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Review Error: {str(e)}")

    @app.get("/api/v1/metrics")
    def api_metrics():
        return get_metrics()

else:
    app = None
