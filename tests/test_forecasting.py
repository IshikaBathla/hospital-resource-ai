import pandas as pd

from backend.database import SessionLocal

from backend.services.forecasting_service import (
    load_patient_arrivals,
    prepare_hourly_data,
    train_and_evaluate_model,
    forecast_next_24_hours,
    estimate_resource_demand,
    prepare_department_hourly_data,
    train_department_forecast_models,
    forecast_department_next_24_hours,
    assess_bed_capacity,
    get_forecast_pressure
)


db = SessionLocal()

try:

    # ---------------------------------------------------------
    # 1. LOAD RAW PATIENT ARRIVAL DATA
    # ---------------------------------------------------------

    df = load_patient_arrivals(db)

    print("Raw records:", len(df))


    # ---------------------------------------------------------
    # 2. PREPARE HOURLY DATA
    # ---------------------------------------------------------

    hourly_df = prepare_hourly_data(df)

    print("Hourly records:", len(hourly_df))


    # ---------------------------------------------------------
    # 3. TRAIN + EVALUATE ML MODEL
    # ---------------------------------------------------------

    result = train_and_evaluate_model(
        hourly_df
    )

    print("Train size:", result["train_size"])
    print("Test size:", result["test_size"])
    print("MAE:", result["mae"])
    print("RMSE:", result["rmse"])


    # ---------------------------------------------------------
    # 4. GENERATE NEXT 24-HOUR OVERALL FORECAST
    # ---------------------------------------------------------

    last_timestamp = hourly_df["arrival_time"].max()

    forecast = forecast_next_24_hours(
        result["model"],
        last_timestamp + pd.Timedelta(hours=1)
    )

    print()
    print("Next 24-hour forecast:")
    print(forecast)


    # ---------------------------------------------------------
    # 5. ESTIMATE OVERALL RESOURCE DEMAND
    # ---------------------------------------------------------

    demand = estimate_resource_demand(
        forecast
    )

    print()
    print("Estimated resource demand:")
    print(demand)


    # ---------------------------------------------------------
    # 6. PREPARE DEPARTMENT-WISE HOURLY DATA
    # ---------------------------------------------------------

    department_hourly = prepare_department_hourly_data(
        df
    )

    print()
    print(
        "Department hourly records:",
        len(department_hourly)
    )


    # ---------------------------------------------------------
    # 7. TRAIN DEPARTMENT-WISE MODELS
    # ---------------------------------------------------------

    models = train_department_forecast_models(
        department_hourly
    )

    print(
        "Departments:",
        list(models.keys())
    )


    # ---------------------------------------------------------
    # 8. GENERATE DEPARTMENT-WISE 24-HOUR FORECAST
    # ---------------------------------------------------------

    department_forecast = forecast_department_next_24_hours(
        models,
        last_timestamp + pd.Timedelta(hours=1)
    )

    print()
    print("Department-wise 24-hour forecast:")
    print(department_forecast)


    # ---------------------------------------------------------
    # 9. ASSESS CURRENT BED CAPACITY
    # ---------------------------------------------------------

    capacity_assessment = assess_bed_capacity(
        db,
        department_forecast
    )

    print()
    print("Bed capacity assessment:")

    for item in capacity_assessment:
        print(item)


    # ---------------------------------------------------------
    # 10. GENERATE FORECAST PRESSURE SIGNAL
    # ---------------------------------------------------------

    forecast_pressure = get_forecast_pressure(
        db,
        department_forecast
    )

    print()
    print("Forecast pressure:")

    for item in forecast_pressure:
        print(item)


finally:

    db.close()