# <Feature name>

**Estimate:** <n>d
**Depends on:** <feature folders, or "nothing">
**Status:** not started

## Purpose

One paragraph. What this does, and what breaks if it does not exist.

## Behaviour

What the agent or workflow actually does, in the order it does it. Write the
Hebrew script lines out where the exact wording matters — "be polite" is not
implementable, a sentence is.

## Interface

The tool contract, if this feature exposes one.

**`tool_name`**

| Field | Type | Required | Notes |
|---|---|---|---|

Returns:

```json
{}
```

## Data

Which tables and columns this reads and writes. Name them exactly; a spec that
says "saves the request" is a spec nobody can verify.

## Acceptance

Numbered, checkable, and each one falsifiable by a single test call. "Works
well" is not acceptance. "Ten consecutive calls, zero wrong rows" is.

1.

## Out of scope

What this feature deliberately does not do, and which feature or release owns it
instead. This section prevents scope drift more reliably than any other.
