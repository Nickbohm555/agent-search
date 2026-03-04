import { InternalDocumentInput } from "../utils/api";

export const SAMPLE_INTERNAL_DOCUMENTS: InternalDocumentInput[] = [
  {
    title: "Product Notes",
    content: "Agent Search loads internal data and can retrieve chunked context.",
    source_ref: "demo://product-notes",
  },
  {
    title: "Roadmap",
    content: "The orchestration flow decomposes user queries and synthesizes final answers.",
    source_ref: "demo://roadmap",
  },
];
