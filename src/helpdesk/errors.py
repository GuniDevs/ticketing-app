"""One error type for every failure the API reports, and the handlers that turn it into JSON."""

from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify(_body(error.code, error.message)), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        code = (error.name or "error").lower().replace(" ", "_")
        return jsonify(_body(code, error.description or error.name)), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):  # noqa: ARG001 - never show internals to the caller
        app.logger.exception("unexpected error")
        return jsonify(_body("internal_error", "something went wrong")), 500
