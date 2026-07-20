# Screenshots — Launch Asset Package

PNG files in this folder are **gitignored**. Keep captures locally and in the iCloud
Launch Assets folder for LinkedIn / portfolio sharing.

## Canonical launch set (verified public demo)

| File | Viewport | Subject |
|------|----------|---------|
| `01-landing.png` | 1440×900 | Landing hero + Try the demo |
| `02-workspace.png` | 1440×900 | Guided workspace, prompt chips, provider badges |
| `03-structured-response.png` | 1440×900 | Completed AI answer with structure/citations |
| `04-approvals.png` | 1440×900 | HITL inbox with curated pending requests |
| `05-knowledge.png` | 1440×900 | Knowledge base + grounded answer |
| `06-leads.png` | 1440×900 | Leads table (seeded pipeline) |
| `07-memory.png` | 1440×900 | Memory UI + shared-demo isolation messaging |
| `08-mobile-workspace.png` | 390×844 | Mobile bottom nav + workspace panels |

Compatibility aliases (older checklist names):

| Alias | Points to |
|-------|-----------|
| `03-approvals.png` | `04-approvals.png` |
| `04-knowledge.png` | `05-knowledge.png` |
| `05-memory.png` | `07-memory.png` |
| `06-mobile.png` | `08-mobile-workspace.png` |

## Capture rules

1. Use **only** https://one-pilot-ai.vercel.app (public demo).
2. Prefer **Try the demo** entry. Do not show credentials, tokens, DevTools, or env values.
3. Confirm badges: Gmail/Calendar **Simulated**; Knowledge retrieval **Fallback ready** (not Unavailable).
4. Approvals titles must be curated NovaEdge copy (Brightline, Northwind, …) — never Faker/lorem.
5. Structured-response shot must wait until the assistant finishes (not “thinking…”).

## Quality bar

- Professional, populated UI (no broken empty states for key surfaces)
- No internal/dev-only wording as the main message
- No secrets
- Consistent dimensions as above

## iCloud copy

```bash
LAUNCH="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AI-Projects/OnePilot AI/Launch Assets"
mkdir -p "$LAUNCH/screenshots" "$LAUNCH/docs"
cp docs/screenshots/*.png "$LAUNCH/screenshots/"
cp -R docs/portfolio "$LAUNCH/docs/"
cp docs/demo_script.md README.md "$LAUNCH/docs/"
```
