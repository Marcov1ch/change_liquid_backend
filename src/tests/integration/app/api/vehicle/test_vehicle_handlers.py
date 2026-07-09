from fastapi import status


class TestGetVehicles:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/vehicles", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_list_returns_owned(self, client, auth_headers, default_vehicle_data):
        client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers)
        resp = client.get("/api/v1/vehicles", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["plate_number"] == "А123АА178"

    def test_list_excludes_archived(self, client, auth_headers, default_vehicle_data):
        resp = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers)
        vehicle_id = resp.json()["id"]
        client.delete(f"/api/v1/vehicles/{vehicle_id}", headers=auth_headers)
        resp = client.get("/api/v1/vehicles", headers=auth_headers)
        assert len(resp.json()) == 0

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/vehicles")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestCreateVehicle:
    def test_create_success(self, client, auth_headers, default_vehicle_data):
        resp = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["plate_number"] == "А123АА178"
        assert data["current_km"] == 50000

    def test_duplicate_plate(self, client, auth_headers, default_vehicle_data):
        client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers)
        resp = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers)
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_invalid_brand(self, client, auth_headers, default_vehicle_data):
        data = dict(default_vehicle_data, brand="FakeBrand")
        resp = client.post("/api/v1/vehicles", json=data, headers=auth_headers)
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_invalid_plate_format(self, client, auth_headers, default_vehicle_data):
        data = dict(default_vehicle_data, plate_number="invalid")
        resp = client.post("/api/v1/vehicles", json=data, headers=auth_headers)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestGetVehicle:
    def test_get_by_id(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.get(f"/api/v1/vehicles/{created['id']}", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == created["id"]

    def test_get_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/vehicles/99999", headers=auth_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_other_user_vehicle(self, client, auth_headers, other_auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.get(f"/api/v1/vehicles/{created['id']}", headers=other_auth_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateVehicle:
    def test_update_fields(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.patch(
            f"/api/v1/vehicles/{created['id']}",
            json={"plate_number": "В456ВВ178", "year": 2021, "current_km": 55000},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["plate_number"] == "В456ВВ178"
        assert data["year"] == 2021
        assert data["current_km"] == 55000

    def test_update_km(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.patch(
            f"/api/v1/vehicles/{created['id']}",
            json={"current_km": 60000},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["current_km"] == 60000

    def test_update_intervals(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.patch(
            f"/api/v1/vehicles/{created['id']}",
            json={"oil_interval_km": 10000, "brake_interval_km": 50000},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["oil_interval_km"] == 10000
        assert data["brake_interval_km"] == 50000

    def test_update_notify_flags(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.patch(
            f"/api/v1/vehicles/{created['id']}",
            json={"oil_notify_enabled": False, "brake_notify_enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["oil_notify_enabled"] is False
        assert data["brake_notify_enabled"] is False

    def test_update_other_user_vehicle(self, client, auth_headers, other_auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.patch(
            f"/api/v1/vehicles/{created['id']}",
            json={"plate_number": "В456ВВ178"},
            headers=other_auth_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteVehicle:
    def test_soft_delete(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        vid = created["id"]
        resp = client.delete(f"/api/v1/vehicles/{vid}", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "ok"

    def test_hard_delete(self, client, auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        vid = created["id"]
        client.delete(f"/api/v1/vehicles/{vid}", headers=auth_headers)
        resp = client.delete(f"/api/v1/vehicles/{vid}/hard", headers=auth_headers)
        assert resp.status_code == status.HTTP_200_OK

    def test_delete_other_user_vehicle(self, client, auth_headers, other_auth_headers, default_vehicle_data):
        created = client.post("/api/v1/vehicles", json=default_vehicle_data, headers=auth_headers).json()
        resp = client.delete(f"/api/v1/vehicles/{created['id']}", headers=other_auth_headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
