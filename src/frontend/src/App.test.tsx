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

    expect(await screen.findByRole("heading", { name: "Main question" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Final answer" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Subquestions & subanswers" })).toBeInTheDocument();
    expect(await screen.findByText("NATO is a military alliance.")).toBeInTheDocument();
    expect(screen.getByText("No subquestions for this run.")).toBeInTheDocument();

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

  it("renders main question and expandable subquestion details from enriched response shape", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            output: "NATO was formed in 1949.",
            main_question: "When and why was NATO formed?",
            sub_qa: [
              {
                sub_question: "Which treaty created NATO?",
                sub_answer: "The North Atlantic Treaty created NATO.",
                sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
                tool_call_input: "{\"query\":\"NATO founding treaty\"}",
              },
            ],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "When and why was NATO formed?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByRole("heading", { name: "Main question" })).toBeInTheDocument();
    expect(screen.getAllByText("When and why was NATO formed?").length).toBeGreaterThan(0);
    expect(screen.getByText("NATO was formed in 1949.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Subquestions & subanswers" })).toBeInTheDocument();

    const firstSubQuestion = screen.getByText("Which treaty created NATO?");
    fireEvent.click(firstSubQuestion);

    expect(
      screen.getByText("NATO was established by the Washington Treaty in April 1949."),
    ).toBeInTheDocument();
    expect(screen.getByText('{"query":"NATO founding treaty"}')).toBeInTheDocument();
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
