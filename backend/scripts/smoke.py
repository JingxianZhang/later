#!/usr/bin/env python3
"""
Basic end-to-end smoke:
1) POST /v1/ingest with a name (or url)
2) Poll GET /v1/tools/{id} until one_pager exists or timeout
3) POST /v1/chat with a simple question

Usage:
  API_URL=http://127.0.0.1:8000 python backend/scripts/smoke.py "OpenAI"
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error


def http_request(method: str, url: str, data: dict | None = None, headers: dict | None = None, timeout: int = 30):
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def main():
    base = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/") + "/v1"
    if len(sys.argv) < 2:
        print("Usage: API_URL=http://127.0.0.1:8000 python backend/scripts/smoke.py \"OpenAI\"")
        sys.exit(1)
    target = sys.argv[1]
    payload = {"name": target} if not target.startswith("http") else {"url": target}

    print(f"[1/3] Ingesting: {payload}")
    res = http_request("POST", f"{base}/ingest", payload)
    tool_id = res["tool_id"]
    print(f"  → tool_id: {tool_id}, status: {res['status']}")

    print("[2/3] Polling for one_pager…")
    t0 = time.time()
    info = None
    while time.time() - t0 < 60:
        info = http_request("GET", f"{base}/tools/{tool_id}")
        if info and isinstance(info.get("one_pager"), dict) and info["one_pager"].get("overview"):
            break
        time.sleep(2)
    if not info or not info.get("one_pager") or not info["one_pager"].get("overview"):
        print("  ! one_pager not ready within 60s")
        sys.exit(2)
    print(f"  → one_pager overview: {info['one_pager'].get('overview','')[:120]}…")

    print("[3/3] Chatting…")
    chat = http_request("POST", f"{base}/chat", {"tool_id": tool_id, "question": "What is this tool about?"})
    answer = chat.get("answer", "")
    cits = chat.get("citations", [])
    print(f"  → answer: {answer[:160]}…")
    print(f"  → citations: {len(cits)}")
    print("OK")


if __name__ == "__main__":
    main()



