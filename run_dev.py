"""
One-click Local Development Runner.
Detects if FastAPI/Uvicorn is available; if so, launches Uvicorn.
Otherwise, launches the built-in HTTP server using Python standard library.
"""

import sys
import os

sys.path.insert(0, ".")

from app.config import HOST, PORT

def main():
    try:
        import uvicorn
        from app.main import app
        print("🚀 Starting FastAPI application with Uvicorn...")
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
    except (ImportError, ModuleNotFoundError):
        print("ℹ️ FastAPI/Uvicorn not found in environment. Launching built-in HTTP server...")
        from app.server import run_server
        run_server(HOST, PORT)

if __name__ == "__main__":
    main()
