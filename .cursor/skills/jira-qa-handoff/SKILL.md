---
name: jira-qa-handoff
description: Moves DemoProjects (KAN) Jira issues to the matching workflow status and notifies #quality-assurance plus QA Grok Bot. Use when starting, pausing, finishing, or handing a KAN ticket to QA; when working KAN-8–KAN-11 or any KAN issue; or when the user mentions Jira status, Slack QA, quality-assurance, or Grok Bot review.
---

# Jira QA handoff

Keep Jira, Slack, and QA Grok Bot in sync while a first contribution is in flight. Do this **in addition to** dual-API rules and dual-tree tests. Do not mark work Done until QA has been asked.

## Constants

| Item | Value |
|---|---|
| Jira site | `https://demoprojectsfkw.atlassian.net` |
| `cloudId` | `635779b5-f903-4920-ac1f-7aa6d4e0c0c6` |
| Project | `KAN` (statuses: **To Do**, **In Progress**, **Done**) |
| Slack channel | `#quality-assurance` (`C0CCNLT9LSE`) |
| Browse URL | `https://demoprojectsfkw.atlassian.net/browse/<KEY>` |

Transitions on this board are named the same as statuses: `To Do`, `In Progress`, `Done`. Call `listJiraIssueTransitions` if a transition fails, then retry with the returned `transitionId`.

## When to move the issue

| Moment | Jira status | Notify Slack + QA Grok Bot? |
|---|---|---|
| Agent or user **starts** implementing a KAN task | **In Progress** | Yes — work started |
| **Ready for QA** (tests in both trees pass, or UI is runnable) | Stay **In Progress** (no Review column) | Yes — please review; **do not** transition to Done |
| QA / human **approves** | **Done** | Yes — QA signed off |
| Work **stops** without finishing | **To Do** | Yes — returned to queue |
| Ticket was only **read**, no implementation | No transition | No |

Never jump **To Do → Done**. Never set **Done** just because code compiled.

## Jira (required)

1. Resolve the issue key (e.g. `KAN-9`). If the user did not give one, use the KAN ticket this session is implementing.
2. `getJiraIssue` — skip the transition if already in the target status.
3. `transitionJiraIssue` with `cloudId`, `issueIdOrKey`, `transitionName` (`In Progress` / `Done` / `To Do`).
4. `addOrEditJiraIssueComment` — one line: what changed and that QA was notified.

If a hook asks before Jira writes, wait for Allow, then retry. Do not skip the transition.

## Slack `#quality-assurance` (required)

Send with `slack_send_message` to `channel_id` `C0CCNLT9LSE`. Markdown, not Slack `*bold*`. Set `unfurl_app_links` true when the message includes the Jira URL.

**Work started**

```markdown
**QA Grok Bot** — please track this.

Started **[KAN-9](https://demoprojectsfkw.atlassian.net/browse/KAN-9)**: Add object_count to skimage.measure
Status: **In Progress**
What: implementing the library function (dual-API + tests come next).
Not ready for sign-off yet.
```

**Ready for QA** (the important handoff)

```markdown
**QA Grok Bot** — review requested.

**[KAN-10](https://demoprojectsfkw.atlassian.net/browse/KAN-10)** is ready for QA.
Status: **In Progress** (waiting on you; not Done)
How to check:
- `spin test -- tests/skimage/measure/test_object_count.py tests/skimage2/measure/test_object_count.py`
- Both test trees must pass.
Please **Allow** or reply in this channel. Do not merge until then.
```

**QA signed off**

```markdown
**QA Grok Bot** — recorded.

**[KAN-10](https://demoprojectsfkw.atlassian.net/browse/KAN-10)** moved to **Done** after QA approval.
```

Lead with **QA Grok Bot** so a Bot watching the channel can pick it up.

## QA Grok Bot (required, same payload)

After the Slack post:

1. Search Slack users for `Grok Bot` or `QA`. If a user id exists, `slack_send_message` with `channel_id` set to that user id and the **same** markdown.
2. If this session has a Grok Bot / Cursor Bot messaging tool, send that same summary there. Wait for Auto-review **Allow** before treating QA as approved.
3. If neither exists, the `#quality-assurance` post **is** the Bot front door. Tell the human in chat: paste or open QA Grok Bot with that summary if they use the desktop Bot.

Do not invent a user id. Do not mark **Done** because Slack send succeeded.

## Order for KAN-8 children

`KAN-9` (library) → `KAN-10` (tests) → `KAN-11` (web app). Handoff to QA after **KAN-10** tests pass, and again after **KAN-11** is runnable. Completing 9 without tests is not a QA handoff.

## Failure

- Slack or Jira tool error: retry once, then report the error in the user chat and continue coding. Do not pretend QA was notified.
- Channel missing: `slack_search_channels` for `quality-assurance`; do not post to `#social` or `#all-demoprojects` as a substitute.
