import { describe, expect, it } from "vitest";
import { approvalActionLabel } from "@/lib/utils";

describe("approvalActionLabel", () => {
  it("uses recruiter-facing copy for Gmail action types", () => {
    expect(approvalActionLabel("gmail_create_draft")).toBe("Email draft");
    expect(approvalActionLabel("gmail_send_email")).toBe("Send email");
    expect(approvalActionLabel("send_email")).toBe("Send email");
  });

  it("falls back to titleized labels for other actions", () => {
    expect(approvalActionLabel("update_crm")).toBe("Update Crm");
  });
});
