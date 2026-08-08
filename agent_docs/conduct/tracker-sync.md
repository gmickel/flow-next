# Conduct checklist — /flow-next:tracker-sync

A correct run projects a flow spec onto one tracker issue and reconciles body, status, and comments — projection, not coordination, with the flow spec staying the source of truth.

- [ ] Every provider interaction goes through a `flowctl tracker` verb or the `tracker sync` facade, with the skill supplying only approved semantic inputs. A session that hand-builds a provider request or reproduces pagination, field mapping, or retry timing in prose or shell has broken this.
- [ ] Only the references the reached path needs are loaded — the selected provider's transport reference and no other, even when an unselected provider is linked from a file that was read.
- [ ] Comment and merged-body content travels through mode `0600` temporary files that are deleted after the call, and each synthesized comment file opens with a stable, non-placeholder `evidence=<token>` line.
- [ ] Recovery decisions branch on the envelope's `class` field rather than provider error prose, following the documented routing for `conflict`, `stale_id`, `capability`, and `external_action_required`.
- [ ] No tracker operation changes Flow task status, and a lifecycle event leaves exactly one aggregate receipt — not a second receipt written around the facade.
- [ ] Under the autonomous gate (`RALPH=1`), discovery, collisions, and body-merge conflicts are deferred or queued for a human; the transcript shows no `AskUserQuestion` on those paths.
