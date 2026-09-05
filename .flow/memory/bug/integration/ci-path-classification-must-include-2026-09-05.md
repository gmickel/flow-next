---
title: CI path classification must include rename sources
date: "2026-09-05"
track: bug
category: integration
module: scripts/ci/classify_changes.py
tags: [ci, git, renames, path-classification]
problem_type: integration
symptoms: A launcher moved to Markdown skipped platform coverage
root_cause: Git name-only rename output omitted the deleted source path
resolution_type: fix
---

## Problem
Git diff --name-only can report only the destination of a detected rename. A runtime file moved into a docs path was classified as docs-only and skipped the Windows launcher smoke.

## Solution
Use git diff --no-renames --name-only -z so the classifier sees both deleted and added paths. The CI policy test moves scripts/launcher to README.md in a temporary Git repository and verifies both paths and full platform coverage for PR and push events.

## Prevention
Test classifier boundaries using real Git renames, including code-to-docs and moves out of platform-specific directories. Filename classification must account for removed paths.
