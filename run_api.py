#!/usr/bin/env python3
"""
AstraGuard AI REST API Server

Run the FastAPI server for telemetry ingestion and anomaly detection.

Usage:
    python run_api.py
    python run_api.py --host 0.0.0.0 --port 8000
    python run_api.py --reload  # Development mode with auto-reload
"""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="AstraGuard AI REST API Server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )

    args = parser.parse_args()

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║          AstraGuard AI REST API Server                    ║
    ╚═══════════════════════════════════════════════════════════╝

    📡 Server starting...
    🌐 Host: {args.host}
    🔌 Port: {args.port}
    📚 Docs: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs
    🔄 Reload: {args.reload}

    Press CTRL+C to stop
    """)

    uvicorn.run(
        "api.service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info"
    )


if __name__ == "__main__":
    main()
