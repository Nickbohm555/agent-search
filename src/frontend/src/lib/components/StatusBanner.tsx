import { RequestState } from "../types";

interface StatusBannerProps {
  state: RequestState;
  message: string;
  testId: string;
  label: string;
  busy?: boolean;
}

export function StatusBanner({ state, message, testId, label, busy = false }: StatusBannerProps) {
  return (
    <div
      className={`status readout-block status-${state}`}
      aria-live="polite"
      aria-atomic="true"
      aria-busy={busy}
      data-busy-indicator={busy ? "active" : "idle"}
      role="status"
      data-testid={testId}
    >
      <p className="readout-label status-label-row">
        <span>{label}</span>
        <span className={`status-signal ${busy ? "status-signal-active" : ""}`} aria-hidden="true" />
      </p>
      <p className="readout-value">{message}</p>
    </div>
  );
}
