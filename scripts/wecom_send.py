#!/usr/bin/env python3
"""Send markdown message to WeCom group bot webhook.

Usage:
  python wecom_send.py < "message.md"          # stdin
  python wecom_send.py "**bold** text"          # arg

Proxy: uses HTTPS_PROXY env, or falls back to Clash Verge 127.0.0.1:7890.
"""
import sys, os, json, urllib.request

WEBHOOK = os.environ.get(
    "WECOM_WEBHOOK",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7a8610e4-f77f-4505-b1c3-844cfca87499"
)

PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "http://127.0.0.1:7890"


def send_markdown(content: str) -> dict:
    """Send markdown_v2 message to WeCom via proxy."""
    payload = json.dumps(
        {"msgtype": "markdown_v2", "markdown_v2": {"content": content}},
        ensure_ascii=False
    ).encode("utf-8")

    proxy_handler = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    opener = urllib.request.build_opener(proxy_handler)

    req = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    resp = opener.open(req, timeout=10)
    return json.loads(resp.read().decode())


def main():
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        content = sys.stdin.read()

    if not content.strip():
        print("ERROR: empty message", file=sys.stderr)
        sys.exit(1)

    if len(content) > 4000:
        content = content[:3990] + "\n\n...截断"

    try:
        result = send_markdown(content)
        if result.get("errcode") != 0:
            print(f"WECOM ERROR: {result}", file=sys.stderr)
            sys.exit(1)
        print("OK", result.get("errmsg", ""))
    except Exception as e:
        print(f"WECOM FAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
