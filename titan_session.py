"""
titan_session.py - Reusable module for driving Titan ERP sessions over SSH.

DO NOT MODIFY THIS FILE when generating new automations. This is the
shared library that every automation script imports from. Any new
behavior should be added to the per-report script, not this module.

Configuration is loaded from:
  .env       - non-secret config (TITAN_HOST, AD_USER) - safe to distribute
  .env.local - secret / per-user config (AD_PASSWORD)

Connects to rhea using a shared service account (AD_USER) authenticated
with a password (AD_PASSWORD). The service account is configured in Titan
to auto-launch the application and auto-logon to the SG division, so a
successful SSH connection lands directly at a Titan menu screen.

Every Titan menu screen contains the marker "G007-DEV" in its title bar,
which is what we use to confirm we're at a menu (rather than a form,
report-running screen, etc).
"""

import os
import time
import queue
import subprocess
import threading

from dotenv import load_dotenv

# Load .env first (defaults), then .env.local (secrets / per-user overrides).
load_dotenv(".env")
load_dotenv(".env.local", override=True)


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

DEFAULT_PLINK = r"C:\Program Files\PuTTY\plink.exe"

# Marker present in the title bar of every Titan menu screen. Used to
# confirm we're sitting at a menu (vs. a form or report screen).
MENU_MARKER = b"G007-DEV"

# Marker that appears when a report's parameter form is complete and
# Titan is asking the user whether to proceed. Detecting this is how
# we know we're done filling the form and ready to submit.
#
# The full text on screen is:
#   "Do you wish to:  [P]roceed, [S]tack, [B]ackground, or [C]ancel"
# We match on "Do you wish to" without the colon because:
#   - Progress sometimes inserts escape sequences mid-string
#   - The colon may be rendered slightly later than the preceding text
#     (cursor positioning artifact), so checking before it appears
#     would miss the dialog
PROCEED_MARKER = b"Do you wish to"

# Safety cap on how many Enters we'll send while looking for the Proceed
# dialog. Set generously above the largest known form (some reports have
# 60+ enterable fields).
MAX_FORM_ENTERS = 100


# ---------------------------------------------------------------------------
# Function key escape sequences (xterm / xterm-256color compatible)
# ---------------------------------------------------------------------------

KEY_F1 = b"\x1bOP"
KEY_F2 = b"\x1bOQ"
KEY_F3 = b"\x1bOR"
KEY_F4 = b"\x1bOS"
KEY_ENTER = b"\r"
KEY_TAB = b"\t"
KEY_ESC = b"\x1b"


# ---------------------------------------------------------------------------
# Session object
# ---------------------------------------------------------------------------

class TitanSession:
    """Holds the running plink subprocess and its background reader thread."""

    def __init__(self, proc, q, reader):
        self.proc = proc
        self.queue = q
        self.reader = reader
        # Buffer of bytes drained from the queue. Used by check_for_marker()
        # so we don't lose bytes between read_until() calls.
        self.buffer = b""

    @property
    def stdin(self):
        return self.proc.stdin


# ---------------------------------------------------------------------------
# Background reader
# ---------------------------------------------------------------------------

def _reader_thread(pipe, q):
    try:
        while True:
            chunk = pipe.read(1)
            if not chunk:
                break
            q.put(chunk)
    except Exception:
        pass
    finally:
        q.put(None)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def read_until(session, marker, timeout=10):
    """Read until marker (bytes) appears or timeout. Returns (matched, captured)."""
    deadline = time.time() + timeout
    buf = session.buffer
    session.buffer = b""
    if marker in buf:
        return (True, buf)
    while time.time() < deadline:
        remaining = deadline - time.time()
        try:
            chunk = session.queue.get(timeout=min(remaining, 0.5))
        except queue.Empty:
            continue
        if chunk is None:
            return (marker in buf, buf)
        buf += chunk
        if marker in buf:
            return (True, buf)
    # Save unmatched bytes back to buffer for future reads.
    session.buffer = buf
    return (False, buf)


