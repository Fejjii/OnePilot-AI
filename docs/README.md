# OnePilot AI Documentation

This directory is the technical documentation entry point for reviewers, maintainers, and development agents.

## Start here

| Document | Purpose |
| --- | --- |
| [Architecture overview](portfolio/ARCHITECTURE_OVERVIEW.md) | Fast technical scan of the system |
| [Architecture](architecture.md) | Detailed system design and component boundaries |
| [Capabilities](capabilities.md) | Current live, simulated, and unavailable capability matrix |
| [Evaluation](evaluation.md) | Deterministic evaluation and regression results |
| [Recruiter demo script](portfolio/RECRUITER_DEMO_SCRIPT.md) | Short guided product walkthrough |

## Core engineering

| Area | Documentation |
| --- | --- |
| Agent orchestration | [Agent workflow](agent_workflow.md) |
| Retrieval augmented generation | [RAG system](rag_system.md) |
| Data platform | [Data architecture](data_architecture.md) and [Data model](data_model.md) |
| Security | [Security](security.md) |
| Safety and privacy | [Safety and privacy](safety_and_privacy.md) |
| Deployment | [Deployment](deployment.md) and [Deployment checklist](deployment_checklist.md) |
| Local development | [Local environment](local_environment.md) |
| Services and scripts | [Services and scripts](services_and_scripts.md) |
| Product limitations | [Limitations and roadmap](limitations_roadmap.md) |

## Demo and integration operations

Public demo documentation is kept in the top level of this directory.

Private Google integration documentation is under [private_demo](private_demo).

Recruiter presentation material is under [portfolio](portfolio).

Screenshots and supporting visual assets are under [screenshots](screenshots).

## Agent collaboration

Cloud and mobile development handoffs are under [agent](agent).

The repository branch roles are:

1. `main` is the canonical product source.
2. `deployment/public-demo` is the public recruiter demo deployment pointer.
3. `deployment/live-google-demo` is the controlled private Google integration deployment pointer.
4. `agent/cloud-state` is an orphan reporting ref for sanitized agent reports and is not a product branch.
5. Feature, fix, documentation, infrastructure, and polish branches are temporary and should be removed after their pull requests are merged.

## Historical material

Completed implementation summaries and superseded planning prompts are preserved under [archive](archive).

Historical documents are useful for provenance, but they are not the current source of truth. Use the root README and the current technical documents above for present behavior.
