"""GET /api/v1/locations against the MySQL test database."""
from app.modules.warehouse.models import Location, LocationKind

URL = "/api/v1/locations"


def test_list_locations_empty(client, db):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}


def test_list_locations_returns_the_full_shape(client, db):
    location = Location(x=3, y=4, kind=LocationKind.storage, zone="A", aisle="A1")
    db.add(location)
    db.commit()

    body = client.get(URL).json()

    assert body == {
        "items": [{"location_id": location.id, "x": 3, "y": 4, "kind": "storage", "zone": "A", "aisle": "A1"}],
        "count": 1,
    }


def test_list_locations_includes_every_kind(client, db):
    db.add_all(Location(x=x, y=0, kind=kind) for x, kind in enumerate(LocationKind))
    db.commit()

    items = client.get(URL).json()["items"]

    assert {item["kind"] for item in items} == {"storage", "pick_station", "dock", "charger"}


def test_list_locations_zone_and_aisle_can_be_null(client, db):
    db.add(Location(x=0, y=0, kind=LocationKind.dock))
    db.commit()

    item = client.get(URL).json()["items"][0]

    assert item["zone"] is None
    assert item["aisle"] is None


def test_list_locations_sorted_row_by_row(client, db):
    db.add_all(Location(x=x, y=y, kind=LocationKind.storage) for x, y in [(1, 1), (0, 1), (5, 0), (2, 0)])
    db.commit()

    items = client.get(URL).json()["items"]

    assert [(item["x"], item["y"]) for item in items] == [(2, 0), (5, 0), (0, 1), (1, 1)]


def test_list_locations_returns_more_than_a_page(client, db):
    db.add_all(Location(x=x, y=0, kind=LocationKind.storage) for x in range(600))
    db.commit()

    assert client.get(URL).json()["count"] == 600