def drain_into_buffer(session, duration=0.3):
    """
    Drain pending output from the queue into session.buffer for `duration`
    seconds. Useful for accumulating output between actions without
    pattern-matching, so a later check_for_marker can find content that
    arrived earlier.
    """
    deadline = time.time() + duration
    while time.time() < deadline:
        try:
            chunk = session.queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if chunk is None:
            break
        session.buffer += chunk


def check_for_marker(session, marker, drain_first=0.3):
    """
    Non-blocking check: drain pending output into the buffer, then
    return True if marker is present. Doesn't consume the buffer -
    repeated calls with the same buffer state will return the same answer.
    """
    drain_into_buffer(session, duration=drain_first)
    return marker in session.buffer


def send_text(session, text):
    """Send raw text with no newline appended."""
    if isinstance(text, str):
        text = text.encode('utf-8')
    session.stdin.write(text)
    session.stdin.flush()


def send_key(session, key_bytes):
    """Send a function key or other control sequence."""
    session.stdin.write(key_bytes)
    session.stdin.flush()


def send_field(session, value=None, settle=0.2):
    """
    Send a value for a single form field, then Enter to advance.

    If value is None or empty string, just sends Enter to accept the
    default. The settle delay gives Progress a moment to render before
    the next action.
    """
    if value:
        send_text(session, str(value))
    send_key(session, KEY_ENTER)
    time.sleep(settle)


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def _build_plink_args(host, user, password, plink_path):
    """Build the argv list for plink with password authentication."""
    return [
        plink_path,
        "-ssh",
        "-l", user,
        "-pw", password,
        "-batch",
        "-t",
        "-no-antispoof",
        host,
    ]


def open_titan_session(host=None, user=None, password=None,
                       plink_path=None, timeout=10):
    """
    Open SSH to the Titan host using the service account and wait for a
    Titan menu screen (G007-DEV marker) to render.

    Returns a TitanSession sitting at a menu, ready for navigation.
    """
    plink_path = plink_path or os.environ.get('PLINK_PATH', DEFAULT_PLINK)
    if not os.path.exists(plink_path):
        raise RuntimeError(
            f"plink.exe not found at {plink_path}. "
            f"Set PLINK_PATH env var to override."
        )

    host = host or os.environ.get('TITAN_HOST')
    if not host:
        raise RuntimeError(
            "TITAN_HOST is not set. Add it to .env (TITAN_HOST=rhea)."
        )

    user = user or os.environ.get('AD_USER')
    if not user:
        raise RuntimeError(
            "AD_USER is not set. Add it to .env (AD_USER=p2lab01)."
        )

    password = password or os.environ.get('AD_PASSWORD')
    if not password:
        raise RuntimeError(
            "AD_PASSWORD is not set. Create .env.local in the project "
            "folder (see .env.local.example) with AD_PASSWORD=<password>."
        )

    args = _build_plink_args(host, user, password, plink_path)

    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )

    q = queue.Queue()
    reader = threading.Thread(target=_reader_thread, args=(proc.stdout, q), daemon=True)
    reader.start()

    session = TitanSession(proc, q, reader)

    matched, output = read_until(session, MENU_MARKER, timeout=timeout)
    if not matched:
        force_close(session)
        raise RuntimeError(
            f"Connected, but never saw a Titan menu (G007-DEV) within {timeout}s.\n"
            f"Captured (repr): {output!r}"
        )

    return session


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def jump_to_function(session, function_code, settle=1.0):
    """
    Jump directly to a Titan screen by typing its function code at the
    current Selection: prompt and pressing Enter.

    After typing, waits `settle` seconds for the destination screen to
    finish rendering before returning. This is important because the
    cursor may not be positioned on the first field until rendering
    completes - if the caller starts sending Enters before then, the
    first Enter can be consumed by the rendering process rather than
    advancing past field 1, causing every subsequent input to land one
    cursor position too early.
    """
    send_text(session, function_code)
    send_key(session, KEY_ENTER)
    time.sleep(settle)


