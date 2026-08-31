"""Tests for app/exceptions.py: custom AppError subclasses and their handlers.

Builds a small standalone FastAPI app wired with `register_exception_handlers`
(the same function `app.main.create_app` uses) and routes that deliberately
raise each error type, so the handler behavior is verified independent of any
particular business route.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
    register_exception_handlers,
)


def _build_error_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Widget", 42)

    @app.get("/boom/not-found-no-id")
    async def raise_not_found_no_id() -> None:
        raise NotFoundError("Widget")

    @app.get("/boom/conflict")
    async def raise_conflict() -> None:
        raise ConflictError("Widget is already locked.")

    @app.get("/boom/validation")
    async def raise_validation() -> None:
        raise ValidationAppError("Widget name is invalid.")

    @app.get("/boom/unhandled")
    async def raise_unhandled() -> None:
        raise RuntimeError("something exploded")

    return app


@pytest.fixture
def error_client():
    with TestClient(_build_error_test_app(), raise_server_exceptions=False) as c:
        yield c


def test_not_found_error_response_shape(error_client: TestClient) -> None:
    response = error_client.get("/boom/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Widget with id '42' not found",
        }
    }


def test_not_found_error_without_identifier(error_client: TestClient) -> None:
    response = error_client.get("/boom/not-found-no-id")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Widget not found"


def test_conflict_error_response_shape(error_client: TestClient) -> None:
    response = error_client.get("/boom/conflict")
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CONFLICT"
    assert body["error"]["message"] == "Widget is already locked."


def test_validation_app_error_response_shape(error_client: TestClient) -> None:
    response = error_client.get("/boom/validation")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Widget name is invalid."


def test_unhandled_exception_returns_generic_500(error_client: TestClient) -> None:
    response = error_client.get("/boom/unhandled")
    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        }
    }
