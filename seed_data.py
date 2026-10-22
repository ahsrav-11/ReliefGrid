from app import db
from app.models import *


def load(reset=True):
    if reset:
        db.drop_all(); db.create_all()
    d = Disaster(name="Cyclone Varda floods", kind="cyclone", severity=4, description="Coastal flooding, roads cut in two districts.")
    db.session.add(d); db.session.flush()
    L = {}
    for key, name, kind, pop, sev in [("dc", "Central Depot", "depot", 0, 1), ("dn", "North Depot", "depot", 0, 1),
                                       ("a", "Coastal Village relief center", "center", 1200, 5),
                                       ("b", "Riverside relief center", "center", 800, 3), ("c", "Hill Town relief center", "center", 400, 4)]:
        L[key] = Location(disaster_id=d.id, name=name, kind=kind, population=pop, severity=sev); db.session.add(L[key])
    db.session.flush()
    admin = User(username="admin", role="admin", full_name="Control Room"); admin.set_password("admin123"); db.session.add(admin)
    U = {}
    for key, un in [("a", "coastal"), ("b", "riverside"), ("c", "hilltown")]:
        U[key] = User(username=un, role="center", full_name=un.title() + " coordinator", location_id=L[key].id)
        U[key].set_password("center123"); db.session.add(U[key])
    R = {n: Resource(name=n, unit=u) for n, u in [("Drinking water", "litres"), ("Food packets", "packets"), ("Medicine kits", "kits"), ("Blankets", "pieces")]}
    db.session.add_all(R.values()); db.session.flush()
    for dep, rname, q, th in [("dc", "Drinking water", 3000, 500), ("dn", "Drinking water", 1500, 500), ("dc", "Food packets", 1200, 200),
                              ("dn", "Food packets", 600, 200), ("dc", "Medicine kits", 150, 40), ("dn", "Blankets", 500, 100)]:
        s = Stock(depot_id=L[dep].id, resource_id=R[rname].id, quantity=q, threshold=th); db.session.add(s); db.session.flush()
        db.session.add(StockTransaction(stock_id=s.id, kind="received", quantity=q))
    for loc, rname, q, urg, pop in [("a", "Drinking water", 3000, 5, 1200), ("b", "Drinking water", 2000, 3, 800), ("c", "Drinking water", 1500, 4, 400),
                                    ("a", "Medicine kits", 120, 5, 1200), ("c", "Medicine kits", 80, 4, 400), ("b", "Food packets", 900, 3, 800)]:
        db.session.add(Request(user_id=U[loc].id, location_id=L[loc].id, disaster_id=d.id, resource_id=R[rname].id, quantity=q, urgency=urg, population=pop))
    db.session.commit()
    print("Seeded. Log in as admin/admin123, coastal/center123, riverside/center123 or hilltown/center123.")
