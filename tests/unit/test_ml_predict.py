from datetime import date

from volatility_platform.domain.models import Ticker
from volatility_platform.features.pipeline import build_feature_frame
from volatility_platform.ml.predict import predict_volatility
from volatility_platform.ml.train import train_model

from ..conftest import synthetic_ohlcv


class TestPredictVolatility:
    def test_produces_valid_prediction_with_correct_fields(self) -> None:
        ohlcv = synthetic_ohlcv(n_days=150)
        train_frame = build_feature_frame(ohlcv, horizon=5, include_target=True)
        model, metadata = train_model(
            train_frame, model_name="volatility_predictor", horizon_days=5
        )

        infer_frame = build_feature_frame(ohlcv, horizon=5, include_target=False)
        current_price = float(ohlcv["close"].iloc[-1])

        prediction = predict_volatility(
            model=model,
            metadata=metadata,
            feature_frame=infer_frame,
            ticker=Ticker("AAPL"),
            current_price=current_price,
        )

        assert prediction.ticker.symbol == "AAPL"
        assert prediction.horizon_days == 5
        assert prediction.current_price == current_price
        assert prediction.model_name == "volatility_predictor"
        assert prediction.model_version == metadata.version
        assert prediction.predicted_volatility >= 0.0
        assert isinstance(prediction.as_of_date, date)

    def test_predicted_volatility_never_negative_even_for_linear_model(self) -> None:
        # Which candidate wins CV is data-dependent; assert the non-negativity
        # invariant holds regardless of which one was actually selected.
        ohlcv = synthetic_ohlcv(n_days=150, seed=7)
        train_frame = build_feature_frame(ohlcv, horizon=5, include_target=True)
        model, metadata = train_model(
            train_frame, model_name="volatility_predictor", horizon_days=5
        )
        infer_frame = build_feature_frame(ohlcv, horizon=5, include_target=False)

        prediction = predict_volatility(
            model=model,
            metadata=metadata,
            feature_frame=infer_frame,
            ticker=Ticker("MSFT"),
            current_price=350.0,
        )
        assert prediction.predicted_volatility >= 0.0
