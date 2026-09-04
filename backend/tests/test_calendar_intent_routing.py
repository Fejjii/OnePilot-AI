"""Calendar tool inference: meetings vs availability vs scheduling must not cross-route."""

from __future__ import annotations

from onepilot.services.calendar_service import infer_calendar_tool

MEETINGS_PROMPTS = (
    "Show my meetings this week.",
    "What meetings are on the calendar this week?",
    "What's on my calendar this week?",
    "List my upcoming meetings",
    "Check my calendar",
)

AVAILABILITY_PROMPTS = (
    "Am I free tomorrow afternoon?",
    "Find available time slots this week.",
    "Find open slots tomorrow",
    "Check my availability next week",
    "When am I free this week?",
)

SUGGEST_PROMPTS = (
    "Suggest three meeting slots next week.",
    "Recommend times for a 30 minute call",
)

SCHEDULE_PROMPTS = (
    "Schedule a 30 minute meeting with a high priority lead next week.",
    "Book a call tomorrow at 3 p.m.",
    "Set up a meeting with the lead on Friday",
    "Create a meeting tomorrow afternoon",
)


def test_meetings_prompts_route_to_list_events() -> None:
    for prompt in MEETINGS_PROMPTS:
        assert infer_calendar_tool(prompt) == "list_events", prompt


def test_availability_prompts_route_to_check_availability() -> None:
    for prompt in AVAILABILITY_PROMPTS:
        assert infer_calendar_tool(prompt) == "check_availability", prompt


def test_suggest_prompts_route_to_suggest_slots() -> None:
    for prompt in SUGGEST_PROMPTS:
        assert infer_calendar_tool(prompt) == "suggest_slots", prompt


def test_schedule_prompts_route_to_create_event_request() -> None:
    for prompt in SCHEDULE_PROMPTS:
        assert infer_calendar_tool(prompt) == "create_event_request", prompt


def test_no_cross_routing_between_calendar_intents() -> None:
    for prompt in MEETINGS_PROMPTS:
        assert infer_calendar_tool(prompt) != "check_availability"
        assert infer_calendar_tool(prompt) != "create_event_request"
    for prompt in AVAILABILITY_PROMPTS:
        assert infer_calendar_tool(prompt) != "list_events"
        assert infer_calendar_tool(prompt) != "create_event_request"
    for prompt in SCHEDULE_PROMPTS:
        assert infer_calendar_tool(prompt) != "list_events"
        assert infer_calendar_tool(prompt) != "check_availability"


def test_explicit_context_overrides_message() -> None:
    assert (
        infer_calendar_tool(
            "Show my meetings this week.",
            context={"calendar_tool": "check_availability"},
        )
        == "check_availability"
    )
