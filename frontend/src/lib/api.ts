import type {
  ApiErrorBody,
  HealthResponse,
  ModelInfoResponse,
  PredictionResponse,
  TickerInfo,
  TrainResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    // Dashboard data (tickers, predictions, model state) changes often and
    // is never something we want a stale cached copy of.
    cache: "no-store",
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(body?.detail ?? response.statusText, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),

  getTickers: () => request<TickerInfo[]>("/tickers"),

  predict: (ticker: string) =>
    request<PredictionResponse>("/predict", {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }),

  getPredictionHistory: (ticker: string, limit = 50) =>
    request<PredictionResponse[]>(`/predictions/${ticker}?limit=${limit}`),

  train: (tickers: string[] | null, horizonDays = 5) =>
    request<TrainResponse>("/train", {
      method: "POST",
      body: JSON.stringify({ tickers, horizon_days: horizonDays }),
    }),

  getModelInfo: () => request<ModelInfoResponse>("/model-info"),
};
