#!/usr/bin/env python3
"""
Wrapper for Wizarr Plus Cython compilation.
The actual implementation is in the plus submodule.
"""

import subprocess
import sys

if __name__ == "__main__":
    # Call the actual setup script in plus submodule
    sys.exit(
        subprocess.call(
            [sys.executable, "plus/build_tools/setup_plus.py"] + sys.argv[1:]
        )
    )
