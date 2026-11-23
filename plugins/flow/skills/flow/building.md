# Building

These rules hold whenever you change code, on every route.

Make the smallest change the evidence justifies so every line serves the request. When the same cause also breaks a sibling case in the same code (the same fallback or parser branch), fix it there too—that is the smallest correct change, not scope creep.

Add no unrequested flags, options, config, guards, abstractions, refactors, or renames; match surrounding code without improving it, keeping only guards needed for correctness or safety. When an interface changes, update its callers and delete the old path; leave no wrapper, alias, flag, or dual paths unless asked for compatibility. Report unrelated problems rather than fixing them—check if they predated your change, fixing only what your change breaks.

Run tests for the changed code and its callers; skip the full suite unless repo instructions or the person ask for it (once, at the end), and always run any check asked for by name. Tests must call code as a user does and check the observed result; rewrite or drop any test that would still pass if the code returned nothing. Before handing back, run any user entry (command, request, or page) and inspect the result, or say plainly why it was not run; changes with no such entry are proven by their tests.
