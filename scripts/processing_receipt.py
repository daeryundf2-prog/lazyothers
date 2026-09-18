from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


VERSION = "1.0"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def hash_file(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Source is not a regular file")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Source is not a regular file")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        current = path.stat()
    def identity(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise ValueError("Source changed while hashing")
    return digest.hexdigest()


def validate_receipt(receipt):
    errors = []
    if not isinstance(receipt, dict):
        return ["processing_receipt must be an object"]
    required = {"schema_version", "case_id", "evidence_id", "status", "source", "artifacts", "tool", "parameters", "started_at", "finished_at", "exit_code", "warnings", "limitations", "review"}
    errors.extend(f"Missing {key}" for key in sorted(required - receipt.keys()))
    if receipt.get("schema_version") != VERSION:
        errors.append("Unsupported schema_version")
    if receipt.get("case_id") is not None and not isinstance(receipt["case_id"], str):
        errors.append("Invalid case_id")
    if not isinstance(receipt.get("evidence_id"), str) or not receipt["evidence_id"].strip():
        errors.append("Invalid evidence_id")
    if receipt.get("status") not in ("complete", "partial", "failed", "not_measured"):
        errors.append("Invalid status")
    code = receipt.get("exit_code")
    if code is not None and type(code) is not int:
        errors.append("Invalid exit_code")
    for key in ("warnings", "limitations"):
        value = receipt.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"Invalid {key}")
    if not isinstance(receipt.get("parameters"), dict):
        errors.append("Invalid parameters")
    tool = receipt.get("tool")
    if not isinstance(tool, dict) or not all(isinstance(tool.get(k), str) and tool[k].strip() for k in ("name", "version")):
        errors.append("Invalid tool")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("Invalid artifacts")
        artifacts = []
    for key, value, nullable in [("source", receipt.get("source"), True)] + [("artifact", a, False) for a in artifacts]:
        if not isinstance(value, dict) or not isinstance(value.get("path"), str) or not value["path"]:
            errors.append(f"Invalid {key} path")
            continue
        digest = value.get("sha256")
        if "sha256" not in value or not (nullable and digest is None or isinstance(digest, str) and re.fullmatch(r"[a-fA-F0-9]{64}", digest)):
            errors.append(f"Invalid {key} sha256")
    dates = {}
    review = receipt.get("review")
    if not isinstance(review, dict):
        errors.append("Invalid review")
        review = {}
    if review.get("status") not in ("pending", "approved"):
        errors.append("Invalid review status")
    for key in ("reviewer", "reviewed_at"):
        if key not in review or review[key] is not None and not isinstance(review[key], str):
            errors.append(f"Invalid review {key}")
    if review.get("status") == "approved" and (not review.get("reviewer") or not review.get("reviewed_at")):
        errors.append("Approval requires reviewer and reviewed_at")
    if review.get("status") == "pending" and (review.get("reviewer") is not None or review.get("reviewed_at") is not None):
        errors.append("Pending review must have null reviewer and reviewed_at")
    timestamps_nullable = receipt.get("status") == "not_measured"
    for key, value in [("started_at", receipt.get("started_at")), ("finished_at", receipt.get("finished_at")), ("reviewed_at", review.get("reviewed_at"))]:
        if value is None:
            if key == "reviewed_at" or timestamps_nullable:
                continue
            errors.append(f"Invalid UTC {key}")
            continue
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if date.utcoffset() is None or date.utcoffset().total_seconds() != 0:
                raise ValueError
            dates[key] = date
        except (AttributeError, TypeError, ValueError):
            errors.append(f"Invalid UTC {key}")
    if dates.get("started_at") and dates.get("finished_at") and dates["started_at"] > dates["finished_at"]:
        errors.append("finished_at precedes started_at")
    if dates.get("reviewed_at") and dates.get("finished_at") and dates["reviewed_at"] < dates["finished_at"]:
        errors.append("Review precedes completion")
    if receipt.get("status") == "complete" and (code != 0 or not isinstance(receipt.get("source"), dict) or not receipt["source"].get("sha256")):
        errors.append("Complete receipt requires measured source and zero exit_code")
    return errors


def verify_receipt(receipt, base_dir=""):
    errors = validate_receipt(receipt)
    if errors:
        return errors
    for entry in [receipt["source"], *receipt["artifacts"]]:
        path = Path(entry["path"])
        if not path.is_absolute():
            path = Path(base_dir) / path
        try:
            actual = hash_file(path)
            if not entry["sha256"]:
                errors.append(f"Unmeasured file: {entry['path']}")
            elif actual != entry["sha256"].lower():
                errors.append(f"Changed file: {entry['path']}")
        except (OSError, ValueError):
            errors.append(f"Missing, unreadable or changing file: {entry['path']}")
    if receipt["status"] != "complete":
        errors.append("Processing not complete")
    return errors


def make_receipt(path, tool, case_id=None, evidence_id=None, parameters=None):
    started = utc_now()
    warnings = []
    try:
        digest = hash_file(path)
    except (OSError, ValueError):
        digest = None
        warnings.append("Source missing, unreadable or changing")
    return {
        "schema_version": VERSION, "case_id": case_id,
        "evidence_id": evidence_id or str(uuid4()),
        "status": "complete" if digest else "not_measured",
        "source": {"path": str(Path(path).absolute()), "sha256": digest},
        "artifacts": [], "tool": {"name": tool, "version": VERSION},
        "parameters": parameters or {}, "started_at": started, "finished_at": utc_now(),
        "exit_code": 0 if digest else None, "warnings": warnings,
        "limitations": ["Local file measurement only; not a signature, trusted timestamp or chain-of-custody proof."],
        "review": {"status": "pending", "reviewer": None, "reviewed_at": None},
    }


def write_verified(path, content, protected=()):
    path = Path(path).absolute()
    if any(path.resolve() == Path(p).resolve() or (path.exists() and Path(p).exists() and os.path.samefile(path, p)) for p in protected if p):
        raise ValueError("Output would overwrite an input")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        expected = hashlib.sha256(data).hexdigest()
        if hash_file(temporary) != expected:
            raise ValueError("Output verification failed")
        os.replace(temporary, path)
        if hash_file(path) != expected:
            raise ValueError("Final output verification failed")
        return expected
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def approve_receipt(receipt, reviewer, base_dir=""):
    errors = verify_receipt(receipt, base_dir)
    if not isinstance(receipt, dict) or not receipt.get("artifacts"):
        errors.append("Final output must be measured before approval")
    if not isinstance(reviewer, str) or not reviewer.strip():
        errors.append("Explicit reviewer required")
    if errors:
        raise ValueError("; ".join(errors))
    result = copy.deepcopy(receipt)
    result["review"] = {"status": "approved", "reviewer": reviewer, "reviewed_at": utc_now()}
    return result
