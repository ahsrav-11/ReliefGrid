# ReliefGrid: Smart Disaster Relief Allocation and Rescue Coordination

Flask + SQLite + vanilla JS + Chart.js. The allocation algorithm lives in `app/allocation_engine.py` (pure Python, no Flask or DB code).

See `docs/TECH_STACK.md` for why each technology was chosen.

## Run
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python seed.py          # demo data (optional: set DATABASE_URL for PostgreSQL, SECRET_KEY for production)
    python run.py           # http://127.0.0.1:5000
    pytest                  # engine + workflow tests

Logins: admin / admin123 (admin); coastal, riverside, hilltown / center123 (relief centers).

## Demo flow
1. Log in as `coastal`, open My requests, send a request.
2. Log in as `admin`, open Allocation, pick Cyclone Varda floods + Drinking water, preview the ranked plan and the reasons, then Apply.
3. Admin: Deliveries, Dispatch. Relief center: Confirm receipt or Report issue.
4. Admin: Simulation (e.g. demand 150%, supply 50%) to compare plans, then Reports.

## Modules
1 Auth/roles: auth.py, utils/RBAC guards | 2 Disasters/locations: admin.py | 3 Inventory: admin.py, services.py (reserved stock prevents over-allocation)
4 Requests: requests_bp.py | 5 Allocation: allocation_engine.py, allocation.py | 6 Deliveries: delivery.py
7 Simulation: allocation.py (simulate) | 8 Dashboards, notifications, reports: core.py

## Priority score
score = 100 x (0.40 urgency/5 + 0.25 population/max + 0.15 area severity/5 + 0.20 quantity/max quantity)
Modes: priority-first, or proportional sharing. Every row stores a plain-language explanation.

## Also included
- Stock log (admin): every received and dispatched quantity per depot.
- Requests can be filtered by status; requests for a closed disaster are blocked.
- A partially approved request stays "partial" after delivery, so its unmet demand is still visible.
- Relief centers can update their affected population in Profile.
- Reports can be downloaded as CSV.
- Not implemented: vehicle capacity limits (optional in the brief).

## Notes
- Forms use Flask-WTF CSRFProtect; validation is done server-side in the routes.
- Flask-Migrate was left out on purpose (db.create_all is enough for a prototype). Run `python seed.py` again after schema changes.
