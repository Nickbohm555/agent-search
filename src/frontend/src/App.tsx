import { API_BASE_URL } from "./utils/config";

export default function App() {
  return (
    <main className="container">
      <h1>Agent Search Scaffold</h1>
      <p>Frontend and backend are scaffolded only.</p>
      <p>API base: <code>{API_BASE_URL}</code></p>
      <p>Next step: implement specs and tests per plan mode.</p>
    </main>
  );
}
