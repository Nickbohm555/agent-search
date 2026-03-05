import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

describe("App run query flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("posts query to /api/agents/run and renders returned output", async () => {
    let resolveRunRequest: ((value: Response) => void) | undefined;
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveRunRequest = resolve;
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What is NATO?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();

    resolveRunRequest?.(
      new Response(JSON.stringify({ output: "NATO is a military alliance." }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    expect(await screen.findByText("NATO is a military alliance.")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/agents/run",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "What is NATO?" }),
        }),
      );
    });
  });

  it("shows an error message when run request fails", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "server error" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What happened?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText("Request failed with status 500")).toBeInTheDocument();
  });
});
