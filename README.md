# Titan Automation Tool

A Python-based automation framework for running reports in Titan, Serigraph's
legacy ERP application (Progress OpenEdge). It connects to the Titan test
server over SSH, drives the character-based interface programmatically, fills
out report parameter forms, and submits them — eliminating the manual,
repetitive work of pulling reports from Titan by hand.

The tool is designed to be used with [Claude Code](https://www.anthropic.com/claude-code).
Users describe the report they want to automate in a structured prompt, and
Claude generates a reusable Python script that runs against Titan. The
generated scripts are deterministic and can be scheduled to run unattended.

## How It Works

1. The framework provides a hardened Python module (`titan_session.py`) that
   handles connecting to Titan, navigating to a report, filling a form, and
   exiting cleanly.
2. The user opens Claude Code in the project folder and pastes a structured
   prompt describing the report they want.
3. Claude reads `titan_functions.csv` (the Titan function code lookup) and
   the relevant report screenshot, then generates a script in `automations/`.
4. The user runs the generated script, which logs into Titan as a service
   account, navigates to the report, fills in parameters, and submits it.
5. Titan emails the report output

## Prerequisites

Before setting up the tool, make sure you have:

- A Windows machine connected to the Serigraph corporate network (VPN if
  remote)
- Python 3.11 and PuTTY
- The service account password (request from IT)
- The Claude desktop application installed and signed in

## Setup Instructions

### Step 1: Install Python 3.11

Download and install Python 3.11 from
[python.org/downloads/windows](https://www.python.org/downloads/windows/).

In the installer:

- **Check the "Add python.exe to PATH" box** (this is required)
- Use the default installation options for everything else

After installation, open a new PowerShell window and verify:

```powershell
py --version
```

You should see `Python 3.11.x`. If you see a different version or an error,
the install didn't complete correctly.

### Step 2: Install PuTTY

Download and install PuTTY from
[putty.org](https://www.putty.org/). The default install location
(`C:\Program Files\PuTTY`) is what the tool expects.

Verify the install in PowerShell:

```powershell
where.exe plink
```

You should see a path to `plink.exe`. If not, either PuTTY isn't installed,
or it's installed somewhere non-standard. In the latter case, you'll set the
`PLINK_PATH` environment variable later.

### Step 3: Clone the project

Clone or download this repository into a folder of your choice. A common
location is `C:\Users\<username>\Documents\GitHub\Titan-Automation-Tool`.

### Step 4: Set up the Python environment

Open PowerShell, navigate to the project folder, and create a virtual
environment:

```powershell
cd <path-to-project-folder>
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Your prompt should now show `(.venv)` at the start, indicating the virtual
environment is active. Install the project dependencies:

```powershell
pip install -r requirements.txt
```

### Step 5: Configure your secrets

Copy `.env.local.example` to `.env.local` in the project folder:

```powershell
Copy-Item .env.local.example .env.local
```

Open `.env.local` in a text editor and replace the placeholder with the
service account password you received from IT.

If you see anything else, jump to [Troubleshooting](#troubleshooting) below.

### Step 6: Open Claude Code

Open the Claude desktop app and navigate to the **Code** section. Start a
new session and point it at your project folder. You're now ready to
generate report automations.

## How to Use

To automate a Titan report, follow the instructions in
[`PROMPT_TEMPLATE.md`](./PROMPT_TEMPLATE.md). The template walks you through:

- Identifying the report by name (must match an entry in
  `titan_functions.csv`)
- Listing any parameters you want to override (everything else uses
  Titan defaults)
- Naming the output script

Once you paste the filled-in prompt into Claude Code, Claude will generate
a new script in the `automations/` folder. Run it with:

```powershell
python automations/<your-script-name>.py
```

### Files That Must Not Be Modified

The following files are the foundation that every generated automation
depends on. Modifying them risks breaking every script in the project:

- **`titan_session.py`** — the connection, navigation, and form-filling
  library
- **`titan_test.py`** — the smoke test that verifies the foundation is
  healthy
- **`automation_template.py`** — the template Claude copies when generating
  a new automation. Changes here propagate into every script generated
  afterward, so framework improvements should go in `titan_session.py`
  whenever possible. Only change the template if the *shape* of every
  generated script needs to change.

If you find a bug or want to extend the framework, fix it in those files
once and verify with `titan_test.py` — but do not modify them as part of
generating a new automation.

## Notes for Developers

### Service Account Configuration

The tool depends on a specific configuration of the service account in
Titan. If any of these change, scripts will break:

- **Auto-launch:** the service account auto-launches Titan on SSH login,
  bypassing the bash shell
- **Auto-logon:** the account auto-logs into the SG Division using entity
  `S0110m` and warehouse `f1`, skipping the login parameters form
- **Skip quit confirmation:** the user preference to confirm quit is
  disabled, so typing `quit` at the Selection: line exits immediately
- **Single Titan account:** the account has only one Titan login, avoiding
  the account-selection screen that appears for multi-account users

Preferences are managed via the Titan `user.prefs` function. If they
get reset (or the account gets reprovisioned), the foundation will need
adjustments.

### Email Printer Setup (`e-claude`)

Report output is routed via a custom Titan "printer" that emails reports
to a configurable address rather than physically printing them. The
current setup uses a printer named `e-claude` configured for email
output. If this printer is ever lost or needs to be recreated, follow
these steps:

**1. Create or verify the `e-claude` email printer via `printer.maint`:**

- Navigate to the `printer.maint` function in Titan
- Set the following fields:
  - **Printer-name:** `e-claude`
  - **Printer-type:** `Email`
  - **Output-spec:** `thru llp -dlp1003 -s -t"Titan Automated Report" -omailto="<destination>"`

**2. Point the service account at the `e-claude` printer via `user.maint`:**

- Navigate to the `user.maint` function in Titan and pull up the service
  account (`p2lab01`)
- Set both of these fields to `e-claude`:
  - **Report Output**
  - **Param Output**

### Progress CHUI Quirks

Titan runs on Progress OpenEdge 11.7.5 and uses Progress's CHUI (Character
User Interface) library to render screens. Some implications:

- **Screens are character-positioned, not line-oriented.** Output captured
  from the SSH session looks like
  `\x1b[2J\x1b[H\x1b[1;1H...` — escape sequences positioning text on a
  virtual character grid. The literal text we want is in there, but
  surrounded by formatting bytes.
- **Marker matching uses literal substrings.** We match against text
  fragments that we know appear on specific screens (e.g., `G007-DEV` for
  any menu, `Do you wish to` for the Proceed dialog). Markers are chosen
  to be specific enough to avoid false positives but short enough to avoid
  false negatives from escape sequences inserted mid-string.
- **Form submission is "fill until dialog appears."** Rather than counting
  fields, the framework presses Enter through every field and watches for
  the Proceed dialog text. This makes scripts robust against minor
  screenshot misreadings (extra or missing fields).
- **Different screens use different keys.** Most screens use Enter to
  advance; some use F1 (Go), F4 (End), or function keys with
  context-specific meanings. The framework currently only uses Enter and
  F4, which has been sufficient for all reports tested.

## Known Limitations

- **Test environment only.** All scripts run against the Titan test
  server (`rhea`). No production usage has been validated.

- **Read-only.** The tool only runs reports. It does not write data
  back into Titan. Write-back is intentionally out of scope until
  read-only extraction is fully proven.

- **Screenshot interpretation is imperfect.** Claude reads form structure
  from screenshots alone, with no companion specification file. Forms
  with dense layouts or ambiguous labels may produce scripts that put the
  wrong values in the wrong fields. The fix is to regenerate with more
  explicit field listings in the prompt.
