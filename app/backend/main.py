from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.v1.routes import routers as v1_routers

app = FastAPI(
    title="FlightTracr API",
    version="0.0.1",
    description="API for parsing boarding passes and managing user data.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_routers, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the FlightTracr API. Go to /docs for API documentation."}


@app.get("/healthz", summary="Health check endpoint", tags=["Health"])
async def healthz():
    """
    Health check endpoint to indicate if the application is running.
    Returns a 200 OK status with a simple message.
    """
    return {"status": "healthy"}


@app.get("/readz", summary="Readiness check endpoint", tags=["Health"])
async def readz():
    """
    Readiness check endpoint to indicate if the application is ready to serve requests.
    Returns a 200 OK status with a simple message.
    """
    return {"status": "ready"}
