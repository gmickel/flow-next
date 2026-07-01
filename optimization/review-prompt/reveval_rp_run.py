#!/usr/bin/env python3
"""EXAMPLE (RP backend-in-the-loop). W/T + FLOWCTL are run-specific — set them
from a fresh `flowctl rp setup-review ... --json` before reuse.

Send baseline vs ft_tighter review prompts through RP (GPT-5.5-high + builder
context) and score detection — the real end-to-end RP validation."""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reveval as R  # noqa: E402

FLOWCTL = "/Users/gordon/work/flow-next/.claude/worktrees/fn-74-cursor-review-backend-cursor-agent-cli/.flow/bin/flowctl"
W = "132"
T = "EDA20987-16AE-4675-898A-C932ABB3C101"
HERE = os.path.dirname(os.path.abspath(__file__))


def chat_send(prompt_file, chat_name, timeout=600):
    t0 = time.time()
    p = subprocess.run(
        [FLOWCTL, "rp", "chat-send", "--window", W, "--tab", T,
         "--message-file", prompt_file, "--new-chat", "--chat-name", chat_name,
         "--mode", "review"],
        capture_output=True, text=True, timeout=timeout)
    return p.stdout, time.time() - t0, p.returncode


def main():
    print("# RP review (GPT-5.5-high) — baseline vs ft_tighter\n")
    for name in ["baseline", "ft_tighter"]:
        pf = os.path.join(HERE, f"rp_prompt_{name}.md")
        try:
            review, dt, rc = chat_send(pf, f"reveval {name}")
        except subprocess.TimeoutExpired:
            print(f"  [{name}] TIMEOUT"); continue
        with open(os.path.join(HERE, f"rp_out_{name}.md"), "w") as fh:
            fh.write(review)
        d = R.detect(review)
        print(f"  [{name}] caught {sum(d.values())}/10 "
              f"(corr {sum(d[g] for g in R.CORRECT)}/5, smell {sum(d[g] for g in R.SMELLS)}/5) "
              f"{dt:.0f}s rc={rc} {R.verdict_of(review)} out={len(review)}ch")
        miss = [f"{g}={R.GROUND[g][1]}" for g in R.GROUND if not d[g]]
        print(f"       missed: {miss}")


if __name__ == "__main__":
    main()
