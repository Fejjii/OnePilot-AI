import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspacePanelTabs } from "./workspace-panel-tabs";

describe("WorkspacePanelTabs", () => {
  it("exposes tab semantics and reports the active panel", () => {
    render(
      <WorkspacePanelTabs
        active="chat"
        onChange={() => {}}
        detailsAvailable
        conversationCount={3}
      />,
    );

    const tablist = screen.getByRole("tablist", { name: /workspace panels/i });
    expect(tablist).toBeInTheDocument();

    const chat = screen.getByRole("tab", { name: /^chat$/i });
    expect(chat).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /history/i })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    expect(screen.getByRole("tab", { name: /details/i })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("switches panels on click", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<WorkspacePanelTabs active="chat" onChange={onChange} />);

    await user.click(screen.getByRole("tab", { name: /history/i }));
    expect(onChange).toHaveBeenCalledWith("history");

    await user.click(screen.getByRole("tab", { name: /details/i }));
    expect(onChange).toHaveBeenCalledWith("details");
  });

  it("supports arrow-key navigation between tabs", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<WorkspacePanelTabs active="chat" onChange={onChange} />);

    screen.getByRole("tab", { name: /^chat$/i }).focus();
    await user.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenCalledWith("history");
  });
});
