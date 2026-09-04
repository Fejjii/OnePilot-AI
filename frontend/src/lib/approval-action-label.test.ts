import { describe, expect, it } from "vitest";
import { approvalActionLabel, isTechnicalIdentifier } from "@/lib/utils";

describe("approvalActionLabel", () => {
  it("uses recruiter-facing copy for Gmail action types", () => {
    expect(approvalActionLabel("gmail_create_draft")).toBe("Email draft");
    expect(approvalActionLabel("gmail_send_email")).toBe("Send email");
    expect(approvalActionLabel("send_email")).toBe("Send email");
  });

  it("uses recruiter-facing copy for calendar and CRM actions", () => {
    expect(approvalActionLabel("schedule_meeting")).toBe("Schedule meeting");
    expect(approvalActionLabel("calendar_create_event")).toBe("Calendar event");
    expect(approvalActionLabel("google_calendar_create_event")).toBe(
      "Calendar event",
    );
    expect(approvalActionLabel("update_crm")).toBe("Update CRM");
  });
});

describe("isTechnicalIdentifier", () => {
  it("hides raw visitor and record IDs", () => {
    expect(isTechnicalIdentifier("usr_1")).toBe(true);
    expect(isTechnicalIdentifier("org_demo")).toBe(true);
    expect(isTechnicalIdentifier("apr_1")).toBe(true);
    expect(isTechnicalIdentifier("Sarah Chen")).toBe(false);
    expect(isTechnicalIdentifier("admin@demo.com")).toBe(false);
  });
});
