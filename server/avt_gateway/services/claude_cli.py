"""Claude CLI integration for document formatting and job execution."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

from ..config import config

logger = logging.getLogger(__name__)


async def format_document(tier: str, raw_content: str) -> str:
    """Format document content using Claude CLI (claude --print --model sonnet).

    Uses the temp file I/O pattern to avoid CLI arg length limits.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _format_sync, tier, raw_content)


def _format_sync(tier: str, raw_content: str) -> str:
    """Synchronous document formatting via Claude CLI."""
    prompt = f"""You are formatting a {tier} document for an Agent Vision Team project.
Clean up the following content into well-structured Markdown.
Preserve all substantive content, but improve formatting, headings, and organization.
Output ONLY the formatted document, no commentary.

---
{raw_content}
"""

    input_fd, input_path = tempfile.mkstemp(suffix="-input.md", prefix="avt-format-")
    output_fd, output_path = tempfile.mkstemp(suffix="-output.md", prefix="avt-format-")

    try:
        # Write prompt to input file
        with open(input_fd, "w") as f:
            f.write(prompt)

        # Run claude --print
        with open(input_path) as fin, open(output_fd, "w") as fout:
            result = subprocess.run(
                ["claude", "--print", "--model", "sonnet"],
                stdin=fin,
                stdout=fout,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                cwd=str(config.project_dir),
            )

        if result.returncode != 0:
            stderr = result.stderr or "Unknown error"
            raise RuntimeError(f"Claude CLI failed: {stderr}")

        # Read output
        return Path(output_path).read_text()

    finally:
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)
