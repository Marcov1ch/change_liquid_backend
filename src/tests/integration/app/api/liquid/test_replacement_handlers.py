import pytest
from fastapi import status


@pytest.fixture
def vehicle(client, auth_headers):
    data = {
        "brand": "Toyota",
        "model": "Camry",
        "plate_number": "А123АА178",
        "year": 2020,
        "current_km": 50000,
        "oil_interval_km": 7000,
        "transmission_interval_km": 60000,
        "brake_interval_km": 40000,
        "coolant_interval_km": 60000,
        "power_steering_interval_km": 40000,
        "differential_oil_interval_km": 80000,
    }
    resp = client.post("/api/v1/vehicles", json=data, headers=auth_headers)
    return resp.json()


class TestCreateReplacements:
    def test_create_single(self, client, auth_headers, vehicle):
        resp = client.post(
            f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
            json={
                "replacements": [{
                    "liquid_type": "engine_oil",
                    "liquid_name": "Mobil 1 5W-30",
                    "liquid_price": 5000,
                    "work_price": 1500,
                    "replacement_date": "2024-06-01",
                    "km_at_replacement": 45000,
                }]
            },
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]["liquid_name"] == "Mobil 1 5W-30"
        assert data[0]["status"] in ("good", "warning", "critical", "overdue")

    def test_create_multiple(self, client, auth_headers, vehicle):
        resp = client.post(
            f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
            json={
                "replacements": [
                    {
                        "liquid_type": "engine_oil",
                        "liquid_name": "Mobil 1 5W-30",
                        "replacement_date": "2024-06-01",
                        "km_at_replacement": 45000,
                    },
                    {
                        "liquid_type": "brake_fluid",
                        "liquid_name": "Bosch DOT4",
                        "replacement_date": "2024-06-01",
                        "km_at_replacement": 45000,
                    },
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 2

    def test_create_other_user_vehicle(self, client, auth_headers, other_auth_headers, vehicle):
        resp = client.post(
            f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
            json={
                "replacements": [{
                    "liquid_type": "engine_oil",
                    "liquid_name": "Mobil 1",
                    "replacement_date": "2024-06-01",
                    "km_at_replacement": 45000,
                }]
            },
            headers=other_auth_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.fixture
def replacement(client, auth_headers, vehicle):
    resp = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
        json={
            "replacements": [{
                "liquid_type": "engine_oil",
                "liquid_name": "Mobil 1 5W-30",
                "liquid_price": 5000,
                "work_price": 1500,
                "replacement_date": "2024-06-01",
                "km_at_replacement": 45000,
            }]
        },
        headers=auth_headers,
    )
    return resp.json()[0]


class TestGetReplacements:
    def test_list_replacements(self, client, auth_headers, vehicle, replacement):
        resp = client.get(
            f"/api/v1/vehicles/{vehicle['id']}/replacements",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_latest_replacement_has_active_status(self, client, auth_headers, vehicle):
        # Первая замена
        client.post(
            f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
            json={
                "replacements": [{
                    "liquid_type": "engine_oil",
                    "liquid_name": "Old Oil",
                    "replacement_date": "2023-01-01",
                    "km_at_replacement": 40000,
                }]
            },
            headers=auth_headers,
        )
        # Вторая замена (более новая по пробегу)
        client.post(
            f"/api/v1/vehicles/{vehicle['id']}/replacements/bulk",
            json={
                "replacements": [{
                    "liquid_type": "engine_oil",
                    "liquid_name": "New Oil",
                    "replacement_date": "2024-06-01",
                    "km_at_replacement": 45000,
                }]
            },
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/v1/vehicles/{vehicle['id']}/replacements",
            headers=auth_headers,
        )
        data = resp.json()
        oil_replacements = [r for r in data if r["liquid_type"] == "engine_oil"]
        oil_replacements.sort(key=lambda r: r["km_at_replacement"])

        assert len(oil_replacements) == 2
        # Старая замена — replaced
        assert oil_replacements[0]["status"] == "replaced"
        assert oil_replacements[0]["status_message"] == "📌 Заменено (предыдущая запись)"
        # Новая замена — активный статус
        assert oil_replacements[1]["status"] != "replaced"

    def test_empty_list(self, client, auth_headers, vehicle):
        resp = client.get(
            f"/api/v1/vehicles/{vehicle['id']}/replacements",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []


class TestUpdateReplacement:
    def test_update_km(self, client, auth_headers, vehicle, replacement):
        resp = client.put(
            f"/api/v1/replacements/{replacement['id']}",
            json={"km_at_replacement": 52000, "liquid_name": "Updated Oil"},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["km_at_replacement"] == 52000
        assert data["liquid_name"] == "Updated Oil"

    def test_update_other_user_replacement(
        self, client, auth_headers, other_auth_headers, vehicle, replacement,
    ):
        resp = client.put(
            f"/api/v1/replacements/{replacement['id']}",
            json={"km_at_replacement": 47000},
            headers=other_auth_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteReplacement:
    def test_delete(self, client, auth_headers, vehicle, replacement):
        resp = client.delete(
            f"/api/v1/replacements/{replacement['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK

        resp = client.get(
            f"/api/v1/vehicles/{vehicle['id']}/replacements",
            headers=auth_headers,
        )
        assert len(resp.json()) == 0

    def test_delete_other_user_replacement(
        self, client, auth_headers, other_auth_headers, vehicle, replacement,
    ):
        resp = client.delete(
            f"/api/v1/replacements/{replacement['id']}",
            headers=other_auth_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
