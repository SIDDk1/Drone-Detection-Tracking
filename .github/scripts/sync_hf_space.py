"""
Upload only the files needed for a Hugging Face Docker Space.

Secrets (Repository → Settings → Secrets and variables → Actions):

  Option A — one secret (recommended):
    HF_TOKEN           — write token
    HF_SPACE_REPO_ID   — exactly "username/space-name" (e.g. SIDDk1/Drone-Detection-Tracking)

  Option B — two secrets:
    HF_TOKEN, HF_USERNAME, SPACE_NAME (SPACE_NAME must be the slug only, no slash)

Paste values without line breaks. If you copy from a URL, use only the two path segments.
"""
from __future__ import annotations

import os
import re
import sys
import traceback

ALLOW_PATTERNS = [
    "Dockerfile",
    "README.md",
    "app.py",
    "packages.txt",
    "backend/**",
    "frontend/**",
    "*.mp4",
    "**/*.mp4",
]

# HF namespace and repo name rules (simplified)
_PART = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]{0,94}[a-zA-Z0-9])?$|^[a-zA-Z0-9]$")


def _clean(s: str) -> str:
    """Strip whitespace, BOM, and line breaks often pasted into GitHub Secrets by mistake."""
    if not s:
        return ""
    s = s.strip().strip("\ufeff")
    # Remove all ASCII control chars (newlines, etc.)
    s = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)
    return s.strip()


def _normalize_hf_username(raw: str) -> str:
    s = _clean(raw)
    for prefix in (
        "https://huggingface.co/",
        "http://huggingface.co/",
        "https://hf.co/",
        "http://hf.co/",
    ):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix) :].strip("/").split("/")[0]
            break
    return s


def _parse_repo_id() -> tuple[str | None, str | None]:
    """
    Returns (repo_id, error_message). repo_id is 'user/space' or None.
    """
    token = _clean(os.environ.get("HF_TOKEN", ""))

    combined = _clean(
        os.environ.get("HF_SPACE_REPO_ID", "")
        or os.environ.get("HF_REPO_ID", "")
    )
    user = _normalize_hf_username(os.environ.get("HF_USERNAME", ""))
    space = _clean(os.environ.get("SPACE_NAME", ""))

    if not token:
        return None, "HF_TOKEN is missing or empty."

    if combined:
        if combined.count("/") != 1:
            return None, (
                "HF_SPACE_REPO_ID must be exactly two parts: username/space-name "
                f"(one slash). Got {combined.count('/')!r} slashes after cleaning."
            )
        a, b = combined.split("/", 1)
        a, b = _clean(a), _clean(b)
        if not a or not b:
            return None, "HF_SPACE_REPO_ID is invalid after removing hidden characters (empty part)."
        repo_id = f"{a}/{b}"
    else:
        if not user or not space:
            return None, (
                "Set either HF_SPACE_REPO_ID (e.g. SIDDk1/Drone-Detection-Tracking) "
                "or both HF_USERNAME and SPACE_NAME. "
                "Do not put line breaks in secret values."
            )
        if "/" in space:
            return None, (
                "SPACE_NAME must not contain '/'. Use HF_SPACE_REPO_ID=user/space "
                "or set SPACE_NAME to the Space slug only."
            )
        repo_id = f"{user}/{space}"

    ns, name = repo_id.split("/", 1)
    if not _PART.match(ns) or not _PART.match(name):
        return None, (
            "Repo id uses invalid characters or length. "
            "Use only letters, digits, '.', '-' or '_' in each part; "
            "each part 1–96 chars; cannot start/end with '-' or '.'."
        )

    return repo_id, None


def main() -> int:
    repo_id, err = _parse_repo_id()
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        print(
            "\nFix: GitHub → repo → Settings → Secrets → Actions.\n"
            "- Add HF_SPACE_REPO_ID = YourUser/YourSpace (no newline at end).\n"
            "- Or HF_USERNAME = YourUser and SPACE_NAME = YourSpace (slug only).\n",
            file=sys.stderr,
        )
        return 1

    token = _clean(os.environ.get("HF_TOKEN", ""))

    # Log without exposing token; repo_id is not secret (public URL)
    print(f"Uploading to Hugging Face Space: {repo_id}")

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: huggingface_hub is not installed.", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            allow_patterns=ALLOW_PATTERNS,
        )
    except Exception as e:
        print(f"ERROR: Upload failed: {e!r}", file=sys.stderr)
        traceback.print_exc()
        print(
            "\nHints:\n"
            "- Create the Space on huggingface.co (Docker) with this exact name.\n"
            "- Token must have write access.\n"
            "- Repo id must match the Space URL: huggingface.co/spaces/<namespace>/<name>\n",
            file=sys.stderr,
        )
        return 1

    print("Successfully uploaded to Hugging Face Space.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
