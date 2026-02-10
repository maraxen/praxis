"""Core backend application for Praxis."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from praxis.backend.api import (
  auth,
  decks,
  discovery,
  hardware,
  machine_backends,
  machine_frontends,
  machines,
  outputs,
  protocols,
  resources,
  scheduler,
  workcell,
)
from praxis.backend.configure import PraxisConfiguration
from praxis.backend.core.asset_lock_manager import AssetLockManager
from praxis.backend.core.asset_manager import AssetManager
from praxis.backend.core.celery import celery_app, configure_celery_app
from praxis.backend.core.filesystem import FileSystem
from praxis.backend.core.orchestrator import Orchestrator
from praxis.backend.core.storage import StorageBackend, StorageFactory
from praxis.backend.core.workcell import Workcell
from praxis.backend.core.workcell_runtime import WorkcellRuntime
from praxis.backend.models.domain.deck import Deck, DeckDefinition
from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.resource import Resource
from praxis.backend.models.domain.workcell import Workcell
from praxis.backend.services.deck import DeckService
from praxis.backend.services.deck_type_definition import DeckTypeDefinitionService
from praxis.backend.services.discovery_service import DiscoveryService
from praxis.backend.services.machine import MachineService
from praxis.backend.services.machine_type_definition import MachineTypeDefinitionService
from praxis.backend.services.protocol_definition import ProtocolDefinitionCRUDService
from praxis.backend.services.resource import ResourceService
from praxis.backend.services.resource_type_definition import ResourceTypeDefinitionService
from praxis.backend.services.workcell import WorkcellService
from praxis.backend.utils.db import (
  AsyncSessionLocal,
  init_praxis_db_schema,
)

if TYPE_CHECKING:
  from praxis.backend.services.praxis_orm_service import PraxisDBService

from praxis.backend.utils.db import (
  async_engine as praxis_async_engine,
)

# --- Configuration and Logging Setup ---
config_file = "praxis.ini"
praxis_config = PraxisConfiguration(config_file)

# Configure logging from config file
logging.basicConfig(
  filename=praxis_config.log_file,
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
  """Manage application startup and shutdown events.

  Initialize database connections, services, and the main orchestrator.

  This function is used to set up the application state and ensure that all
  necessary components are ready before the application starts handling requests.

  After the application is done, it will clean up resources such as closing
  database connections and disposing of the SQLAlchemy engine.

  Args:
    app: The FastAPI application instance.

  Yields:
    None.

  Raises:
    Exception: If any error occurs during the startup sequence, it will log the error
    and re-raise the exception to prevent the application from starting.

  """
  db_service_instance: PraxisDBService | None = None
  orchestrator: Orchestrator | None = None
  asset_manager: AssetManager | None = None
  workcell_runtime: WorkcellRuntime | None = None
  discovery_service: DiscoveryService | None = None
  try:
    logger.info("Application startup sequence initiated...")

    # Determine storage backend from configuration
    storage_backend_str = praxis_config.storage_backend
    is_lite = praxis_config.is_lite_mode
    logger.info("Storage backend: %s (lite mode: %s)", storage_backend_str, is_lite)

    # Map string to enum
    backend_map = {
      "postgresql": StorageBackend.POSTGRESQL,
      "memory": StorageBackend.MEMORY,
      "sqlite": StorageBackend.SQLITE,
      "redis": StorageBackend.REDIS,
    }
    storage_backend = backend_map.get(storage_backend_str, StorageBackend.POSTGRESQL)

    # Create key-value store and task queue based on backend
    kv_store = StorageFactory.create_key_value_store(storage_backend)
    task_queue = StorageFactory.create_task_queue(storage_backend)
    app.state.kv_store = kv_store
    app.state.task_queue = task_queue
    logger.info(
      "Storage layer initialized: kv_store=%s, task_queue=%s",
      type(kv_store).__name__,
      type(task_queue).__name__,
    )

    logger.info("Initializing Praxis database schema...")
    engine = getattr(app.state, "async_engine", None)
    await init_praxis_db_schema(engine=engine)
    logger.info("Praxis database schema initialization complete.")

    # Initialize AssetManager and WorkcellRuntime
    logger.info("Initializing AssetManager and WorkcellRuntime...")

    workcell = Workcell(
      name="test_workcell",
      save_file="test_workcell.json",
      file_system=FileSystem(),
    )
    async with AsyncSessionLocal() as db_session:
      deck_service = DeckService(Deck)
      machine_service = MachineService(Machine)
      resource_service = ResourceService(Resource)
      deck_type_definition_service = DeckTypeDefinitionService(DeckDefinition)
      workcell_service = WorkcellService(Workcell)
      workcell_runtime = WorkcellRuntime(
        db_session_factory=AsyncSessionLocal,
        workcell=workcell,
        deck_service=deck_service,
        machine_service=machine_service,
        resource_service=resource_service,
        deck_type_definition_service=deck_type_definition_service,
        workcell_service=workcell_service,
      )
    logger.info("WorkcellRuntime initialized successfully.")
    async with AsyncSessionLocal() as db_session:  # Use async with for session
      asset_lock_manager = AssetLockManager()
      resource_type_definition_service = ResourceTypeDefinitionService(db_session)
      asset_manager = AssetManager(
        db_session=db_session,
        workcell_runtime=workcell_runtime,
        deck_service=deck_service,
        machine_service=machine_service,
        resource_service=resource_service,
        resource_type_definition_service=resource_type_definition_service,
        asset_lock_manager=asset_lock_manager,
      )

      # Initialize the new type definition services
      logger.info("Initializing type definition services...")
      machine_type_definition_service = MachineTypeDefinitionService(db_session)
      logger.info("Type definition services initialized.")

      # Initialize DiscoveryService with all type definition services
      logger.info("Initializing DiscoveryService...")
      from praxis.backend.models.domain.protocol import FunctionProtocolDefinition, ProtocolRun

      protocol_definition_service = ProtocolDefinitionCRUDService(FunctionProtocolDefinition)
      discovery_service = DiscoveryService(
        db_session_factory=AsyncSessionLocal,
        resource_type_definition_service=resource_type_definition_service,
        machine_type_definition_service=machine_type_definition_service,
        protocol_definition_service=protocol_definition_service,
      )
      logger.info("DiscoveryService initialized.")

      # Instantiate and initialize the Orchestrator with its dependencies
      logger.info("Initializing orchestrator...")
      orchestrator = Orchestrator(
        db_session_factory=AsyncSessionLocal,
        asset_manager=asset_manager,
        workcell_runtime=workcell_runtime,
      )
      logger.info("Orchestrator dependencies initialized.")

      # Configure Celery (only in production mode)
      if not is_lite:
        logger.info("Configuring Celery app...")
        configure_celery_app(
          celery_app,
          broker_url=praxis_config.celery_broker_url,
          backend_url=praxis_config.celery_result_backend,
        )
        logger.info("Celery app configured.")
        scheduler_task_queue = celery_app
      else:
        logger.info("Lite mode: Skipping Celery configuration, using in-memory task queue")
        scheduler_task_queue = task_queue

      # Initialize ProtocolExecutionService
      logger.info("Initializing ProtocolExecutionService...")
      from praxis.backend.core.protocol_execution_service import ProtocolExecutionService
      from praxis.backend.core.scheduler import ProtocolScheduler
      from praxis.backend.services.mock_data_generator import MockTelemetryService
      from praxis.backend.services.protocols import ProtocolRunService

      protocol_run_service = ProtocolRunService(ProtocolRun)
      protocol_scheduler = ProtocolScheduler(
        db_session_factory=AsyncSessionLocal,
        task_queue=scheduler_task_queue,
        protocol_run_service=protocol_run_service,
        protocol_definition_service=protocol_definition_service,
      )

      # Inject scheduler into orchestrator
      # This addresses the circular dependency where Orchestrator needs Scheduler to release assets
      orchestrator.scheduler = protocol_scheduler

      mock_telemetry_service = MockTelemetryService(protocol_run_service=protocol_run_service)

      protocol_execution_service = ProtocolExecutionService(
        db_session_factory=AsyncSessionLocal,
        asset_manager=asset_manager,
        workcell_runtime=workcell_runtime,
        scheduler=protocol_scheduler,
        orchestrator=orchestrator,
        protocol_run_service=protocol_run_service,
        protocol_definition_service=protocol_definition_service,
      )
      logger.info("ProtocolExecutionService initialized.")

      # Store the fully initialized services in the app state
      app.state.orchestrator = orchestrator
      app.state.discovery_service = discovery_service
      app.state.praxis_config = praxis_config
      app.state.protocol_execution_service = protocol_execution_service
      app.state.mock_telemetry_service = mock_telemetry_service
      logger.info(
        "Orchestrator, DiscoveryService, and ProtocolExecutionService attached to application state."
      )
      logger.info("Application startup complete.")

      yield  # The application is now running

  except Exception:
    logger.exception("Error during application startup")
    # In a production scenario, you might want to exit or handle this more gracefully
    raise
  finally:
    logger.info("Application shutdown sequence initiated...")
    try:
      # Safely close the database services using the instance created during startup
      if db_service_instance:
        logger.info("Closing PraxisDBService (Keycloak pool)...")
        await db_service_instance.close()
        logger.info("PraxisDBService closed.")

      # Dispose of the SQLAlchemy engine for the main Praxis DB
      logger.info("Disposing of Praxis SQLAlchemy engine...")
      await praxis_async_engine.dispose()
      logger.info("Praxis SQLAlchemy engine disposed.")

      logger.info("Application shutdown complete.")
    except Exception:
      logger.exception("Error during application shutdown")


app = FastAPI(
  title="Praxis Backend",
  description="A comprehensive Python-based platform to automate and manage laboratory \
    workflows.",
  version="1.0.0",
  lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> Response:
  """Handle ValueError exceptions."""
  from fastapi.responses import JSONResponse

  return JSONResponse(
    status_code=400,
    content={"detail": str(exc)},
  )


# CORS Middleware Configuration
import os

_default_cors = "http://localhost:5173,http://localhost:4200"
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_cors).split(",") if o.strip()]

app.add_middleware(
  CORSMiddleware,
  allow_origins=_cors_origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- API Router Inclusion ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(
  outputs.router,
  prefix="/api/v1/data-outputs",
  tags=["Data Outputs"],
)
app.include_router(protocols.router, prefix="/api/v1/protocols", tags=["Protocols"])
app.include_router(workcell.router, prefix="/api/v1/workcell", tags=["Workcell"])
app.include_router(resources.router, prefix="/api/v1/resources", tags=["Assets"])
app.include_router(decks.router, prefix="/api/v1/decks", tags=["Decks"])
app.include_router(machines.router, prefix="/api/v1/machines", tags=["Machines"])
app.include_router(
  machine_frontends.router, prefix="/api/v1/machine-frontends", tags=["Machine Frontends"]
)
app.include_router(
  machine_backends.router, prefix="/api/v1/machine-backends", tags=["Machine Backends"]
)
app.include_router(hardware.router, prefix="/api/v1/hardware", tags=["Hardware"])
app.include_router(discovery.router, prefix="/api/v1/discovery", tags=["Discovery"])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["Scheduler"])

from praxis.backend.api import repl, websockets

app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])
app.include_router(repl.router, prefix="/api/v1/repl", tags=["REPL"])


# --- Middleware and Root Endpoint ---


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:  # type: ignore
  """Middleware to log incoming requests and their response status codes."""
  logger.info("Request: %s %s", request.method, request.url.path)
  response: Response = await call_next(request)
  logger.info(
    "Response: %s %s - Status %s",
    request.method,
    request.url.path,
    response.status_code,
  )
  return response


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
  """Redirects the root URL to the static index page."""
  return RedirectResponse(url="/docs")
