import pandas as pd

from sqlalchemy import text
from sqlalchemy.orm import Session

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def load_patient_arrivals(db: Session):
    query = text("""
        SELECT arrival_time, emergency_level, department
        FROM patient_arrivals
        ORDER BY arrival_time
    """)

    result = db.execute(query).mappings().all()

    if not result:
        return pd.DataFrame()

    df = pd.DataFrame(result)

    df["arrival_time"] = pd.to_datetime(df["arrival_time"])

    return df


def prepare_hourly_data(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df["arrival_time"] = pd.to_datetime(
        df["arrival_time"]
    )

    hourly = (
        df.set_index("arrival_time")
        .resample("1h")
        .size()
        .reset_index(name="arrival_count")
    )

    hourly["hour"] = (
        hourly["arrival_time"].dt.hour
    )

    hourly["day_of_week"] = (
        hourly["arrival_time"].dt.dayofweek
    )

    hourly["is_weekend"] = (
        hourly["day_of_week"] >= 5
    ).astype(int)

    return hourly


def train_arrival_forecast_model(
    hourly_df: pd.DataFrame
):
    if hourly_df.empty:
        raise ValueError(
            "No historical data available"
        )

    features = [
        "hour",
        "day_of_week",
        "is_weekend"
    ]

    X = hourly_df[features]
    y = hourly_df["arrival_count"]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X, y)

    return model


def train_and_evaluate_model(
    hourly_df: pd.DataFrame
):
    if len(hourly_df) < 10:
        raise ValueError(
            "Not enough historical data"
        )

    features = [
        "hour",
        "day_of_week",
        "is_weekend"
    ]

    # Time-series split:
    # first 80% = training
    # last 20% = testing
    split_index = int(
        len(hourly_df) * 0.8
    )

    train_df = hourly_df.iloc[
        :split_index
    ]

    test_df = hourly_df.iloc[
        split_index:
    ]

    X_train = train_df[features]
    y_train = train_df["arrival_count"]

    X_test = test_df[features]
    y_test = test_df["arrival_count"]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = mean_squared_error(
        y_test,
        predictions
    ) ** 0.5

    return {
        "model": model,
        "mae": mae,
        "rmse": rmse,
        "train_size": len(train_df),
        "test_size": len(test_df)
    }


def forecast_next_24_hours(
    model,
    start_time
):
    future_data = pd.date_range(
        start=start_time,
        periods=24,
        freq="1h"
    )

    future_df = pd.DataFrame({
        "arrival_time": future_data
    })

    future_df["hour"] = (
        future_df["arrival_time"].dt.hour
    )

    future_df["day_of_week"] = (
        future_df["arrival_time"].dt.dayofweek
    )

    future_df["is_weekend"] = (
        future_df["day_of_week"] >= 5
    ).astype(int)

    features = [
        "hour",
        "day_of_week",
        "is_weekend"
    ]

    future_df["predicted_arrivals"] = (
        model.predict(
            future_df[features]
        )
    )

    future_df["predicted_arrivals"] = (
        future_df["predicted_arrivals"]
        .clip(lower=0)
        .round(2)
    )

    return future_df[
        [
            "arrival_time",
            "predicted_arrivals"
        ]
    ]


def estimate_resource_demand(
    forecast_df: pd.DataFrame
):
    if forecast_df.empty:
        return {
            "total_predicted_arrivals": 0.0,
            "peak_predicted_arrivals": 0.0
        }

    total_predicted = (
        forecast_df[
            "predicted_arrivals"
        ].sum()
    )

    peak_predicted = (
        forecast_df[
            "predicted_arrivals"
        ].max()
    )

    return {
        "total_predicted_arrivals": float(
            round(total_predicted, 2)
        ),
        "peak_predicted_arrivals": float(
            round(peak_predicted, 2)
        )
    }


# --------------------------------
# Department-wise Forecasting
# --------------------------------

def prepare_department_hourly_data(
    df: pd.DataFrame
):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df["arrival_time"] = pd.to_datetime(
        df["arrival_time"]
    )

    department_hourly = (
        df.groupby(
            [
                pd.Grouper(
                    key="arrival_time",
                    freq="1h"
                ),
                "department"
            ]
        )
        .size()
        .reset_index(
            name="arrival_count"
        )
    )

    department_hourly["hour"] = (
        department_hourly[
            "arrival_time"
        ].dt.hour
    )

    department_hourly["day_of_week"] = (
        department_hourly[
            "arrival_time"
        ].dt.dayofweek
    )

    department_hourly["is_weekend"] = (
        department_hourly[
            "day_of_week"
        ] >= 5
    ).astype(int)

    return department_hourly


def train_department_forecast_models(
    department_hourly_df: pd.DataFrame
):
    if department_hourly_df.empty:
        raise ValueError(
            "No department historical data available"
        )

    features = [
        "hour",
        "day_of_week",
        "is_weekend"
    ]

    models = {}

    departments = sorted(
        department_hourly_df[
            "department"
        ].unique()
    )

    for department in departments:

        department_df = (
            department_hourly_df[
                department_hourly_df[
                    "department"
                ] == department
            ]
        )

        X = department_df[features]

        y = department_df[
            "arrival_count"
        ]

        model = RandomForestRegressor(
            n_estimators=100,
            random_state=42
        )

        model.fit(
            X,
            y
        )

        models[department] = model

    return models


