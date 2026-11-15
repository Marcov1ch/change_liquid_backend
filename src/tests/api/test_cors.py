from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.common.cors import setup_cors


def _client() -> TestClient:
    app = FastAPI()
    setup_cors(app)

    @app.get('/ping')
    def ping() -> dict[str, str]:
        return {'status': 'ok'}

    return TestClient(app)


def test_capacitor_preflight_allowed() -> None:
    response = _client().options(
        '/auth/currency',
        headers={
            'Origin': 'https://localhost',
            'Access-Control-Request-Method': 'PATCH',
            'Access-Control-Request-Headers': 'authorization,content-type',
        },
    )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://localhost'
    assert 'authorization' in response.headers['access-control-allow-headers'].lower()


def test_retry_after_is_exposed() -> None:
    response = _client().get('/ping', headers={'Origin': 'https://localhost'})

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://localhost'
    assert 'retry-after' in response.headers['access-control-expose-headers'].lower()


def test_unknown_origin_not_allowed() -> None:
    response = _client().options(
        '/api/v1/vehicles',
        headers={
            'Origin': 'https://evil.example',
            'Access-Control-Request-Method': 'GET',
        },
    )

    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers
