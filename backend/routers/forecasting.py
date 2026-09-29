from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import pandas as pd

from backend.database import get_db
from backend.services.forecasting_service import (
    load_patient_arrivals,
    prepare_hourly_data,
    train_and_evaluate_model,
    forecast_next_24_hours,
    estimate_resource_demand,
    prepare_department_hourly_data,
    train_department_forecast_models,
    forecast_department_next_24_hours,
    assess_bed_capacity
)

router = APIRouter(
    prefix="/forecasting",
    tags=["Forecasting"]
)


@router.get("/arrival")
def get_arrival_forecast(
    db: Session = Depends(get_db)
):
    df = load_patient_arrivals(db)

    if df.empty:
        return {
            "status": "no_data",
            "message": "No patient arrival data available"
        }

    hourly_df = prepare_hourly_data(df)

    result = train_and_evaluate_model(hourly_df)

    last_timestamp = hourly_df["arrival_time"].max()

    forecast = forecast_next_24_hours(
        result["model"],
        last_timestamp + pd.Timedelta(hours=1)
    )

    demand = estimate_resource_demand(forecast)

    return {
        "status": "success",
        "model": "RandomForestRegressor",
        "mae": result["mae"],
        "rmse": result["rmse"],
        "train_size": result["train_size"],
        "test_size": result["test_size"],
        "forecast": forecast.to_dict(orient="records"),
        "resource_demand": demand
    }


@router.get("/department")
def get_department_forecast(
    db: Session = Depends(get_db)
):
    df = load_patient_arrivals(db)

    if df.empty:
        return {
            "status": "no_data",
            "message": "No patient arrival data available"
        }

    department_hourly = prepare_department_hourly_data(df)

    models = train_department_forecast_models(
        department_hourly
    )

    last_timestamp = df["arrival_time"].max()

    forecast = forecast_department_next_24_hours(
        models,
        last_timestamp + pd.Timedelta(hours=1)
    )

    return {
        "status": "success",
        "departments": list(models.keys()),
        "forecast": forecast.to_dict(orient="records")
    }


@router.get("/capacity")
def get_bed_capacity_assessment(
    db: Session = Depends(get_db)
):
    df = load_patient_arrivals(db)

    if df.empty:
        return {
            "status": "no_data",
            "message": "No patient arrival data available"
        }

    department_hourly = prepare_department_hourly_data(df)

    models = train_department_forecast_models(
        department_hourly
    )

    last_timestamp = df["arrival_time"].max()

    department_forecast = forecast_department_next_24_hours(
        models,
        last_timestamp + pd.Timedelta(hours=1)
    )

    capacity = assess_bed_capacity(
        db,
        department_forecast
    )

    return {
        "status": "success",
        "capacity_assessment": capacity
    }