def forecast_department_next_24_hours(
    models,
    start_time
):
    future_data = pd.date_range(
        start=start_time,
        periods=24,
        freq="1h"
    )

    future_base = pd.DataFrame({
        "arrival_time": future_data
    })

    future_base["hour"] = (
        future_base[
            "arrival_time"
        ].dt.hour
    )

    future_base["day_of_week"] = (
        future_base[
            "arrival_time"
        ].dt.dayofweek
    )

    future_base["is_weekend"] = (
        future_base[
            "day_of_week"
        ] >= 5
    ).astype(int)

    features = [
        "hour",
        "day_of_week",
        "is_weekend"
    ]

    forecasts = []

    for department, model in models.items():

        department_forecast = (
            future_base[
                [
                    "arrival_time",
                    "hour",
                    "day_of_week",
                    "is_weekend"
                ]
            ].copy()
        )

        department_forecast[
            "department"
        ] = department

        department_forecast[
            "predicted_arrivals"
        ] = model.predict(
            department_forecast[
                features
            ]
        )

        department_forecast[
            "predicted_arrivals"
        ] = (
            department_forecast[
                "predicted_arrivals"
            ]
            .clip(lower=0)
            .round(2)
        )

        forecasts.append(
            department_forecast[
                [
                    "arrival_time",
                    "department",
                    "predicted_arrivals"
                ]
            ]
        )

    if not forecasts:
        return pd.DataFrame()

    return pd.concat(
        forecasts,
        ignore_index=True
    )


# --------------------------------
# Bed Capacity Assessment
# --------------------------------

def assess_bed_capacity(
    db: Session,
    department_forecast: pd.DataFrame
):
    if department_forecast.empty:
        return []

    result = []

    # Current hospital bed wards
    supported_wards = [
        "ICU",
        "General"
    ]

    for department in supported_wards:

        forecast_df = (
            department_forecast[
                department_forecast[
                    "department"
                ] == department
            ]
        )

        if forecast_df.empty:
            predicted_demand = 0.0
            peak_hourly_demand = 0.0
        else:
            predicted_demand = float(
                forecast_df[
                    "predicted_arrivals"
                ].sum()
            )

            peak_hourly_demand = float(
                forecast_df[
                    "predicted_arrivals"
                ].max()
            )

        # Total beds
        total_query = text("""
            SELECT COUNT(*) AS total_beds
            FROM beds
            WHERE LOWER(ward) = LOWER(:ward)
        """)

        total_row = db.execute(
            total_query,
            {
                "ward": department
            }
        ).mappings().first()

        total_beds = int(
            total_row["total_beds"] or 0
        )

        # Currently available beds
        available_query = text("""
            SELECT COUNT(*) AS available_beds
            FROM beds
            WHERE LOWER(ward) = LOWER(:ward)
              AND status = 'available'
        """)

        available_row = db.execute(
            available_query,
            {
                "ward": department
            }
        ).mappings().first()

        available_beds = int(
            available_row["available_beds"] or 0
        )

        occupied_beds = (
            total_beds -
            available_beds
        )

        # Forecast is a demand signal,
        # not a direct bed-shortage count.
        if available_beds == 0:
            status = "no_current_capacity"

        elif (
            peak_hourly_demand >
            available_beds
        ):
            status = "capacity_pressure"

        else:
            status = "capacity_available"

        result.append({
            "department": department,
            "predicted_24h_arrivals": round(
                predicted_demand,
                2
            ),
            "peak_hourly_demand": round(
                peak_hourly_demand,
                2
            ),
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "status": status
        })

    return result
def get_forecast_pressure(
    db: Session,
    department_forecast: pd.DataFrame
):
    """
    Converts ML forecast + current bed state
    into a simple resource pressure signal.

    ML only predicts demand.
    It does NOT allocate resources.
    """

    if department_forecast.empty:
        return []

    pressure = []

    supported_wards = ["ICU", "General"]

    for department in supported_wards:

        forecast_df = department_forecast[
            department_forecast["department"] == department
        ]

        if forecast_df.empty:
            continue

        predicted_24h = float(
            forecast_df["predicted_arrivals"].sum()
        )

        peak_hourly = float(
            forecast_df["predicted_arrivals"].max()
        )

        result = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_beds,
                    COUNT(*) FILTER (
                        WHERE status = 'available'
                    ) AS available_beds
                FROM beds
                WHERE LOWER(ward) = LOWER(:ward)
            """),
            {"ward": department}
        ).mappings().first()

        total_beds = int(result["total_beds"] or 0)
        available_beds = int(result["available_beds"] or 0)
        occupied_beds = total_beds - available_beds

        if available_beds == 0:
            status = "critical_pressure"

        elif peak_hourly > available_beds:
            status = "capacity_pressure"

        else:
            status = "normal"

        pressure.append({
            "department": department,
            "predicted_24h_arrivals": round(
                predicted_24h, 2
            ),
            "peak_hourly_demand": round(
                peak_hourly, 2
            ),
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "status": status
        })

    return pressure