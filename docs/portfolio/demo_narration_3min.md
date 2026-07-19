# 3-Minute Demo Narration

Use with the live public demo: https://one-pilot-ai.vercel.app  
Full step list: [../demo_script.md](../demo_script.md)

---

**0:00–0:25 — Landing**  
“This is OnePilot AI — an AI operations platform for small businesses. Landing page first: product story, safety model, and architecture. No credentials. I’ll click **Try the demo**.”

**0:25–0:50 — Guided workspace**  
“We’re in a seeded NovaEdge workspace. Provider badges show what’s simulated versus available. These prompt chips run real chat requests — not hardcoded UI replies.”

**0:50–1:20 — Knowledge search**  
“I’ll ask what NovaEdge services and integrations are. The agent retrieves from the knowledge base and answers with citations. Weak evidence is called out instead of hallucinating.”

**1:20–1:55 — Approvals + simulated Gmail/Calendar**  
“Next: draft an email to a high-priority lead, then propose a meeting. The agent prepares the actions, but nothing executes until Approvals. On this public demo, Gmail and Calendar are mock providers — the HITL gate is still real.”

**1:55–2:15 — Approvals page**  
“Here’s the queue: payload, risk, approve or reject. Approving runs the configured provider and writes an audit entry.”

**2:15–2:35 — Leads / insights**  
“Leads and dashboard show pipeline and usage — business context around the agent, not just chat.”

**2:35–2:50 — Memory behavior**  
“Memory UI exists for durable facts. On the shared public demo, agent memory is disabled and demo start clears memories so reviewers don’t leak context across sessions.”

**2:50–3:00 — Mobile + close**  
“On a phone, bottom tabs and workspace Chat/History/Details keep the same flows usable. That’s OnePilot: grounded answers, tool workflows, and humans always in the loop.”
