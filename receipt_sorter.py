#!/usr/bin/env python3
"""Sort receipts and invoices locally with an open-weight model served by Ollama.

Nothing leaves the machine: files are read from disk, sent to localhost:11434,
and copied into sorted/<category>/ with a normalized name plus a summary.csv.
"""
import argparse
import base64
import csv
import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_EXTS = {".txt", ".pdf"}
CATEGORIES = ["software", "travel", "meals", "office", "equipment", "services", "utilities", "other"]
FIELDS = ["file", "doc_type", "vendor", "date", "total", "currency", "category", "new_path"]

PROMPT = f"""You extract data from a receipt or invoice. Reply with JSON only, with keys:
"doc_type": "receipt" or "invoice",
"vendor": string,
"date": "YYYY-MM-DD" or "",
"total": number (grand total, no currency symbol),
"currency": 3-letter code, e.g. "USD",
"category": one of {CATEGORIES}.
Use "" or 0 when unknown. Do not guess."""


def ask_model(host, model, prompt, image=None, text=None):
    content = prompt if text is None else f"{prompt}\n\nDOCUMENT TEXT:\n{text[:8000]}"
    msg = {"role": "user", "content": content}
    if image is not None:
        msg["images"] = [base64.b64encode(image).decode()]
    body = json.dumps({"model": model, "messages": [msg], "stream": False,
                       "format": "json", "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{host}/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["message"]["content"]


def read_text(path):
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("PDF support needs: pip install pypdf")
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    return path.read_text(errors="replace")


def parse_reply(raw):
    """Parse and sanitize the model's JSON reply; never trust its shape."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
    if not isinstance(data, dict):
        data = {}
    try:
        total = round(float(str(data.get("total", 0)).replace(",", "")), 2)
    except ValueError:
        total = 0.0
    date = str(data.get("date", ""))
    category = str(data.get("category", "other")).lower()
    return {
        "doc_type": "invoice" if data.get("doc_type") == "invoice" else "receipt",
        "vendor": str(data.get("vendor", "")).strip(),
        "date": date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else "",
        "total": total,
        "currency": str(data.get("currency", "")).upper()[:3],
        "category": category if category in CATEGORIES else "other",
    }


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "unknown"


def new_name(info, ext):
    return f"{info['date'] or 'undated'}_{slug(info['vendor'])}_{info['total']:.2f}{ext}"


def unique(path):
    n, p = 1, path
    while p.exists():
        n += 1
        p = path.with_name(f"{path.stem}-{n}{path.suffix}")
    return p


def process(path, host, model):
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        raw = ask_model(host, model, PROMPT, image=path.read_bytes())
    else:
        raw = ask_model(host, model, PROMPT, text=read_text(path))
    return parse_reply(raw)


def main(argv=None, ask=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inbox", type=Path, help="folder of receipts/invoices")
    ap.add_argument("-o", "--out", type=Path, default=Path("sorted"))
    ap.add_argument("-m", "--model", default="gemma3:4b", help="any Ollama vision model")
    ap.add_argument("--host", default="http://localhost:11434")
    args = ap.parse_args(argv)

    files = sorted(p for p in args.inbox.iterdir() if p.suffix.lower() in IMAGE_EXTS | TEXT_EXTS)
    args.out.mkdir(parents=True, exist_ok=True)
    rows, failed = [], 0
    for f in files:
        try:
            info = process(f, args.host, args.model)
        except Exception as e:  # keep going; one bad file shouldn't stop the batch
            print(f"FAILED {f.name}: {e}", file=sys.stderr)
            failed += 1
            continue
        dest_dir = args.out / info["category"]
        dest_dir.mkdir(exist_ok=True)
        dest = unique(dest_dir / new_name(info, f.suffix.lower()))
        shutil.copy2(f, dest)  # originals are never modified
        rows.append({"file": f.name, **info, "new_path": str(dest)})
        print(f"{f.name} -> {dest}")
    with open(args.out / "summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} sorted, {failed} failed. Summary: {args.out / 'summary.csv'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
