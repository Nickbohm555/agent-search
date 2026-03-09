import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

    expect(await screen.findByRole("option", { name: "All Sources" })).toBeInTheDocument();
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

    expect(await screen.findByRole("option", { name: "All Sources" })).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: "Geopolitics (loaded)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "NATO" })).toBeInTheDocument();
  });
});

describe("App run query flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows ordered stage rail and progressive status updates while polling", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-1", run_id: "run-1", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            run_id: "run-1",
            status: "running",
            message: "Stage completed: subquestions_ready",
            stage: "subquestions_ready",
            stages: [],
            decomposition_sub_questions: ["First subquestion?"],
            sub_qa: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            run_id: "run-1",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["First subquestion?"],
            sub_qa: [],
            output: "NATO is a military alliance.",
            result: {
              main_question: "What is NATO?",
              sub_qa: [],
              output: "NATO is a military alliance.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What is NATO?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();
    expect(await screen.findByText("Run status: Stage completed: subquestions_ready")).toBeInTheDocument();
    expect(getStageStatusText("decompose")).toContain("in_progress");
    expect(getStageStatusText("search")).toContain("pending");
    expect(screen.getByRole("heading", { name: "Decompose" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Decomposed subquestions" })).toBeInTheDocument();
    expect(screen.getByText("First subquestion?")).toBeInTheDocument();
    expect(screen.getByText("Subquestion count: 1")).toBeInTheDocument();
    expect(screen.getByText("Ends with ?: yes")).toBeInTheDocument();
    expect(screen.getByText("Dedupe: pass")).toBeInTheDocument();
    expect(screen.getByText("No answer yet.")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Run status: Completed.")).toBeInTheDocument();
    });
    expect(getStageStatusText("decompose")).toContain("completed");
    expect(getStageStatusText("final")).toContain("completed");
    expect(screen.getByText("NATO is a military alliance.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Main question" })).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/agents/run-async",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "What is NATO?" }),
        }),
      );
    });

    const stageLabels = screen.getAllByText(/decompose|expand|search|rerank|answer|final/, {
      selector: ".stage-name",
    });
    expect(stageLabels.map((item) => item.textContent)).toEqual([
      "decompose",
      "expand",
      "search",
      "rerank",
      "answer",
      "final",
    ]);
  });

  it("renders main question and expandable subquestion details from async final result", async () => {
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
            job_id: "job-2",
            run_id: "run-2",
            status: "running",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-2",
            run_id: "run-2",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["Which treaty created NATO?"],
            sub_qa: [
              {
                sub_question: "Which treaty created NATO?",
                sub_answer: "The North Atlantic Treaty created NATO.",
                sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
                tool_call_input: "{\"query\":\"NATO founding treaty\"}",
              },
            ],
            output: "NATO was formed in 1949.",
            result: {
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
            },
            error: null,
            cancel_requested: false,
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

    const subanswersHeading = screen.getByRole("heading", { name: "Subquestions & subanswers" });
    const subanswersSection = subanswersHeading.closest("section");
    expect(subanswersSection).toBeTruthy();
    const firstSubQuestion = within(subanswersSection as HTMLElement).getByText("Which treaty created NATO?");
    fireEvent.click(firstSubQuestion);

    expect(screen.getByText(/The North Atlantic Treaty created NATO\./)).toBeInTheDocument();
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

function getStageStatusText(stageName: string): string {
  const stageLabel = screen.getByText(stageName);
  const stageItem = stageLabel.closest("li");
  expect(stageItem).toBeTruthy();
  return stageItem?.textContent ?? "";
}
