export function formatLoadSuccessMessage(documentsLoaded: number, chunksCreated: number): string {
  return `Loaded ${documentsLoaded} documents and created ${chunksCreated} chunks.`;
}

export function formatRunSuccessMessage(subQueryCount: number): string {
  return `Run complete. ${subQueryCount} sub-queries processed.`;
}

export function formatHeartbeatMessage(step: string, status: "started" | "completed"): string {
  const stepLabel = step.replace(/_/g, " ");
  const verb = status === "started" ? "in progress" : "completed";
  return `Step update: ${stepLabel} ${verb}.`;
}
