#!/usr/bin/env python3
"""
Wrapper script for building Wizarr Plus.
The actual implementation is in the plus submodule.
"""

import subprocess
import sys

if __name__ == "__main__":
    # Call the actual script in plus submodule
    sys.exit(
        subprocess.call(
            [sys.executable, "plus/build_tools/build_plus_local.py"] + sys.argv[1:]
        )
    )
