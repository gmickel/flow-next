# Measure

This playbook covers both one-off performance or metric changes and changes to text a model reads (prompts, skills, or instructions). Never claim a win from reading code or text, and report any gap inside run-to-run noise as no measurable result.

## Performance or one-off metric

Identify what bounds the run from a real profile or counters rather than guessing from source. Take a baseline on a real surface in production-like settings, confirm the expected work ran with no new errors, make the change, and measure again the same way across multiple interleaved runs. Report both baseline and post-change medians, their spread, and how they were taken.

## Prompt, skill, or instruction change

Measure baseline against candidate before keeping the change, on representative cases that would show the difference, holding the model constant. Judge from observed outputs rather than self-reports, using neutral labels so the comparison stays blind. Because running model draws spends money, confirm the draw count and budget with the person before running; when unattended or declined, design the comparison harness and report that no measurement ran.
