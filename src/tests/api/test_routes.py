from fastapi import FastAPI

from app.api.routes import setup_routes

_API_METHODS = {'get', 'post', 'put', 'patch', 'delete'}

_EXPECTED_ROUTES: set[tuple[str, str, tuple[str, ...]]] = {
    ('/api/v1/vehicles', 'GET', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}', 'GET', ('vehicles',)),
    ('/api/v1/vehicles', 'POST', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/km', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/restore', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/notify', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/sizes', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/intervals', 'PATCH', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}', 'DELETE', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/hard', 'DELETE', ('vehicles',)),
    ('/api/v1/vehicles/{vehicle_id}/replacements', 'GET', ('replacements',)),
    ('/api/v1/replacements/{replacement_id}', 'GET', ('replacements',)),
    ('/api/v1/replacements/{replacement_id}', 'PUT', ('replacements',)),
    ('/api/v1/replacements/{replacement_id}', 'DELETE', ('replacements',)),
    ('/api/v1/vehicles/{vehicle_id}/replacements/bulk', 'POST', ('replacements',)),
    ('/api/v1/vehicles/{vehicle_id}/tire-sets', 'GET', ('tire-sets',)),
    ('/api/v1/vehicles/{vehicle_id}/tire-sets', 'POST', ('tire-sets',)),
    ('/api/v1/tire-sets/{tire_set_id}', 'PATCH', ('tire-sets',)),
    ('/api/v1/tire-sets/{tire_set_id}', 'DELETE', ('tire-sets',)),
    ('/api/v1/vehicles/{vehicle_id}/tire-sets/{tire_set_id}/install', 'POST', ('tire-sets',)),
    ('/api/v1/vehicles/{vehicle_id}/fuel-records', 'GET', ('fuel-records',)),
    ('/api/v1/vehicles/{vehicle_id}/fuel-records', 'POST', ('fuel-records',)),
    ('/api/v1/fuel-records/{record_id}', 'GET', ('fuel-records',)),
    ('/api/v1/fuel-records/{record_id}', 'PATCH', ('fuel-records',)),
    ('/api/v1/fuel-records/{record_id}', 'DELETE', ('fuel-records',)),
    ('/api/v1/vehicles/{vehicle_id}/other-expenses', 'GET', ('other-expenses',)),
    ('/api/v1/vehicles/{vehicle_id}/other-expenses', 'POST', ('other-expenses',)),
    ('/api/v1/other-expenses/{expense_id}', 'GET', ('other-expenses',)),
    ('/api/v1/other-expenses/{expense_id}', 'PATCH', ('other-expenses',)),
    ('/api/v1/other-expenses/{expense_id}', 'DELETE', ('other-expenses',)),
    ('/api/v1/vehicles/{vehicle_id}/repairs', 'GET', ('repairs',)),
    ('/api/v1/vehicles/{vehicle_id}/repairs', 'POST', ('repairs',)),
    ('/api/v1/repairs/{repair_id}', 'GET', ('repairs',)),
    ('/api/v1/repairs/{repair_id}', 'PUT', ('repairs',)),
    ('/api/v1/repairs/{repair_id}', 'DELETE', ('repairs',)),
    ('/api/v1/vehicles/{vehicle_id}/share', 'GET', ('share',)),
    ('/api/v1/vehicles/{vehicle_id}/share', 'POST', ('share',)),
    ('/api/v1/vehicles/{vehicle_id}/share/rotate', 'POST', ('share',)),
    ('/api/v1/vehicles/{vehicle_id}/share', 'DELETE', ('share',)),
    ('/api/v1/public/vehicles/{token}', 'GET', ('public',)),
    ('/api/v1/enums/brands', 'GET', ('enums',)),
    ('/api/v1/enums/models/{brand}', 'GET', ('enums',)),
    ('/api/v1/enums/components', 'GET', ('enums',)),
    ('/api/v1/enums/component-configs', 'GET', ('enums',)),
}


def _openapi_routes(app: FastAPI) -> set[tuple[str, str, tuple[str, ...]]]:
    schema = app.openapi()
    return {
        (path, method.upper(), tuple(operation.get('tags', [])))
        for path, operations in schema['paths'].items()
        for method, operation in operations.items()
        if method in _API_METHODS
    }


def test_setup_routes_preserves_public_api_contract() -> None:
    app = FastAPI()
    setup_routes(app)

    assert _openapi_routes(app) == _EXPECTED_ROUTES


def test_setup_routes_has_no_duplicate_path_method_pairs() -> None:
    app = FastAPI()
    setup_routes(app)

    keys = [
        (route.path, tuple(sorted(route.methods - {'HEAD', 'OPTIONS'})))
        for route in app.routes
        if getattr(route, 'path', '').startswith('/api/v1')
    ]

    assert len(keys) == len(set(keys))
    assert len(keys) == len(_EXPECTED_ROUTES)
