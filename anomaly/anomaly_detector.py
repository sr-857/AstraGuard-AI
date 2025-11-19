
#!/usr/bin/env python3
import numpy as np
import pickle
import os
from sklearn.ensemble import IsolationForest

MODEL_PATH = os.path.join(os.path.dirname(__file__),"anomaly_if.pkl")

def synthesize_normal(n=1000):
    # generate synthetic normal telemetry: voltage, current, temp, gyro, wheel_speed
    volt = np.random.normal(7.9, 0.03, n)
    curr = np.random.normal(0.55, 0.01, n)
    temp = np.random.normal(24, 0.4, n)
    gyro = np.random.normal(0, 0.015, n)
    wheel = np.random.normal(480, 4, n)
    X = np.vstack([volt, curr, temp, gyro, wheel]).T
    return X

def train_and_save():
    X = synthesize_normal(2000)
    model = IsolationForest(contamination=0.01, random_state=42)
    model.fit(X)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print("Saved model to", MODEL_PATH)

def load_model():
    if not os.path.exists(MODEL_PATH):
        train_and_save()
    with open(MODEL_PATH,"rb") as f:
        return pickle.load(f)

def detect_anomaly(sample):
    # sample must be array-like [v, c, t, gyro, wheel]
    model = load_model()
    import numpy as np
    X = np.array(sample).reshape(1, -1)
    score = model.decision_function(X)[0]
    pred = model.predict(X)[0]  # -1 anomaly, 1 normal
    is_anom = (pred == -1)
    return bool(is_anom), float(score)

if __name__ == "__main__":
    train_and_save()
