import { RuntimeAgentRunResponse } from "../../utils/api";

interface ProgressHistoryProps {
  runDetails: RuntimeAgentRunResponse | null;
}

export function ProgressHistory({ runDetails }: ProgressHistoryProps) {
  return (
    <div className="progress-history" data-testid="progress-history-region">
      <h3>Progress History</h3>
      {runDetails ? (
        <>
          <div className="readout-group">
            <h4 className="readout-group-title">Timeline</h4>
            {runDetails.graph_state?.timeline?.length ? (
              <ol data-testid="timeline-list">
                {runDetails.graph_state.timeline.map((entry, index) => (
                  <li key={`${entry.step}-${index}`}>
                    <strong>{entry.step}</strong>: {entry.status}
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
            <h4 className="readout-group-title">Validation</h4>
            {runDetails.validation_results.length ? (
              <ol data-testid="validation-list">
                {runDetails.validation_results.map((validation) => (
                  <li key={`${validation.sub_query}-${validation.tool}`}>
                    {validation.sub_query}: {validation.status}
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
