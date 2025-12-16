def train_predictor(df):
    df = df.rename(columns={"timestamp": "ds", "battery": "y"})
    model = Prophet()
    model.fit(df)
    return model


def forecast_battery(model, minutes=20):
    future = model.make_future_dataframe(periods=minutes, freq="min")
    out = model.predict(future)
    return out.tail(minutes)[["ds", "yhat"]]


def predict_failure_time(forecast, threshold=6.0):
    