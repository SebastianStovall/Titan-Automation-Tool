# Titan Report Automation Prompt Template

Copy the prompt below into a new Claude Code session pointed at this
project folder. Fill in the bracketed sections with your report details.

---

## Prompt to paste:

```
I want to automate a Titan report.

REPORT NAME: <exact description from titan_functions.csv,
              e.g. "Monthly Account Status Report">

PARAMETERS:
  <field name>: <value>
  <field name>: <value>
  <leave any field blank or omit it to accept the Titan default>

OUTPUT FILENAME: <descriptive name for the generated automation script,
                  e.g. "pull_monthly_account_status.py">

---

Please generate a new automation script in the automations/ folder.
Follow these rules exactly:

1. READ titan_session.py to understand the available helper functions.
   DO NOT modify it. DO NOT modify titan_test.py. DO NOT modify
   automation_template.py.

2. READ titan_functions.csv to find the function code for the requested
   report. The "description" column matches what I gave under REPORT NAME.
   The "function" column has the code to use with jump_to_function().

3. READ the screenshot for this report's parameter form, located at
   reports/<report-name>/parameters.png. From the screenshot, determine:
   - The list of fields in cursor-traversal order (top-to-bottom,
     left-to-right within each row)
   - The default values shown on screen
   - Which fields I want to override (per the PARAMETERS section above)
     vs. which to accept defaults for

   Before writing the FIELDS list, walk through the screenshot
   methodically and enumerate every cursor stop. State the breakdown out
   loud in your reasoning, structured by section. For each section,
   identify what it is (header, filter row, grid, etc.), the cursor
   stops in traversal order, and the count for that section. Then sum
   the section counts to get the total.

   When counting, remember:

   - **Multi-column rows.** A row that displays as
     "Starting Status: F   to: CC" is two cursor stops, not one - a
     "From" value and a "To" value. Count both.

   - **Grids.** A grid of N columns by M rows is N*M cells = N*M cursor
     stops, traversed left-to-right within each row, then to the next
     row. State the dimensions explicitly.

   - **Display-only fields don't count.** Read-only labels, computed
     values, and "Page X of Y" indicators are not cursor stops. Only
     enterable fields (shown with input underlines, highlights, or
     editable widgets) are stops.

4. COPY automation_template.py to automations/<OUTPUT FILENAME>. Replace
   the placeholder identity values and the FIELDS list with the real
   field-by-field tuples for this report.

5. Each entry in FIELDS is (label, value). Use a short, descriptive
   label that matches what's on the screen ("Entity Code Range From").
   Use None for value to accept the Titan default. Use a string value
   to override.

6. fill_form() detects the Proceed dialog automatically. You do NOT
   need to count fields exactly - if you miss a few at the end,
   fill_form() sends Enters to accept defaults until the dialog
   appears. But list every field you can see so the log output is
   readable and so override values land on the right field.

7. Do NOT modify the open_titan_session(), jump_to_function(),
   fill_form(), submit_proceed(), or quit_titan() helpers, and do NOT
   add timing-related code (sleeps, waits, retries) inside the
   generated script. The library already handles render timing,
   inter-field settling, and dialog detection. Adding ad-hoc waits in
   the script is more likely to cause bugs than fix them.

8. Do NOT remove or change the `sys.path` manipulation block at the top
   of the imports. The script lives in the automations/ subfolder, so
   that block is what allows it to import titan_session from the
   project root. Without it, the script will crash with
   "ModuleNotFoundError: No module named 'titan_session'".

9. After generating the script, print a brief summary listing:
   - The function code used
   - The total field count and the section breakdown
   - Which fields used the value I provided vs. accepting defaults

When you're done, I'll run the new script with
`python automations/<OUTPUT FILENAME>`.
```

---

## Notes for users

- **REPORT NAME** must match a description in `titan_functions.csv`. If
  Claude can't find a unique match, it will ask you to clarify.

- **PARAMETERS** can be omitted entirely if you want all defaults. List
  one field per line in the format `Field Name: value`. Leave fields
  out (or specify them with no value) to accept Titan's default.

- **OUTPUT FILENAME** should be descriptive. It becomes the script name
  in `automations/`. Use snake_case and end with `.py`.

- The script doesn't produce a CSV directly. Titan emails the report
  output to the address mapped to the running Titan account.

- If a script doesn't work right, the printed field labels in its
  output tell you which field got which value (according to the
  script's labels - not necessarily where the cursor actually was). If
  values land in the wrong place, the most common cause is a
  miscounted cursor stop earlier in the FIELDS list. Verify by walking
  through the form manually one Enter at a time and counting.
