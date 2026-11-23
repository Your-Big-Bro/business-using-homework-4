"""pip wrapper that avoids the sandbox-broken tempfile.mkdtemp.

On this Windows host the DSH sandbox gives directories created by
tempfile.mkdtemp an owner-only ACL (they become unreadable even for the
creating process), which breaks pip's download/unpack step. Replacing
mkdtemp with a plain os.makedirs based implementation fixes it.

Usage:  python tools/pipx.py install --target .pylibs <pkgs...>
"""
from __future__ import annotations

import os
import random
import string
import sys
import tempfile


def _mkdtemp(suffix: str | None = None, prefix: str | None = None, dir: str | None = None) -> str:
    base = dir or tempfile.gettempdir()
    for _ in range(200):
        name = (prefix or "tmp") + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        ) + (suffix or "")
        path = os.path.join(base, name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            return path
    raise FileExistsError("mkdtemp: could not create a unique directory")


tempfile.mkdtemp = _mkdtemp

from pip._internal.cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
