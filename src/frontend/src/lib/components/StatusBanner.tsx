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
      role="status"
      data-testid={testId}
    >
      <p className="readout-label">{label}</p>
      <p className="readout-value">{message}</p>
    </div>
  );
}
