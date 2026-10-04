import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.database import initialize_database
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.patients import (
    router as patient_router
)

from backend.routers.beds import (
    router as bed_router
)

from backend.routers.staff import (
    router as staff_router
)

from backend.routers.equipment import (
    router as equipment_router
)

from backend.routers.assignments import (
    router as assignment_router
)

from backend.routers.recommendations import (
    router as recommendation_router
)

from backend.routers.procedures import (
    router as procedure_router
)

from backend.services.background_service import (
    background_resource_monitor
)

from backend.routers.simulation import (
    router as simulation_router
)

from backend.routers.optimization import (
    router as optimization_router
)

from backend.routers import forecasting

from backend.models.recommendation_outcome import (
    RecommendationOutcome
)

from backend.routers import outcomes

from backend.routers import what_if

from backend.routers.strategy import (
    router as strategy_router
)

from backend.routers import auth

from backend.routers.alerts import (
    router as alert_router
)


# =========================================================
# APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Initialize database
    initialize_database()

    # Start background monitor
    monitor_task = asyncio.create_task(
        background_resource_monitor()
    )

    print(
        "Background resource monitor started."
    )

    try:

        yield

    finally:

        monitor_task.cancel()

        try:

            await monitor_task

        except asyncio.CancelledError:

            pass

        print(
            "Background resource monitor stopped."
        )


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="AI Hospital Resource Coordination System",

    description=(
        "Hospital resource allocation, "
        "constraint-aware recommendations "
        "and human-in-the-loop decisions."
    ),

    version="1.0.0",

    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(
    patient_router
)

app.include_router(
    bed_router
)

app.include_router(
    staff_router
)

app.include_router(
    equipment_router
)

app.include_router(
    assignment_router
)

app.include_router(
    recommendation_router
)

app.include_router(
    procedure_router
)

app.include_router(
    simulation_router
)

app.include_router(
    optimization_router
)

app.include_router(
    forecasting.router
)

app.include_router(
    outcomes.router
)

app.include_router(
    what_if.router
)

app.include_router(
    strategy_router
)

app.include_router(
    auth.router
)

app.include_router(
    alert_router
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def root():

    return {
        "message": "AI Hospital Resource Coordination API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/hello")
def hello():

    return {
        "message": "Hello Hospital"
    }


@app.get("/db-test")
def db_test():

    return {
        "database": "connected"
    }