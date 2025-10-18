#!/usr/bin/env python3
"""
Wrapper script for license verification.
The actual implementation is in the plus submodule.
"""

import subprocess
import sys

if __name__ == "__main__":
    # Call the actual script in plus submodule
    sys.exit(
        subprocess.call(
            [sys.executable, "plus/build_tools/verify_plus_license.py"] + sys.argv[1:]
        )
    )
