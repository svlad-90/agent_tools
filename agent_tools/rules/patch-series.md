---
sync: skill
---

# Patch Series Workflow

These rules apply when an agent constructs, rewrites, reviews, or prepares a
git patch series, especially for serious external or open-source projects.

Optimize not only for the final working diff, but for a human-reviewable
series. A reviewer should be able to read the commits in order and understand
the design as a set of small, justified layers.

## Read Nearby Code First

Before editing, inspect the surrounding subsystem and adjacent components that
solve similar problems. Prefer existing local patterns for naming, public API
shape, internal/private header boundaries, data structures, synchronization,
error handling, tests, and build integration.

Do not invent a parallel architecture when the repository already has a nearby
one.

## Series Shape

Build the series from the base branch in logical layers:

1. Common or shared code extraction, if the reviewed change needs it.
2. Mechanical rename or file movement, if needed.
3. Minimal buildable core implementation.
4. Incremental feature additions, one coherent behavior per commit.
5. API compatibility or migration wrappers, after the core mechanism exists.
6. Tests and validation support, placed where they make the relevant behavior
   reviewable.

The exact order may vary, but each commit must have one clear reason to exist.

Avoid giant "add everything" commits. Avoid fixup-style commits unless the
user explicitly asks for them.

## Commit Quality

Each commit should:

- Build independently when checked out.
- Preserve existing behavior unless the commit explicitly changes it.
- Have one clear purpose.
- Be small enough for a reviewer to understand.
- Explain why the change exists, not only what files changed.
- Avoid mixing unrelated concerns.

Do not mix these in one commit unless the split would make the tree
temporarily unbuildable:

- Common-code extraction.
- Mechanical renames.
- New functionality.
- Public API changes.
- Internal implementation details.
- Tests.
- Formatting or cleanup.
- Compatibility wrappers.

## No Opportunistic Cleanup

Do not add opportunistic improvements just because nearby code looks
imperfect.

Before including any cleanup, ask:

- Is it required by the user request?
- Is it required by a reviewer comment?
- Is it required for the current feature to work correctly?
- Is it required to keep an intermediate commit buildable?
- Is there a failing test or concrete bug that justifies it?

If the answer is no, leave it out.

If cleanup is required, isolate it in its own commit and state the dependency
clearly in the commit message and review notes.

## Review Comments

Treat reviewer comments as design constraints, not as after-the-fact patches.

For every reviewer comment:

- Identify the architectural intent behind the comment.
- Check whether adjacent code already solves the same problem.
- Apply the fix in the earliest logical commit.
- Avoid adding a workaround in new code when common code or existing design
  should be reused.
- Keep public API concerns separate from internal implementation concerns.

If a comment asks for common factoring, do that before adding the new user of
the common code.

If a comment asks to hide internals, do not expose temporary public structs
just to make implementation easier.

If a comment asks for API harmonization, first understand the existing API and
then add compatibility only after the core implementation can support it.

## Public vs Internal API

Keep public headers narrow.

Public API may expose:

- Stable types callers must use.
- Opaque handles.
- Function declarations.
- Constants that are part of the contract.

Public API should not expose:

- List nodes.
- Locks.
- Semaphores.
- Workqueue state.
- Internal buffers.
- Parser state.
- Lifetime bookkeeping.
- Transport internals.

When the library owns object lifetime, prefer opaque handles and allocate/free
inside the library.

If internal lifetime tracking is needed, explain the concrete race, ownership
rule, or callback behavior it protects.

## Common Code

Move code into common modules only when there are at least two legitimate
users, or when an existing component already defines the authoritative
representation.

When factoring common code:

- Move the narrowest reusable type or helper.
- Keep component-specific storage private.
- Convert between common data and private runtime structures at module
  boundaries.
- Avoid forcing one component's internal representation onto another component.
- Keep common helpers small and protocol-focused.

## Naming

Use precise names.

Avoid abbreviations that have common conflicting meanings. For example, do not
use "cli" for a client library if it can be read as "command line interface".
Prefer names that match the role of the module in the architecture.

Mechanical renames should be separate from behavioral changes when practical.

## Validation

After constructing or rewriting a series:

- Validate every commit that is expected to be buildable.
- Validate the final runtime behavior when a runtime environment exists.
- Record which command validated which commit.
- If an intermediate commit cannot be build-tested, explain why and
  restructure if possible.

Do not claim the series is ready for review until validation matches the
series that will be pushed.

If commit messages are rewritten or commits are reordered, remember that
commit hashes changed. Revalidate or clearly prove that only metadata changed.

## Review Reports

When producing review reports for a series:

- Generate one report per commit unless explicitly asked otherwise.
- Use stable commit indexes: Commit 01, Commit 02, etc.
- Explain why each commit exists at that point in the series.
- State which reviewer comments it addresses.
- State what is intentionally deferred to later commits.
- Call out any non-obvious design or lifetime decision.
- Do not justify unrelated cleanup after the fact. Remove it unless it is
  truly required.

## Final Check

Before finishing, review the final diff against the original request and ask:

- Is every change necessary?
- Is every reviewer comment addressed in the right layer?
- Can a human understand the series incrementally?
- Does each commit build?
- Did we avoid accidental cleanup?
- Are public APIs narrow and internals hidden?
- Is the pushed branch the validated branch?

If any answer is weak, fix the series before reporting completion.
