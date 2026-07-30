# Frozen interview mini-transcript (fn-147 R5 discrimination fixture)

Scenario: `/flow-next:interview --scope=business` on a NEW IDEA ("export saved searches").
Three questions were asked and answered; two criteria were never asked about and were
drafted by the agent while filling the acceptance section. `STRATEGY.md` has one populated
track, `### Self-serve`, whose body reads "every export path a user can reach in the product
must work without a support ticket".

Frozen — do not edit to make an emission look better. Re-emitting against a changed
transcript is not the same check.

---

Q1 (success metric): "How will you know the export feature worked?"
A1 (PO): "Support stops getting the 'can you send me my searches' ticket. Concretely:
zero of those tickets in a month."

Q2 (MVP boundary): "Which formats are in the first release?"
A2 (PO): "CSV only. JSON and the scheduled email digest are later."

Q3 (target user): "Who is doing the exporting?"
A3 (PO): "Analysts on the paid tier. Not admins, they already have the DB."

Q4 (prioritization rationale): SKIPPED by the PO ("ask engineering").

Not asked at all:
- what happens when an export exceeds the row cap
- whether the export is audit-logged
