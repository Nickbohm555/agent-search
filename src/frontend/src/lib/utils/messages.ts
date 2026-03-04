export function formatLoadSuccessMessage(documentsLoaded: number, chunksCreated: number): string {
  return `Loaded ${documentsLoaded} documents and created ${chunksCreated} chunks.`;
}

export function formatRunSuccessMessage(subQueryCount: number): string {
  return `Run complete. ${subQueryCount} sub-queries processed.`;
}
