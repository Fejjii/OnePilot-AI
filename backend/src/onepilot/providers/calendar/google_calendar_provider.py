from __future__ import annotations


from datetime import UTC, datetime, timedelta

from typing import Any

from urllib.parse import quote


import httpx


from onepilot.core.errors import ProviderUnavailableError

from onepilot.core.logging import get_logger

from onepilot.providers.calendar.base import CalendarProvider

from onepilot.providers.calendar.event_utils import (
    is_blocking_event,
    overlaps_window,
    parse_event_bounds,
)
from onepilot.providers.calendar.scope_utils import (
    has_calendar_scopes,
    missing_calendar_scopes,
    scopes_from_tokeninfo,
)

from onepilot.providers.calendar.slot_utils import (
    build_available_slots,
    pick_suggested_slots,
)

from onepilot.providers.email.gmail_auth import GoogleOAuthClient

from onepilot.schemas.calendar import (
    CalendarAvailabilityResult,
    CalendarCreateEventResult,
    CalendarEvent,
    CalendarProviderStatus,
    CalendarSlotSuggestionResult,
    CalendarStatusReason,
)


log = get_logger(__name__)


_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def _format_rfc3339(dt: datetime) -> str:

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _map_http_status_to_reason(status_code: int, *, scope_ok: bool) -> CalendarStatusReason:

    if status_code == 401:
        return "invalid_refresh_token"

    if status_code == 403:
        return "missing_calendar_scope" if not scope_ok else "calendar_api_disabled_or_forbidden"

    return "calendar_api_error"


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar API-backed provider (OAuth refresh-token flow)."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str = "primary",
        calendar_ids: list[str] | None = None,
        aggregate_selected: bool = True,
        create_enabled: bool = True,
        timeout_seconds: float = 20.0,
    ) -> None:

        if not all((client_id, client_secret, refresh_token)):
            raise ProviderUnavailableError("Google Calendar OAuth credentials not configured")

        self._oauth = GoogleOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            timeout_seconds=timeout_seconds,
        )

        self._calendar_id = calendar_id or "primary"
        self._calendar_ids = calendar_ids or []
        self._aggregate_selected = aggregate_selected

        self._create_enabled = create_enabled

        self._timeout = timeout_seconds

        self._last_status_reason: CalendarStatusReason | None = None

        self._scope_check_ok: bool | None = None

    def _resolve_calendar_id(self, calendar_id: str | None) -> str:

        return (calendar_id or self._calendar_id or "primary").strip()

    def _probe_live_api(self) -> tuple[bool, CalendarStatusReason | None]:
        """Lightweight events.list probe; supports calendarId=primary."""

        token = self._oauth.get_access_token()

        granted = scopes_from_tokeninfo(token, timeout_seconds=self._timeout)

        self._scope_check_ok = has_calendar_scopes(granted) if granted is not None else None

        if granted is not None and not has_calendar_scopes(granted):
            self._last_status_reason = "missing_calendar_scope"

            return False, "missing_calendar_scope"

        cal_id = quote(self._resolve_calendar_id(None), safe="@._-")

        now = datetime.now(UTC).replace(tzinfo=None)

        end = now + timedelta(days=1)

        params = {
            "timeMin": _format_rfc3339(now),
            "timeMax": _format_rfc3339(end),
            "maxResults": 1,
            "singleEvents": "true",
        }

        url = f"{_CALENDAR_API}/calendars/{cal_id}/events"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    self._last_status_reason = None

                    return True, None

                reason = _map_http_status_to_reason(
                    response.status_code,
                    scope_ok=bool(self._scope_check_ok),
                )

                self._last_status_reason = reason

                log.warning(
                    "calendar_probe_failed", status_code=response.status_code, reason=reason
                )

                return False, reason

        except httpx.HTTPError as exc:
            log.warning("calendar_probe_transport_error", error=str(exc))

            self._last_status_reason = "calendar_api_error"

            return False, "calendar_api_error"

    def get_status(self) -> CalendarProviderStatus:

        try:
            ok, reason = self._probe_live_api()

        except httpx.HTTPStatusError:
            ok, reason = False, "token_refresh_failed"

        except (httpx.HTTPError, ValueError):
            ok, reason = False, "token_refresh_failed"

        mode: str = "live" if ok else "unhealthy"

        return CalendarProviderStatus(
            configured=True,
            mode=mode,  # type: ignore[arg-type]
            active=ok,
            fallback_used=False,
            calendar_id=self._calendar_id,
            create_enabled=self._create_enabled,
            status_reason=reason,
            scope_check_ok=self._scope_check_ok,
            capabilities={
                "availability_check": ok,
                "suggest_slots": ok,
                "create_event": self._create_enabled and ok,
                "requires_approval_for_create": True,
            },
        )

    def _api_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:

        token = self._oauth.get_access_token()

        url = f"{_CALENDAR_API}{path}"

        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.request(method, url, headers=headers, json=json, params=params)

                response.raise_for_status()

                if response.status_code == 204:
                    return {}

                data = response.json()

                return data if isinstance(data, dict) else {}

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code

            granted = scopes_from_tokeninfo(token, timeout_seconds=self._timeout)

            scope_ok = has_calendar_scopes(granted) if granted is not None else True

            reason = _map_http_status_to_reason(code, scope_ok=scope_ok)

            self._last_status_reason = reason

            log.warning("calendar_api_error", status_code=code, path=path, reason=reason)

            raise ProviderUnavailableError(f"Calendar API unavailable ({reason})") from exc

        except httpx.HTTPError as exc:
            self._last_status_reason = "calendar_api_error"

            log.warning("calendar_api_transport_error", path=path, error=str(exc))

            raise ProviderUnavailableError("Calendar API transport error") from exc

    @staticmethod
    def _parse_event_time(value: dict | None, *, default_timezone: str = "UTC") -> datetime:
        """Parse Google event start/end dict to UTC-naive."""
        if not value:
            return datetime.now(UTC).replace(tzinfo=None)
        start, _, _ = parse_event_bounds(value, value, default_timezone=default_timezone)
        return start

    def _normalize_events(
        self,
        items: list[dict],
        *,
        default_timezone: str,
    ) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []

        for item in items:
            if not is_blocking_event(item):
                continue
            start, end, _ = parse_event_bounds(
                item.get("start"),
                item.get("end"),
                default_timezone=default_timezone,
            )
            events.append(
                CalendarEvent(
                    id=str(item.get("id", "")),
                    summary="Busy",
                    start_time=start,
                    end_time=end,
                    attendees=[],
                )
            )

        return events

    def _fetch_selected_calendar_ids(self) -> list[str]:
        data = self._api_request("GET", "/users/me/calendarList", params={"maxResults": 50})
        items = data.get("items") or []
        selected: list[str] = []
        for item in items if isinstance(items, list) else []:
            if item.get("selected") is True and item.get("id"):
                selected.append(str(item["id"]))
        return selected or [self._calendar_id]

    def _calendar_ids_for_query(self, calendar_id: str | None) -> list[str]:
        if self._calendar_ids:
            return self._calendar_ids
        resolved = self._resolve_calendar_id(calendar_id)
        if resolved != "primary":
            return [resolved]
        if self._aggregate_selected:
            try:
                return self._fetch_selected_calendar_ids()
            except ProviderUnavailableError:
                log.warning("calendar_selected_list_failed", fallback_calendar=resolved)
        return [resolved]

    def _list_events_for_calendar(
        self,
        cal_id: str,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str,
    ) -> list[dict]:
        encoded = quote(cal_id, safe="@._-")
        params = {
            "timeMin": _format_rfc3339(time_min),
            "timeMax": _format_rfc3339(time_max),
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeZone": timezone,
            "showDeleted": "false",
            "maxResults": 50,
        }
        data = self._api_request("GET", f"/calendars/{encoded}/events", params=params)
        items = data.get("items") or []
        raw_items = items if isinstance(items, list) else []
        return self._normalize_events(raw_items, default_timezone=timezone)

    def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        calendar_id: str | None = None,
        timezone: str = "Europe/Berlin",
    ) -> list[dict]:
        calendar_ids = self._calendar_ids_for_query(calendar_id)
        merged: dict[str, CalendarEvent] = {}
        failures = 0
        for cal_id in calendar_ids:
            try:
                for event in self._list_events_for_calendar(
                    cal_id, time_min, time_max, timezone=timezone
                ):
                    merged[event.id] = event
            except ProviderUnavailableError:
                failures += 1
                log.warning("calendar_events_fetch_failed", calendar_id=cal_id[:8] + "***")
                continue

        if failures == len(calendar_ids):
            raise ProviderUnavailableError("Calendar API unavailable for all queried calendars")

        return [
            {
                "id": event.id,
                "summary": event.summary,
                "start": event.start_time.isoformat(),
                "end": event.end_time.isoformat(),
                "attendees": [],
            }
            for event in merged.values()
        ]

    def count_events_next_days(self, days: int = 7) -> int:
        """Count events in the next N days (no titles returned)."""

        now = datetime.now(UTC).replace(tzinfo=None)

        end = now + timedelta(days=days)

        return len(self.list_events(now, end))

    def get_availability(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str,
        workday_start: str,
        workday_end: str,
        slot_duration_minutes: int,
        calendar_id: str | None = None,
        query_type: str = "range",
    ) -> dict:

        try:
            raw_events = self.list_events(
                time_min,
                time_max,
                calendar_id=calendar_id,
                timezone=timezone,
            )

            busy = [
                CalendarEvent(
                    id=str(item["id"]),
                    summary="Busy",
                    start_time=datetime.fromisoformat(str(item["start"])),
                    end_time=datetime.fromisoformat(str(item["end"])),
                    attendees=[],
                )
                for item in raw_events
            ]

            slots = build_available_slots(
                time_min,
                time_max,
                timezone=timezone,
                workday_start=workday_start,
                workday_end=workday_end,
                slot_duration_minutes=slot_duration_minutes,
                busy_events=busy,
            )

            conflict_count = sum(
                1
                for event in busy
                if overlaps_window(event.start_time, event.end_time, time_min, time_max)
            )

            result = CalendarAvailabilityResult(
                mode="live",
                timezone=timezone,
                busy_events=busy,
                available_slots=slots,
                fallback_used=False,
            )

            payload = result.model_dump(mode="json")

            payload["query_type"] = query_type
            payload["conflict_count"] = conflict_count
            payload["event_count"] = len(busy)
            payload["has_conflicts"] = conflict_count > 0

            return payload

        except ProviderUnavailableError as exc:
            reason = self._last_status_reason or "calendar_api_error"

            return CalendarAvailabilityResult(
                mode="unhealthy",
                timezone=timezone,
                status="error",
                error_code=reason,
                safe_error_message="Calendar provider is unhealthy. Check provider diagnostics.",
            ).model_dump(mode="json") | {"query_type": query_type}

    def suggest_slots(
        self,
        time_min: datetime,
        time_max: datetime,
        *,
        timezone: str,
        duration_minutes: int,
        max_slots: int,
        workday_start: str,
        workday_end: str,
        calendar_id: str | None = None,
    ) -> dict:

        availability = self.get_availability(
            time_min,
            time_max,
            timezone=timezone,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_duration_minutes=duration_minutes,
            calendar_id=calendar_id,
        )

        if availability.get("status") == "error":
            return CalendarSlotSuggestionResult(
                mode="unhealthy",
                timezone=timezone,
                status="error",
                error_code=availability.get("error_code"),
                safe_error_message=availability.get("safe_error_message"),
            ).model_dump(mode="json")

        from onepilot.schemas.calendar import CalendarSlot

        slots = [
            CalendarSlot.model_validate(row) for row in availability.get("available_slots") or []
        ]

        suggested = pick_suggested_slots(slots, max_slots=max_slots)

        return CalendarSlotSuggestionResult(
            mode="live",
            timezone=timezone,
            suggested_slots=suggested,
            fallback_used=False,
        ).model_dump(mode="json")

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        *,
        timezone: str,
        attendees: list[str] | None = None,
        description: str | None = None,
        location: str | None = None,
        calendar_id: str | None = None,
    ) -> dict:

        if not self._create_enabled:
            return CalendarCreateEventResult(
                mode="live",
                status="error",
                error_code="create_disabled",
                safe_error_message="Calendar event creation is disabled in server configuration.",
            ).model_dump(mode="json")

        cal_id = quote(self._resolve_calendar_id(calendar_id), safe="@._-")

        body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": timezone},
        }

        if description:
            body["description"] = description[:4000]

        if location:
            body["location"] = location[:500]

        if attendees:
            body["attendees"] = [{"email": email} for email in attendees[:10]]

        try:
            data = self._api_request("POST", f"/calendars/{cal_id}/events", json=body)

            event_id = str(data.get("id") or "")

            result = CalendarCreateEventResult(
                mode="live",
                status="success",
                event_id=event_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                attendee_count=len(attendees or []),
                fallback_used=False,
            )

            return result.model_dump(mode="json")

        except ProviderUnavailableError:
            reason = self._last_status_reason or "calendar_api_error"

            return CalendarCreateEventResult(
                mode="unhealthy",
                status="error",
                error_code=reason,
                safe_error_message="Calendar provider is unhealthy. Check provider diagnostics.",
            ).model_dump(mode="json")
