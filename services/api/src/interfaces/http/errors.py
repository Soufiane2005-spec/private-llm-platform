from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(Exception)
    async def unhandled_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "path": str(request.url.path),
                }
            },
        )