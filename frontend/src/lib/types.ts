/**
 * TypeScript mirrors of the FastAPI response schemas (see
 * `src/volatility_platform/api/schemas.py`). Kept in sync by hand for a
 * project this size; a larger one would generate these from the OpenAPI
 * schema (FastAPI serves one at /openapi.json) to guarantee drift can't happen.
 */

export interface TickerInfo {
  ticker: string;
  latest_trading_date: string | null;
  bar_count: number;
}

export interface TickerWithLatestPrediction extends TickerInfo {
  latestPrediction: PredictionResponse | null;
}

export interface PredictionResponse {
  ticker: string;
  horizon_days: number;
  as_of_date: string;
  current_price: number;
  predicted_volatility: number;
  annualized_volatility_pct: number;
  expected_move_pct: number;
  expected_move_dollars: number;
  expected_price_range_low: number;
  expected_price_range_high: number;
  model_name: string;
  model_version: string;
  generated_at: string;
}

export interface TrainResponse {
  model_name: string;
  version: string;
  algorithm: string;
  horizon_days: number;
  trained_at: string;
  training_samples: number;
  metrics: Record<string, number>;
  feature_names: string[];
  candidate_metrics: Record<string, { rmse: number; mae: number; r2: number }>;
}

export type ModelInfoResponse = TrainResponse;

export interface HealthResponse {
  status: string;
  mongodb_connected: boolean;
}

export interface ApiErrorBody {
  detail: string;
}
