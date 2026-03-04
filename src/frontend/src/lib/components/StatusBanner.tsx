import { RequestState } from "../types";

interface StatusBannerProps {
  state: RequestState;
  message: string;
  testId: string;
}

export function StatusBanner({ state, message, testId }: StatusBannerProps) {
  return (
    <div className={`status status-${state}`} aria-live="polite" data-testid={testId}>
      {message}
    </div>
  );
}
