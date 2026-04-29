"""
automation_template.py - Template for new Titan report automations.

Claude Code copies this file when generating a new automation. The shape
of every generated automation matches this template exactly:

  1. Open session (always the same)
  2. Jump to function code (filled in by Claude from titan_functions.csv)
  3. Build the field-values list (filled in by Claude from screenshot)
  4. Call fill_form() and submit_proceed() (always the same)
  5. Quit cleanly (always the same)

Generated automations live in the automations/ folder.

DO NOT modify titan_session.py or titan_test.py.
"""

import sys
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
# Replace these with values for the report being automated.
# ---------------------------------------------------------------------------

REPORT_NAME = "<human-readable report name, e.g. 'Monthly Account Status Report'>"
FUNCTION_CODE = "<function code from titan_functions.csv, e.g. 'g223'>"


# ---------------------------------------------------------------------------
# FORM FIELDS
# List of (label, value) tuples representing the parameter form, in the
# order fields are visited starting from the cursor's initial position.
#
# - label: a short string for logs ("Entity Code Range From"). Pick a
#   label that matches what's on screen, so failures are easy to diagnose.
# - value: the value to type. Use None to accept whatever default is
#   currently displayed in the field.
#
# fill_form() detects the Proceed dialog automatically, so you don't
# need to count fields exactly. If your list is shorter than the form,
# fill_form() sends Enters to accept defaults for the rest. If your
# list happens to be longer, that's fine too - fill_form() stops as
# soon as the Proceed dialog appears.
# ---------------------------------------------------------------------------

FIELDS = [
    # ("As-of date", None),
    # ("Parameter Output", None),
    # ("Report Output", None),
    # ("Memo", None),
    # ("Entity Code Range From", "S0110M"),
    # ("Entity Code Range To", "S0110M"),
    # ...
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
