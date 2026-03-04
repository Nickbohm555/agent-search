import { FormEvent } from "react";

interface QueryFormProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  isRunDisabled: boolean;
  isLoading: boolean;
}

export function QueryForm({ query, onQueryChange, onSubmit, isRunDisabled, isLoading }: QueryFormProps) {
  return (
    <form onSubmit={onSubmit}>
      <label htmlFor="query-input">Query</label>
      <textarea
        id="query-input"
        name="query"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        rows={3}
        placeholder="Ask a complex question..."
      />
      <button type="submit" disabled={isRunDisabled}>
        {isLoading ? "Running..." : "Run Agent"}
      </button>
    </form>
  );
}
