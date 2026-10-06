from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.websocket_manager import (
    connection_manager
)


router = APIRouter(
    tags=["Real-Time Monitoring"]
)


@router.websocket("/ws/notifications")
async def notification_websocket(
    websocket: WebSocket
):
    await connection_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

    except Exception:
        connection_manager.disconnect(websocket)