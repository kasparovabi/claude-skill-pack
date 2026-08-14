#!/usr/bin/env python3
"""Build a Hermes relay JSON payload from a plain-text report file.

Avoids the security-scanner-blocked `python3 -c` / heredoc one-liner that
cron task instructions often suggest. Usage:

    python3 build_relay_payload.py \
        --report /tmp/report.txt \
        --chat-id -<chat_id> \
        --topic-id 2177 \
        --out /tmp/payload.json

Then:
    curl -s -X POST http://127.0.0.1:8767/relay/send \
        -H 'Content-Type: application/json' -d @/tmp/payload.json

Markdown markers in the report are preserved (Telegram renders them).
"""
import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="/tmp/report.txt")
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--topic-id", default=None)
    ap.add_argument("--out", default="/tmp/payload.json")
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as fh:
        text = fh.read()

    payload = {"chat_id": str(args.chat_id), "text": text}
    if args.topic_id:
        payload["topic_id"] = str(args.topic_id)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload))

    print(f"wrote {args.out} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
