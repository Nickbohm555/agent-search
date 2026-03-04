import { useMemo } from "react";
import { API_BASE_URL } from "./utils/config";

export default function App() {
  const sampleK = useMemo(() => 5, []);

  return (
    <main className="container">
      <h1>Agent Search Scaffold</h1>
      <p>Frontend: React + TypeScript + Vite</p>
      <p>Backend: FastAPI + Postgres + Alembic + pgvector</p>
      <p>API base: <code>{API_BASE_URL}</code></p>
      <p>Health check: <code>{API_BASE_URL}/api/health</code></p>
      <p>Similarity default k: <code>{sampleK}</code></p>
    </main>
  );
}
