import { forwardRef } from "react";
import { RequestState } from "../types";

interface StatusBannerProps {
  state: RequestState;
  message: string;
  testId: string;
  label: string;
  busy?: boolean;
}

export const StatusBanner = forwardRef<HTMLDivElement, StatusBannerProps>(function StatusBanner(
  { state, message, testId, label, busy = false },
  ref,
) {
  return (
    <div
      ref={ref}
      className={`status readout-block status-${state}`}
      aria-live="polite"
      aria-atomic="true"
      aria-busy={busy}
      data-busy-indicator={busy ? "active" : "idle"}
      role="status"
      tabIndex={-1}
      data-testid={testId}
    >
      <p className="readout-label status-label-row">
        <span>{label}</span>
        <span className={`status-signal ${busy ? "status-signal-active" : ""}`} aria-hidden="true" />
      </p>
      <p className="readout-value">{message}</p>
    </div>
  );
});
