#!/usr/bin/env python3
"""Entry point for the link-claude-project skill.

The implementation lives in the `lcp/` package alongside this file. This
script is a thin shim: it puts the script directory on sys.path so the
package imports resolve, then dispatches to lcp.cli.main.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lcp.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
