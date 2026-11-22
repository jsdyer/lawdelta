"""Small append-only, content-verified snapshot store. No network during build."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

AGENT = "CoolCode-{tool}/1.0 (+https://github.com/jsdyer/{tool})"

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return value

def fetch(url, tool, extra_headers=None):
    headers = {"User-Agent": AGENT.format(tool=tool), "Accept": "application/json, application/xml, text/xml, text/plain"}
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("Response too large")
        return raw, {"url": url, "retrieved_at": utcnow(), "http_status": response.status,
                     "content_type": response.headers.get("Content-Type"),
                     "last_modified": response.headers.get("Last-Modified"), "etag": response.headers.get("ETag"),
                     "sha256": digest(raw)}

def manifest(root):
    path = root / "data/manifest.json"
    if not path.exists():
        return {"schema_version": 1, "captures": []}
    value = json.loads(path.read_text())
    if value.get("schema_version") != 1 or not isinstance(value.get("captures"), list):
        raise ValueError("Invalid capture manifest")
    seen = set()
    for item in value["captures"]:
        timestamp(item["captured_at"])
        path = item["path"]
        if not re.fullmatch(r"history/[0-9TZ-]+\.json", path) or path in seen:
            raise ValueError("Unsafe or repeated capture path")
        seen.add(path)
        raw = (root / "data" / path).read_bytes()
        if digest(raw) != item["sha256"]:
            raise ValueError("Historical capture hash mismatch")
        capture = json.loads(raw)
        if capture.get("captured_at") != item["captured_at"]:
            raise ValueError("Capture date does not match manifest")
        for source in capture.get("sources", []):
            relative = source["archive_path"]
            if not re.fullmatch(r"raw/[0-9a-f]{64}\.(xml|json|txt)", relative):
                raise ValueError("Unsafe source path")
            if digest((root / "data" / relative).read_bytes()) != source["sha256"]:
                raise ValueError("Historical source hash mismatch")
    return value

def save(root, capture, raw_sources, summary):
    index = manifest(root)
    data = root / "data"
    (data / "history").mkdir(parents=True, exist_ok=True)
    (data / "raw").mkdir(exist_ok=True)
    for raw, suffix, metadata in raw_sources:
        key = f"raw/{digest(raw)}.{suffix}"
        metadata["archive_path"] = key
        dest = data / key
        if dest.exists() and dest.read_bytes() != raw:
            raise ValueError("Immutable raw collision")
        if not dest.exists():
            dest.write_bytes(raw)
    capture["sources"] = [item[2] for item in raw_sources]
    timestamp(capture["captured_at"])
    key = "history/" + capture["captured_at"].replace(":", "") + ".json"
    raw = canonical(capture)
    dest = data / key
    if dest.exists():
        if dest.read_bytes() != raw:
            raise ValueError("Immutable capture collision")
        return
    dest.write_bytes(raw)
    index["captures"].append({"captured_at": capture["captured_at"], "path": key, "sha256": digest(raw)})
    index["captures"].sort(key=lambda item: item["captured_at"])
    summary.update({"schema_version": 1, "captured_at": capture["captured_at"], "latest": key, "capture_count": len(index["captures"]), "history_url": "./manifest.json"})
    # Commit only after all data and sources have been validated by the caller.
    for name, value in [("manifest.json", index), ("index.json", summary)]:
        temp = data / (name + ".tmp")
        temp.write_bytes(canonical(value))
        temp.replace(data / name)
    manifest(root)
