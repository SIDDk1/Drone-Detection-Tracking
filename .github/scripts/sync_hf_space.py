"""
Upload only the files needed for a Hugging Face Docker Space.
Requires secrets: HF_TOKEN, HF_USERNAME, SPACE_NAME (Space slug only, not full repo id).
"""
from __future__ import annotations

import os
import sys
import traceback

# Files required for Dockerfile-based Space (see repo Dockerfile)
ALLOW_PATTERNS = [
    "Dockerfile",
    "README.md",
    "app.py",
    "packages.txt",
    "backend/**",
    "*.mp4",  # root-level video (fnmatch: **/*.mp4 does NOT match files at repo root)
    "**/*.mp4",
]


def main() -> int:
    token = (os.environ.get("HF_TOKEN") or "").strip()
    user = (os.environ.get("HF_USERNAME") or "").strip()
    space = (os.environ.get("SPACE_NAME") or "").strip()

    if not token or not user or not space:
        print(
            "ERROR: Set GitHub Actions secrets HF_TOKEN, HF_USERNAME, and SPACE_NAME.\n"
            "SPACE_NAME must be only the Space name (e.g. Drone-Detection-Tracking), "
            "not username/repo.",
            file=sys.stderr,
        )
        return 1

    if "/" in space:
        print(
            "ERROR: SPACE_NAME must not contain '/'. Use the Space slug only.\n"
            f"Got: {space!r}",
            file=sys.stderr,
        )
        return 1

    repo_id = f"{user}/{space}"
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
            "- Create the Space on huggingface.co first (Docker SDK), same name as SPACE_NAME.\n"
            "- Token needs write access (Settings → Access Tokens).\n"
            "- HF_USERNAME must match the Space owner.\n",
            file=sys.stderr,
        )
        return 1

    print("Successfully uploaded to Hugging Face Space.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
