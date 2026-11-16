from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, BrandDB, ModelDB, VehicleDB
from app.repository.vehicle_repository import VehicleRepository


def _seed_vehicle(session: Session) -> VehicleDB:
    session.add_all([
        BrandDB(id=1, name='VW'),
        ModelDB(id=1, brand_id=1, name='Golf'),
    ])
    vehicle = VehicleDB(
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2020,
        current_km=10000,
        owner_id=1,
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def test_replace_reference_creates_items_and_variants() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        vehicle = _seed_vehicle(session)

        repository = VehicleRepository(session)
        dto = repository.replace_reference(vehicle.id, [
            {
                'component_type': 'engine_oil',
                'volume_liters': 5.7,
                'note': None,
                'variants': [
                    {'name': '0W-20', 'approvals': 'VW 508 00'},
                    {'name': '5W-30', 'approvals': 'VW 504 00'},
                ],
            },
            {
                'component_type': 'cabin_filter',
                'volume_liters': None,
                'note': 'менять раз в год',
                'variants': [{'name': 'MANN CUK 2643', 'approvals': None}],
            },
        ])

    assert dto is not None
    assert [item['component_type'] for item in dto.reference_items] == [
        'engine_oil',
        'cabin_filter',
    ]
    oil = dto.reference_items[0]
    assert oil['volume_liters'] == 5.7
    assert [variant['name'] for variant in oil['variants']] == ['0W-20', '5W-30']


def test_replace_reference_removes_previous_items() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        vehicle = _seed_vehicle(session)

        repository = VehicleRepository(session)
        repository.replace_reference(vehicle.id, [
            {
                'component_type': 'engine_oil',
                'volume_liters': 5.7,
                'note': None,
                'variants': [{'name': '0W-20', 'approvals': None}],
            },
        ])
        dto = repository.replace_reference(vehicle.id, [
            {
                'component_type': 'coolant',
                'volume_liters': 7.5,
                'note': None,
                'variants': [],
            },
        ])

    assert dto is not None
    assert len(dto.reference_items) == 1
    assert dto.reference_items[0]['component_type'] == 'coolant'


def test_replace_reference_updates_same_component() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        vehicle = _seed_vehicle(session)
        repository = VehicleRepository(session)
        repository.replace_reference(vehicle.id, [
            {
                'component_type': 'engine_oil',
                'volume_liters': 5.7,
                'note': None,
                'variants': [{'name': '0W-20', 'approvals': None}],
            },
        ])
        dto = repository.replace_reference(vehicle.id, [
            {
                'component_type': 'engine_oil',
                'volume_liters': 6.0,
                'note': None,
                'variants': [{'name': '5W-30', 'approvals': 'VW 504 00'}],
            },
        ])

    assert dto is not None
    assert len(dto.reference_items) == 1
    oil = dto.reference_items[0]
    assert oil['volume_liters'] == 6.0
    assert [variant['name'] for variant in oil['variants']] == ['5W-30']
