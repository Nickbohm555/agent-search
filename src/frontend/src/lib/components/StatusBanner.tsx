import { RequestState } from "../types";

interface StatusBannerProps {
  state: RequestState;
  message: string;
  testId: string;
  label: string;
}

/**
 * Called by `App` to render one load/run status readout with deterministic
 * state labeling and optional processing indicator during in-flight work.
 */
export function StatusBanner({ state, message, testId, label }: StatusBannerProps) {
  const stateLabel = state === "loading" ? "PROCESSING" : state.toUpperCase();
  const isLoading = state === "loading";

  return (
    <div
      className={`status readout-block status-${state}`}
      aria-live="polite"
      role="status"
      data-testid={testId}
      data-processing={isLoading ? "true" : "false"}
    >
      <p className="readout-label">{label}</p>
      <p className="readout-value">
        <span className={`status-chip ${isLoading ? "status-chip-loading" : ""}`}>{stateLabel}</span>
        <span>{message}</span>
      </p>
    </div>
  );
}
