"""
run_variance_exception_report.py - Automate the Variance Exception Report.

Generated from automation_template.py. Do not edit titan_session.py or
titan_test.py.
"""

import sys
import os

# Make sure the project root (one level up from automations/) is on the
# Python path so we can import titan_session. This lets scripts live in
# automations/ while still importing from the project's root files.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from titan_session import (
    open_titan_session,
    jump_to_function,
    fill_form,
    submit_proceed,
    quit_titan,
    force_close,
)


# ---------------------------------------------------------------------------
# REPORT IDENTITY
# ---------------------------------------------------------------------------

REPORT_NAME = "Variance Exception Report"
FUNCTION_CODE = "except.report"


# ---------------------------------------------------------------------------
# FORM FIELDS
# ---------------------------------------------------------------------------

FIELDS = [
    # Header section
    ("As-of date", None),
    ("Parameter Output", "e-claude"),
    ("Report Output", "e-claude"),
    ("Memo", None),

    # Filters
    ("Variance Type (M/L/P/*)", None),
    ("Starting Status (From)", None),
    ("Starting Status (to)", None),
    ("Starting Entity (From)", None),
    ("Starting Entity (to)", None),
    ("Starting WO# (From)", None),
    ("Starting WO# (to)", None),
    ("Exception %", None),

    # Work-orders grid (7 columns x 7 rows = 49 cells)
    ("Work-order 1", "595192"),
    ("Work-order 2", None),
    ("Work-order 3", None),
    ("Work-order 4", None),
    ("Work-order 5", None),
    ("Work-order 6", None),
    ("Work-order 7", None),
    ("Work-order 8", None),
    ("Work-order 9", None),
    ("Work-order 10", None),
    ("Work-order 11", None),
    ("Work-order 12", None),
    ("Work-order 13", None),
    ("Work-order 14", None),
    ("Work-order 15", None),
    ("Work-order 16", None),
    ("Work-order 17", None),
    ("Work-order 18", None),
    ("Work-order 19", None),
    ("Work-order 20", None),
    ("Work-order 21", None),
    ("Work-order 22", None),
    ("Work-order 23", None),
    ("Work-order 24", None),
    ("Work-order 25", None),
    ("Work-order 26", None),
    ("Work-order 27", None),
    ("Work-order 28", None),
    ("Work-order 29", None),
    ("Work-order 30", None),
    ("Work-order 31", None),
    ("Work-order 32", None),
    ("Work-order 33", None),
    ("Work-order 34", None),
    ("Work-order 35", None),
    ("Work-order 36", None),
    ("Work-order 37", None),
    ("Work-order 38", None),
    ("Work-order 39", None),
    ("Work-order 40", None),
    ("Work-order 41", None),
    ("Work-order 42", None),
    ("Work-order 43", None),
    ("Work-order 44", None),
    ("Work-order 45", None),
    ("Work-order 46", None),
    ("Work-order 47", None),
    ("Work-order 48", None),
    ("Work-order 49", None),
]


def run():
    """Run the automation. Returns 0 on success, nonzero on failure."""

    print(f"Opening Titan session for: {REPORT_NAME}")
    try:
        session = open_titan_session()
    except RuntimeError as e:
        print(f"FAILED to open session: {e}")
        return 1

    try:
        print(f"Jumping to function: {FUNCTION_CODE}")
        jump_to_function(session, FUNCTION_CODE)

        print("Filling form...")
        proceed_seen, enters = fill_form(session, FIELDS)

        if not proceed_seen:
            print(f"FAILED: Proceed dialog never appeared after {enters} Enters.")
            print("Possible causes:")
            print("  - The form has more fields than expected and we hit the safety cap")
            print("  - We jumped to the wrong screen (function code mismatch)")
            print("  - A field rejected its value and the form is still waiting")
            force_close(session)
            return 2

        print("Submitting (confirming Proceed dialog)...")
        submit_proceed(session)

        # Brief pause so Titan can start processing before we head to quit.
        import time
        time.sleep(2)

        print("Submitted. Quitting Titan...")
        rc = quit_titan(session)
        print(f"plink exited with code {rc}")
        return 0 if rc == 0 else 3

    except KeyboardInterrupt:
        print("\nInterrupted. Force-closing session.")
        force_close(session)
        return 130

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        force_close(session)
        return 4


if __name__ == "__main__":
    sys.exit(run())
