#!/usr/bin/env python3
"""AdReceipts entry point: python adreceipts.py <command> --help"""

import sys

if sys.version_info < (3, 9):
    sys.stderr.write("AdReceipts needs Python 3.9 or newer.\n")
    sys.exit(1)

from adreceipts.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
