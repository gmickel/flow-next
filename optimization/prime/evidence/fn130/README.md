# fn-130 Prime authenticated evidence

Durable completion evidence for the B1 and candidate Prime judgment rules.
Unlike ordinary `optimization/prime/results/` runs, this directory is tracked.

- Backend/model: Claude Code 2.1.218, `sonnet`
- Date: 2026-07-24 UTC
- B1 source: `8ed71a73ccc593a8a018dcdb805a86f396dcf76f`
- B1/candidate rule SHA: `df3fa766e9a1cc87ff1fc789f2a3720bdfc615846caec7aa5bb653adeaec5c4f`
- Auth and instruction-leak preflights: PASS for both variants
- Outcomes: 7/7 B1 PASS; 7/7 candidate PASS
- Blocking threshold: 6/6 synthetic PASS, negative control PASS
- Usage: all 14 judgment artifacts have nonzero input and output tokens
- Isolation: every artifact records a clean, sandboxed, non-breached run

Artifacts retain the structured model output, deterministic per-fixture score,
transport usage, source ref/hash, CLI version, date, and isolation report. The
two `preflight-*.json` files retain the scrubbed auth/leak probes.

Reproduce:

```bash
python3 optimization/prime/run_agentic_eval.py --all --backend claude \
  --model sonnet \
  --rules-ref 8ed71a73ccc593a8a018dcdb805a86f396dcf76f \
  --label b1 --output-dir optimization/prime/evidence/fn130

python3 optimization/prime/run_agentic_eval.py --all --backend claude \
  --model sonnet --label candidate \
  --output-dir optimization/prime/evidence/fn130
```
