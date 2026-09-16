"""FastAPI and WebSocket transport adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from jarvis.config.settings import Settings
from jarvis.core.application import Application, create_application
from jarvis.models.contracts import ChatRequest, ChatResponse


def create_api(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        application = create_application(settings)
        app.state.application = application
        await application.start()
        yield
        await application.stop()

    api = FastAPI(title="JARVIS API", version="0.1.0", lifespan=lifespan)

    def application(request: Request) -> Application:
        return request.app.state.application  # type: ignore[no-any-return]

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/v1/tools")
    async def available_tools(request: Request) -> list[dict[str, object]]:
        return application(request).tools.descriptions()

    @api.post("/v1/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        return await application(request).brain.respond(payload.message, payload.conversation_id)

    @api.websocket("/v1/ws/chat")
    async def chat_socket(socket: WebSocket) -> None:
        await socket.accept()
        try:
            while True:
                payload = ChatRequest.model_validate_json(await socket.receive_text())
                await socket.send_json(
                    (
                        await socket.app.state.application.brain.respond(
                            payload.message, payload.conversation_id
                        )
                    ).model_dump(mode="json")
                )
        except WebSocketDisconnect:
            return

    return api
