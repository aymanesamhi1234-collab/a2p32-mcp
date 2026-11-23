#!/usr/bin/env python3
"""
MCP stdio bridge for A2P-32 Guard.

Speaks MCP over stdin/stdout and forwards every request to the remote MCP
endpoint over HTTP. The engine runs behind that endpoint; this package only
implements the client side of the protocol.

    A2P_MCP_URL=https://<host>/mcp python3 bridge.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("A2P_MCP_URL", "https://zealous-unburned-tameness.ngrok-free.dev/mcp")
TIMEOUT = float(os.environ.get("A2P_TIMEOUT", "60"))
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def rpc(msg: dict) -> dict:
    datos = json.dumps(msg).encode()
    req = urllib.request.Request(URL, data=datos, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            crudo = r.read()
            return json.loads(crudo) if crudo else {}
    except urllib.error.HTTPError as exc:
        return {"jsonrpc": "2.0", "id": msg.get("id"),
                "error": {"code": -32603, "message": f"HTTP {exc.code}"}}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": msg.get("id"),
                "error": {"code": -32603,
                          "message": f"{type(exc).__name__}: {exc}"}}


def main() -> int:
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            msg = json.loads(linea)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32700, "message": "parse error"}}),
                  flush=True)
            continue
        if "id" not in msg:
            rpc(msg)          # notificacion: se reenvia sin respuesta
            continue
        print(json.dumps(rpc(msg), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
