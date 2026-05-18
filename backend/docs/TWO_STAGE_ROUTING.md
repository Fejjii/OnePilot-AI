# Two-Stage Routing Architecture

This document describes the generalized two-stage routing architecture implemented in OnePilot AI.

## Overview

The routing system now uses a two-stage classification approach to handle user messages:

**Stage 1: Message Classification** - Classifies messages into high-level semantic categories
**Stage 2: Intent Classification** - Maps message classes to specific tool intents

This architecture prevents issues like "What can you do for me?" incorrectly routing to knowledge_search and triggering weak RAG results.

## Stage 1: Message Classification

### Module: `message_classifier.py`

Classifies messages into one of these classes:

1. **capability_or_help** - User asks what the assistant can do, how to use it, what features are available
2. **conversational** - Greetings, thanks, acknowledgments, small talk, testing
3. **correction_or_meta** - User corrections, cancellations, topic changes, conversation comments
4. **business_knowledge** - Questions about company services, policies, pricing, integrations, support, etc.
5. **workflow_request** - Requests to draft emails, create leads, schedule meetings, approve actions, summarize documents
6. **unclear** - Too short, ambiguous, or insufficient information
7. **out_of_scope** - Entertainment, weather, jokes, personal advice, clearly unrelated

### Classification Approach

Uses **semantic scoring** rather than hardcoded phrase matching:
- Each message class has a set of weighted regex patterns
- Patterns score presence of semantic indicators (not exact phrases)
- Scores are summed and thresholds determine the classification
- Priority rules ensure correct disambiguation (e.g., corrections before knowledge search)

### Example Patterns

```python
# Capability/help indicators
- "what can you do", "how can you help", "show me features"
- Assistant/system references + help/capability terms

# Business knowledge indicators
- "service", "product", "integration", "policy", "pricing"
- "your/you" + business domain terms (e.g., "your pricing")

# Workflow indicators
- Action verbs + business objects: "draft email", "create lead", "schedule meeting"
- "new customer", "interested prospect" (lead-related)
```

## Stage 2: Intent Classification

### Module: `intent_classifier.py` (updated)

Maps message classes to specific intents:

| Message Class | Intent | Rationale |
|---|---|---|
| capability_or_help | general_assistant | Explain assistant capabilities |
| conversational | general_assistant | Natural conversational response |
| correction_or_meta | general_assistant | Acknowledge and redirect |
| business_knowledge | knowledge_search | Search knowledge base with RAG |
| workflow_request | (varies) | Deeper inspection needed |
| unclear | clarification | Ask for more detail |
| out_of_scope | out_of_scope | Polite boundary |

### Workflow Request Routing

Workflow requests require deeper inspection to determine the specific action:

- **Email patterns** → `email_drafting`
- **Lead patterns** → `lead_support`
- **Document summary patterns** → `document_summary`
- **General workflow patterns** → `workflow_action`
- **Ambiguous** → `clarification`

## Updated Components

### AgentState Schema
Added fields for two-stage routing:
```python
message_class: MessageClass | None
message_class_confidence: float
message_class_reason: str
route_reason: str  # Human-readable routing explanation
```

### Workflow Graph
Updated to include message classification node:
```
classify_message -> classify_intent -> route -> {tools} -> guardrail -> finalize
```

### General Chat Tool
Enhanced to handle different message classes:
- **capability_or_help**: Returns structured capability explanation (no LLM call)
- **out_of_scope**: Returns boundary message (no LLM call)
- **conversational**: Uses conversational system prompt
- **correction_or_meta**: Uses correction-aware system prompt

## Trace Visibility

The AI Workspace trace now shows:
```
Step: classify_message
Detail: class=capability_or_help reason=capability_or_help_indicators

Step: classify_intent
Detail: rules:message_class:capability_or_help
Intent: general_assistant

Route reason: message_class=capability_or_help -> intent=general_assistant
```

## Test Coverage

- **Message Classification**: 101 tests covering all message classes and edge cases
- **Two-Stage Routing**: 27 tests covering full pipeline and priority rules
- **Intent Classification**: 13 tests covering legacy compatibility
- **Agent Workflow**: 15 tests covering end-to-end agent execution
- **General Chat Tool**: 6 tests covering message class handling

**Total: 162 passing tests**

## Key Design Principles

1. **Generalized, not example-driven**: Uses semantic scoring, not hardcoded phrases
2. **Priority-based**: Corrections and meta comments detected before knowledge search
3. **Disambiguation logic**: Business knowledge trumps capability questions when both signals present
4. **Backward compatible**: Legacy classification path preserved for old tests
5. **Auditable**: Every routing decision has a human-readable reason
6. **Deterministic**: Rule-based for reproducibility and testing

## Example Routing

### Example 1: Capability Question
```
Input: "What can you do for me?"
Stage 1: capability_or_help (score: 3.5)
Stage 2: general_assistant
Tool: chat.general
Output: Structured capability explanation
RAG Called: No
```

### Example 2: Business Knowledge
```
Input: "What services does NovaEdge Solutions offer and what integrations are supported?"
Stage 1: business_knowledge (score: 5.5)
Stage 2: knowledge_search
Tool: rag.answer
Output: Answer with citations from knowledge base
RAG Called: Yes
```

### Example 3: Correction
```
Input: "This is not what I meant."
Stage 1: correction_or_meta (score: 3.0)
Stage 2: general_assistant
Tool: chat.general (with correction prompt)
Output: "I understand. What would you like to focus on instead?"
RAG Called: No
```

### Example 4: Workflow Request
```
Input: "Draft a follow up email for this lead."
Stage 1: workflow_request (score: 5.0)
Stage 2: email_drafting (workflow sub-classification)
Tool: email.draft
Output: Email draft with approval gate
RAG Called: No
```

## Migration Notes

- Existing tests continue to work via legacy classification path
- No breaking changes to external APIs
- Trace format enhanced but backward compatible
- All existing intents preserved

## Future Improvements

- Add LLM-based classification as optional fallback (already stubbed)
- Fine-tune thresholds based on production data
- Add more sophisticated workflow disambiguation
- Support multi-class classification for hybrid requests