def fill_form(session, values, post_field_settle=0.3):
    """
    Fill a Titan report parameter form by sending field values one at a
    time, watching for the Proceed dialog to appear.

    Stops when:
      - The Proceed dialog appears (success), OR
      - We've hit MAX_FORM_ENTERS Enters total (safety cap).

    `values` is a list of (label, value) tuples. label is for printing /
    debugging; value is None to accept the default.

    Returns (proceed_seen: bool, total_enters_sent: int).
    """
    enters_sent = 0

    # Send the values the user supplied.
    for label, value in values:
        if value is not None and value != "":
            print(f"  -> {label}: {value!r}")
            send_text(session, str(value))
        else:
            print(f"  -> {label}: (default)")
        send_key(session, KEY_ENTER)
        enters_sent += 1
        time.sleep(post_field_settle)

        if check_for_marker(session, PROCEED_MARKER, drain_first=0.3):
            print(f"  ** Proceed dialog appeared after {enters_sent} fields.")
            return (True, enters_sent)

        if enters_sent >= MAX_FORM_ENTERS:
            print(f"  ** Hit MAX_FORM_ENTERS ({MAX_FORM_ENTERS}) without Proceed dialog.")
            _dump_buffer_for_diagnostics(session)
            return (False, enters_sent)

    # All user-supplied values sent. Keep pressing Enter to accept defaults
    # for any remaining fields until the Proceed dialog appears.
    while enters_sent < MAX_FORM_ENTERS:
        if check_for_marker(session, PROCEED_MARKER, drain_first=0.4):
            print(f"  ** Proceed dialog appeared after {enters_sent} fields.")
            return (True, enters_sent)

        print(f"  -> (auto-default field {enters_sent + 1})")
        send_key(session, KEY_ENTER)
        enters_sent += 1
        time.sleep(post_field_settle)

    # Final check after the cap.
    if check_for_marker(session, PROCEED_MARKER, drain_first=0.5):
        print(f"  ** Proceed dialog appeared after {enters_sent} fields (just at cap).")
        return (True, enters_sent)

    print(f"  ** Hit MAX_FORM_ENTERS ({MAX_FORM_ENTERS}) without Proceed dialog.")
    _dump_buffer_for_diagnostics(session)
    return (False, enters_sent)


def _dump_buffer_for_diagnostics(session):
    """
    Print the last chunk of captured output when something goes wrong.
    Helps diagnose what state the screen is actually in vs. what we expected.
    """
    # Drain a bit more in case bytes are still arriving.
    drain_into_buffer(session, duration=0.5)
    tail = session.buffer[-2000:]
    print("\n  === Last ~2000 bytes captured (repr) ===")
    print(f"  {tail!r}")
    print("  === End diagnostics ===\n")


def submit_proceed(session):
    """
    Confirm the Proceed dialog by pressing Enter. Assumes the dialog is
    currently displayed (typically called immediately after fill_form
    returns proceed_seen=True).
    """
    send_key(session, KEY_ENTER)


def return_to_main_menu(session, max_attempts=5, per_attempt_timeout=2):
    """
    Press F4 (End) until we're back at a menu screen (G007-DEV marker
    visible). Useful before quitting, in case a report or form left us
    on a non-menu screen.

    Returns True if a menu was reached within max_attempts, False otherwise.
    """
    if check_for_marker(session, MENU_MARKER, drain_first=0.3):
        return True

    for _ in range(max_attempts):
        send_key(session, KEY_F4)
        time.sleep(0.5)
        matched, _ = read_until(session, MENU_MARKER, timeout=per_attempt_timeout)
        if matched:
            return True

    return False


def quit_titan(session, timeout=10):
    """
    Quit Titan from a menu screen. Calls return_to_main_menu() first as a
    safety net. Then types 'quit' and presses Enter, which the service
    account is configured to interpret as "exit immediately, no
    confirmation."

    Since we're connected as a service account, exiting Titan terminates
    the SSH session entirely.

    Returns plink's exit code.
    """
    if not return_to_main_menu(session):
        return force_close(session)

    send_text(session, "quit")
    send_key(session, KEY_ENTER)

    try:
        session.proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        session.proc.terminate()
        try:
            session.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            session.proc.kill()

    return session.proc.returncode


def force_close(session):
    """Hard-kill the session. Use only on error paths."""
    try:
        session.proc.terminate()
        session.proc.wait(timeout=2)
    except Exception:
        try:
            session.proc.kill()
        except Exception:
            pass
    return session.proc.returncode
