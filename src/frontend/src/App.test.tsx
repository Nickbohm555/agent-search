import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App wiki source dropdown", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the hardcoded wiki topic list even if wiki source API fails", async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("option", { name: "Geopolitics" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Strait of Hormuz" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "NATO" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "International Relations" })).toBeInTheDocument();
  });

  it("merges API loaded state into hardcoded wiki topic options", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          sources: [
            {
              source_id: "geopolitics",
              label: "Geopolitics",
              article_query: "Geopolitics",
              already_loaded: true,
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("option", { name: "Geopolitics (loaded)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "NATO" })).toBeInTheDocument();
  });
});
