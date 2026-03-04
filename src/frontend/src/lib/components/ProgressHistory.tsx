import { RuntimeAgentGraphStep, RuntimeAgentRunResponse } from "../../utils/api";

interface ProgressHistoryProps {
  runDetails: RuntimeAgentRunResponse | null;
  streamedProgress: RuntimeAgentGraphStep[];
  streamedSubQueries: string[];
}

export function ProgressHistory({ runDetails, streamedProgress, streamedSubQueries }: ProgressHistoryProps) {
  const timeline = streamedProgress.length > 0 ? streamedProgress : runDetails?.graph_state?.timeline ?? [];
  const subQueries = streamedSubQueries.length > 0 ? streamedSubQueries : runDetails?.sub_queries ?? [];
  const toolAssignments = runDetails?.tool_assignments ?? [];
  const validationResults = runDetails?.validation_results ?? [];

  return (
    <div className="progress-history" data-testid="progress-history-region">
      <h3>Progress History</h3>
      {runDetails || streamedProgress.length > 0 || streamedSubQueries.length > 0 ? (
        <>
          <div className="readout-group">
            <h4 className="readout-group-title">Timeline</h4>
            {timeline.length ? (
              <ol data-testid="timeline-list">
                {timeline.map((entry, index) => (
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
            {subQueries.length ? (
              <ol data-testid="subquery-list">
                {subQueries.map((subQuery) => {
                  const assignment = toolAssignments.find((item) => item.sub_query === subQuery);
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
            {validationResults.length ? (
              <ol data-testid="validation-list">
                {validationResults.map((validation) => (
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
