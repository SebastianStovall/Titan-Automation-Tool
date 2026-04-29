# Titan Report Automation Prompt Template

Copy the prompt below into a new Claude Code session pointed at this
project folder. Fill in the bracketed sections with your report details.

---

## Prompt to paste:

```
I want to automate a Titan report.

REPORT NAME: Variance Exception Report

PARAMETERS:
  Work-orders: 595192

OUTPUT FILENAME: run_variance_exception_report.py

---

Please generate a new automation script in the automations/ folder.
Follow these rules exactly:

1. READ titan_session.py to understand the available helper functions.
   DO NOT modify it. DO NOT modify titan_test.py.

2. READ titan_functions.csv to find the function code for the requested
   report. The "description" column matches what I gave under REPORT NAME.
   The "function" column has the code to use with jump_to_function().

3. READ the screenshot for this report's parameter form, located at
   reports/<report-name>/parameters.png. Use it to determine:
   - The list of fields, in order from cursor start (top-to-bottom,
     left-to-right within each row)
   - Default values shown on screen
   - Which fields I want to override (per the PARAMETERS section above)
     vs. which to accept defaults for

4. COPY automation_template.py to automations/<OUTPUT FILENAME>. Replace
   the placeholder identity values and the FIELDS list with the real
   field-by-field tuples for this report.

5. Each entry in FIELDS is (label, value). Use a short, descriptive label
   that matches what's on the screen ("Entity Code Range From"). Use None
   for value to accept the Titan default. Use a string value to override.

6. fill_form() detects the Proceed dialog automatically. You do NOT need
   to count fields exactly - if you miss a few, fill_form() will send
   Enters to accept defaults for the rest. But it's still better to list
   every field you can see so the log output is readable.

7. Do NOT modify the open_titan_session(), fill_form(), submit_proceed(),
   or quit_titan() boilerplate. Do NOT add error handling beyond what's
   in the template.

8. After generating the script, print a brief summary listing:
   - The function code used
   - The fields listed in FIELDS, indicating which had override values
     and which used defaults

When you're done, I'll run the new script with `python automations/<OUTPUT FILENAME>`.
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

- If a script doesn't work right, the printed field labels in its output
  tell you which field got which value. Common fixes:
  - Wrong field count: re-check the screenshot, regenerate the script
  - Wrong values in fields: Claude misread the screenshot, regenerate
    with more explicit field listing in the PARAMETERS section
