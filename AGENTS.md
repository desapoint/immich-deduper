# Repository Instructions

## Fork and contribution workflow

This repository is a fork of `RazgrizHsu/immich-deduper`.

- Treat `origin` (`desapoint/immich-deduper`) as the writable fork and `upstream`
  (`RazgrizHsu/immich-deduper`) as the read-only source project.
- Keep every change minimal and limited to the user's request. Do not include
  unrelated cleanup, refactoring, formatting, dependency updates, or generated
  files unless they are required or explicitly requested.
- Preserve fork-specific behavior. Check the relevant differences from upstream
  before changing code that may have diverged, and do not silently overwrite or
  revert either the user's work or fork-only changes.
- Prepare changes so they are reviewable as a focused pull request: use a
  purpose-specific branch when branch work is requested, keep commits cohesive,
  follow the repository's contribution and PR templates, and run proportionate
  validation for the files changed.
- Do not push branches, create pull requests, or otherwise mutate a remote unless
  the user explicitly asks for that remote action.
- If the user asks for a pull request without naming a destination repository,
  target `origin` (the fork), never `upstream`.
- Never open, submit, or retarget a pull request to `upstream` unless the user
  explicitly asks to propose that specific change to the upstream project.
- When the user explicitly requests an upstream contribution, first compare the
  change with the current upstream base. Put only the generally useful upstream
  change on a dedicated branch, exclude fork-specific and unrelated commits,
  follow upstream's contribution guidance, validate it, and show the intended
  upstream base/head and PR content before submission when approval is needed.
- Fetching or inspecting upstream is read-only and may be used when needed.
  Merging, rebasing, or otherwise syncing upstream into the fork requires an
  explicit user request because it can materially change the fork.
