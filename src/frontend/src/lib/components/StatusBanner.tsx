import { RequestState } from "../types";

interface StatusBannerProps {
  state: RequestState;
  message: string;
  testId: string;
  label: string;
}

export function StatusBanner({ state, message, testId, label }: StatusBannerProps) {
  return (
    <div className={`status readout-block status-${state}`} aria-live="polite" role="status" data-testid={testId}>
      <p className="readout-label">{label}</p>
      <p className="readout-value">{message}</p>
    </div>
  );
}
