import { RuntimeAgentRunResponse } from "../../utils/api";

interface ProgressHistoryProps {
  runDetails: RuntimeAgentRunResponse | null;
}

function formatTimelineDetails(details: Record<string, unknown>): string {
  const entries = Object.entries(details);
  if (entries.length === 0) {
    return "";
  }

  return entries
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => {
      if (Array.isArray(value)) {
        return `${key}=${value.map((item) => String(item)).join(", ")}`;
      }
      if (value && typeof value === "object") {
        return `${key}=${JSON.stringify(value)}`;
      }
      return `${key}=${String(value)}`;
    })
    .join(" | ");
}

export function ProgressHistory({ runDetails }: ProgressHistoryProps) {
  const timeline = runDetails?.graph_state?.timeline ?? [];
  const currentTimelineIndex = timeline.length > 0 ? timeline.length - 1 : -1;

  return (
    <div className="progress-history" data-testid="progress-history-region">
      <h3>Progress History</h3>
      {runDetails ? (
        <>
          <div className="readout-group">
            <h4 className="readout-group-title">Timeline</h4>
            {timeline.length ? (
              <ol data-testid="timeline-list">
                {timeline.map((entry, index) => (
                  <li
                    key={`${entry.step}-${index}`}
                    className={`timeline-item ${index === currentTimelineIndex ? "timeline-item-current" : ""}`}
                    data-current-step={index === currentTimelineIndex ? "true" : "false"}
                  >
                    <p>
                      <strong>{entry.step}</strong>: {entry.status}
                    </p>
                    {Object.keys(entry.details).length > 0 ? (
                      <p className="timeline-details">{formatTimelineDetails(entry.details)}</p>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p data-testid="timeline-empty">No graph timeline available.</p>
            )}
          </div>

          <div className="readout-group">
            <h4 className="readout-group-title">Sub-queries</h4>
            {runDetails.sub_queries.length ? (
              <ol data-testid="subquery-list">
                {runDetails.sub_queries.map((subQuery) => {
                  const assignment = runDetails.tool_assignments.find((item) => item.sub_query === subQuery);
                  const toolLabel = assignment ? assignment.tool : "unassigned";
                  return (
                    <li key={subQuery}>
                      {subQuery} ({toolLabel})
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p data-testid="subquery-empty">No sub-queries were returned.</p>
            )}
          </div>

          <div className="readout-group">
            <h4 className="readout-group-title">Retrieval</h4>
            {runDetails.retrieval_results.length ? (
              <ol data-testid="retrieval-list">
                {runDetails.retrieval_results.map((retrieval) => {
                  if (retrieval.tool === "internal") {
                    return (
                      <li key={`${retrieval.sub_query}-${retrieval.tool}`}>
                        {retrieval.sub_query}: internal results {retrieval.internal_results.length}
                      </li>
                    );
                  }

                  return (
                    <li key={`${retrieval.sub_query}-${retrieval.tool}`}>
                      <p>
                        {retrieval.sub_query}: opened {retrieval.opened_urls.length} web page
                        {retrieval.opened_urls.length === 1 ? "" : "s"}
                      </p>
                      {retrieval.opened_urls.length ? (
                        <ul className="retrieval-url-list" data-testid="retrieval-opened-urls">
                          {retrieval.opened_urls.map((url) => (
                            <li key={url} className="retrieval-url-item">
                              {url}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p data-testid="retrieval-empty">No retrieval results were returned.</p>
            )}
          </div>

          <div className="readout-group">
            <h4 className="readout-group-title">Validation</h4>
            {runDetails.validation_results.length ? (
              <ol data-testid="validation-list">
                {runDetails.validation_results.map((validation) => (
                  <li key={`${validation.sub_query}-${validation.tool}`}>
                    <p>
                      {validation.sub_query}: {validation.status} after {validation.attempts} attempt
                      {validation.attempts === 1 ? "" : "s"}
                    </p>
                    {validation.follow_up_actions.length ? (
                      <p className="validation-follow-up">
                        follow-up: {validation.follow_up_actions.join(", ")}
                      </p>
                    ) : null}
                    {validation.attempt_trace.length ? (
                      <ul className="validation-attempt-list" data-testid="validation-attempt-trace">
                        {validation.attempt_trace.map((attempt) => (
                          <li key={`${validation.sub_query}-attempt-${attempt.attempt}`} className="validation-attempt-item">
                            attempt {attempt.attempt}: {attempt.sufficient ? "sufficient" : "insufficient"} | internal{" "}
                            {attempt.internal_result_count} | opened {attempt.opened_page_count}
                            {attempt.follow_up_action ? ` | next ${attempt.follow_up_action}` : ""}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p data-testid="validation-empty">No validation results were returned.</p>
            )}
          </div>
        </>
      ) : (
        <p>No run details yet.</p>
      )}
    </div>
  );
}
