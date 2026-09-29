import builtins
import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from praxis.backend.core.repl_session import ReplSession
from praxis.backend.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/session")
async def repl_websocket_endpoint(websocket: WebSocket):
  """WebSocket endpoint for interactive REPL session."""
  await websocket.accept()
  logger.info("REPL WebSocket connected")

  # Initialize a new session
  # TODO: Inject actual context (LiquidHandler, etc.)
  session = ReplSession(context={"msg": "Hello from Praxis REPL!"})

  # Send initial variables
  await websocket.send_json(
    {"type": "VARS_UPDATE", "payload": {"variables": session.get_variables()}}
  )

  try:
    while True:
      data = await websocket.receive_json()
      command_type = data.get("type")
      payload = data.get("payload", {})

      if command_type == "EXEC":
        code = payload.get("code", "")

        # Run in thread executor if blocking, but interactive console relies on state
        # For now run synchronously as code.InteractiveConsole is fast for simple steps
        # Long running tasks will block - acceptable for v1
        more, output, error = session.push(code)

        response: dict[str, Any] = {
          "type": "RESULT",
          "id": data.get("id"),
          "payload": {
            "more": more,
            "output": output,
          },
        }

        # If InteractiveConsole.push caught an exception it prints to stderr (captured in output)
        # If we caught something else, we send ERROR
        if error:
          response["type"] = "ERROR"
          response["payload"]["error"] = error

        await websocket.send_json(response)

        # Send variable update after execution
        await websocket.send_json(
          {"type": "VARS_UPDATE", "payload": {"variables": session.get_variables()}}
        )

      elif command_type == "COMPLETION":
        text = payload.get("code", "")  # or 'text'
        matches = session.get_completions(text)
        await websocket.send_json(
          {"type": "COMPLETION_RESULT", "id": data.get("id"), "payload": {"matches": matches}}
        )

      elif command_type == "RESTART":
        # Create new session
        session = ReplSession(context={"msg": "Hello from Praxis REPL (Restarted)!"})
        await websocket.send_json(
          {
            "type": "RESULT",
            "id": data.get("id"),
            "payload": {"more": False, "output": "\nSession Restarted.\n", "restart": True},
          }
        )
        await websocket.send_json(
          {"type": "VARS_UPDATE", "payload": {"variables": session.get_variables()}}
        )

  except WebSocketDisconnect:
    logger.info("REPL WebSocket disconnected")
  except Exception as e:
    logger.error(f"REPL WebSocket error: {e}")
    with contextlib.suppress(builtins.BaseException):
      await websocket.close(code=1011)


class SaveSessionRequest(BaseModel):
  history: list[str]


@router.post("/save_session")
async def save_session(request: SaveSessionRequest):
  """Save the current session history as a protocol."""
  try:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"repl_session_{timestamp}.py"
    file_path = Path("praxis/protocols") / filename

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = [
      f"# REPL Session saved at {datetime.now(timezone.utc).isoformat()}",
      "# strict: true",  # default to strict for safety
      "",
      "from pylabrobot.legacy.liquid_handling import LiquidHandler",
      "from pylabrobot import resources",
      "",
      "async def protocol(lh: LiquidHandler):",
    ]

    # Add indented history (reversed since frontend stores newest-first)
    chronological_history = request.history[::-1]
    content.extend(f"  {line}" for line in chronological_history)

    async with aiofiles.open(file_path, "w") as f:
      await f.write("\n".join(content))

    return {"filename": filename, "path": str(file_path)}

  except Exception as e:
    logger.error(f"Error saving session: {e}")
    raise HTTPException(status_code=500, detail=str(e)) from e
