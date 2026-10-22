
from app import db
from app.models import *


def load(reset=True):
    if reset:
        db.drop_all()
        db.create_all()

    # Create disaster
    disaster = Disaster(
        name="Cyclone Varda floods",
        kind="cyclone",
        severity=4,
        description="Coastal flooding, roads cut in two districts."
    )
    db.session.add(disaster)
    db.session.flush()

    # Create locations
    locations = {}

    location_data = [
        ("dc", "Central Depot", "depot", 0, 1),
        ("dn", "North Depot", "depot", 0, 1),
        ("a", "Coastal Village relief center", "center", 1200, 5),
        ("b", "Riverside relief center", "center", 800, 3),
        ("c", "Hill Town relief center", "center", 400, 4),
    ]

    for key, name, kind, population, severity in location_data:
        locations[key] = Location(
            disaster_id=disaster.id,
            name=name,
            kind=kind,
            population=population,
            severity=severity,
        )
        db.session.add(locations[key])

    db.session.flush()

    # Create admin account
    admin = User(
        username="admin@example.com",
        role="admin",
        full_name="Control Room",
    )
    admin.set_password("Admin@ReliefGrid2026")
    db.session.add(admin)

    # Create relief center accounts
    users = {}

    center_accounts = [
        ("a", "coastal@example.com"),
        ("b", "riverside@example.com"),
        ("c", "hilltown@example.com"),
    ]

    for key, email in center_accounts:
        users[key] = User(
            username=email,
            role="center",
            full_name=email.split("@")[0].title() + " Coordinator",
            location_id=locations[key].id,
        )
        users[key].set_password("Center@ReliefGrid2026")
        db.session.add(users[key])

    # Create resources
    resource_data = [
        ("Drinking water", "litres"),
        ("Food packets", "packets"),
        ("Medicine kits", "kits"),
        ("Blankets", "pieces"),
    ]

    resources = {
        name: Resource(name=name, unit=unit)
        for name, unit in resource_data
    }

    db.session.add_all(resources.values())
    db.session.flush()

    # Create depot stock
    stock_data = [
        ("dc", "Drinking water", 3000, 500),
        ("dn", "Drinking water", 1500, 500),
        ("dc", "Food packets", 1200, 200),
        ("dn", "Food packets", 600, 200),
        ("dc", "Medicine kits", 150, 40),
        ("dn", "Blankets", 500, 100),
    ]

    for depot, resource_name, quantity, threshold in stock_data:
        stock = Stock(
            depot_id=locations[depot].id,
            resource_id=resources[resource_name].id,
            quantity=quantity,
            threshold=threshold,
        )
        db.session.add(stock)
        db.session.flush()

        db.session.add(
            StockTransaction(
                stock_id=stock.id,
                kind="received",
                quantity=quantity,
            )
        )

    # Create relief requests
    request_data = [
        ("a", "Drinking water", 3000, 5, 1200),
        ("b", "Drinking water", 2000, 3, 800),
        ("c", "Drinking water", 1500, 4, 400),
        ("a", "Medicine kits", 120, 5, 1200),
        ("c", "Medicine kits", 80, 4, 400),
        ("b", "Food packets", 900, 3, 800),
    ]

    for location_key, resource_name, quantity, urgency, population in request_data:
        db.session.add(
            Request(
                user_id=users[location_key].id,
                location_id=locations[location_key].id,
                disaster_id=disaster.id,
                resource_id=resources[resource_name].id,
                quantity=quantity,
                urgency=urgency,
                population=population,
            )
        )

    db.session.commit()

    print("Demo data created successfully!")
    print("Admin: admin@example.com / Admin@ReliefGrid2026")
    print("Coastal: coastal@example.com / Center@ReliefGrid2026")
    print("Riverside: riverside@example.com / Center@ReliefGrid2026")
    print("Hilltown: hilltown@example.com / Center@ReliefGrid2026")
