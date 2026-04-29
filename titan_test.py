"""
titan_test.py - Smoke test for the Titan automation foundation.

DO NOT MODIFY THIS FILE when generating new automations. This is the
foundation health-check that should always work. Any new behavior
belongs in a new script under automations/.

Connects to rhea, verifies arrival at a Titan menu (G007-DEV marker),
then quits cleanly. Used to verify the foundation is healthy before
running real automations.

Run with the venv activated:
    python titan_test.py
"""

import sys
from titan_session import (
    open_titan_session,
    quit_titan,
    force_close,
)


def main():
    print("Step 1: Opening service-account session and waiting for Titan menu...")
    try:
        session = open_titan_session()
    except RuntimeError as e:
        print(f"FAILED: {e}")
        return 1
    print("        Reached Titan menu (G007-DEV).")

    try:
        print("\nStep 2: Quitting Titan and closing the SSH session...")
        rc = quit_titan(session)
        print(f"        plink exited with code {rc}")

        if rc == 0:
            print("\nFOUNDATION HEALTHY: connect -> menu -> quit, all clean.")
            return 0
        else:
            print(f"\nFoundation mostly OK but plink exit code was {rc} (expected 0).")
            return 2

    except KeyboardInterrupt:
        print("\nInterrupted. Force-closing session.")
        force_close(session)
        return 130


if __name__ == "__main__":
    sys.exit(main())
