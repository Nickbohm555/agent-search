export function formatLoadSuccessMessage(sourceType: string, documentsLoaded: number, chunksCreated: number): string {
  if (sourceType === "wiki") {
    return `Wiki load complete. Loaded ${documentsLoaded} documents and created ${chunksCreated} chunks.`;
  }

  return `Loaded ${documentsLoaded} documents and created ${chunksCreated} chunks.`;
}

export function formatRunSuccessMessage(subQueryCount: number): string {
  return `Run complete. ${subQueryCount} sub-queries processed.`;
}
