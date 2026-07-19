# Screenshots — Capture Guide

PNG/JPG/WebP files in this folder are **gitignored**. Keep captures locally (or in private storage) and reference them from README / LinkedIn. This folder ships **placeholders + capture instructions** so the portfolio checklist is complete even before images are attached.

## Target set (recruiter-facing)

| Placeholder | Capture | Viewport | What to show |
|-------------|---------|----------|--------------|
| `01-landing.md` → `01-landing.png` | Landing `/` | 1440×900 | Hero with **OnePilot AI** brand signal, **Try the demo** CTA, safety line about simulated Gmail/Calendar |
| `02-workspace.md` → `02-workspace.png` | Workspace `/workspace` | 1440×900 | Guided empty state **or** cited answer; provider badges visible; prompt chips |
| `03-approvals.md` → `03-approvals.png` | Approvals `/approvals` | 1440×900 | Pending queue with risk badge and payload preview |
| `04-knowledge.md` → `04-knowledge.png` | Knowledge `/knowledge` | 1440×900 | Doc list (~19) + grounded answer with citations |
| `05-memory.md` → `05-memory.png` | Memory `/memory` | 1440×900 | Memory UI; on public demo show shared-demo / agent-memory disabled state if visible |
| `06-mobile.md` → `06-mobile.png` | Workspace mobile | 390×844 | Bottom tabs + Chat/History/Details; sticky composer |

Optional extras (nice for case study):

| File | Page | Notes |
|------|------|-------|
| `07-dashboard.png` | Dashboard | Usage + pending approvals |
| `08-leads.png` | Leads | 12 seeded leads |
| `09-settings-providers.png` | Settings | Gmail/Calendar **mock** diagnostics (no secrets) |

## Capture procedure (public demo)

1. Open https://one-pilot-ai.vercel.app in a clean browser profile.
2. Click **Try the demo**.
3. Walk [../demo_script.md](../demo_script.md) steps 2–8.
4. Capture at the viewports above (Browser DevTools device mode for mobile).
5. Redact any personal email if you signed in with a non-demo account (prefer demo entry).
6. Save files as the `.png` names in the table (gitignored).
7. Keep the matching `0x-*.md` placeholders as the checklist.

## Quality bar

- No secrets, tokens, or `.env` values in frame
- Prefer light theme as shipped
- Show **simulated** Gmail/Calendar messaging when those surfaces are visible
- Avoid overlapping OS notifications

## README embedding (after capture)

```markdown
![Landing](docs/screenshots/01-landing.png)
![Workspace](docs/screenshots/02-workspace.png)
![Approvals](docs/screenshots/03-approvals.png)
```

Until PNGs exist, link reviewers to the live demo instead of broken image tags.
