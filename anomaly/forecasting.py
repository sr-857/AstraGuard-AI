import pandas as pd  # type: ignore
from prophet import Prophet  # type: ignore
from typing import Optional


def train_predictor(df: pd.DataFrame) -> Prophet:
    """
    Train a Prophet model on the battery data.

    Args:
        df: DataFrame containing 'timestamp' and 'battery' columns.

    Returns:
        Trained Prophet model.
    """
    # Prepare data for Prophet (requires 'ds' and 'y' columns)
    df_prophet = df.rename(columns={"timestamp": "ds", "battery": "y"})

    model = Prophet()
    model.fit(df_prophet)
    return model


def forecast_battery(model: Prophet, minutes: int = 20) -> pd.DataFrame:
    """
    Forecast battery levels for the next 'minutes'.

    Args:
        model: Trained Prophet model.
        minutes: Number of minutes to forecast.

    Returns:
        DataFrame with 'ds' (timestamp) and 'yhat' (predicted battery level).
    """
    future = model.make_future_dataframe(periods=minutes, freq="min")
    forecast = model.predict(future)
    return forecast.tail(minutes)[["ds", "yhat"]]


def predict_failure_time(forecast: pd.DataFrame, threshold: float = 6.0) -> Optional[pd.Timestamp]:
    """
    Predict the time when the battery level will fall below the threshold.

    Args:
        forecast: DataFrame with 'ds' and 'yhat' columns.
        threshold: Critical battery level.

    Returns:
        Timestamp of failure or None if no failure predicted.
    """
    # Filter for future predictions where yhat < threshold
    critical = forecast[forecast['yhat'] < threshold]

    if not critical.empty:
        return critical.iloc[0]['ds']

    return None
