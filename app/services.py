from . import db
from .models import Stock, Location, Delivery


def depot_stocks(disaster_id, resource_id):
    return (Stock.query.join(Location, Stock.depot_id == Location.id)
            .filter(Location.disaster_id == disaster_id, Stock.resource_id == resource_id).all())


def available(disaster_id, resource_id):
    return sum(max(0, s.available) for s in depot_stocks(disaster_id, resource_id))


def assign_deliveries(req, qty):
    """Reserve stock (largest available depot first) and create one delivery per depot used."""
    if qty > available(req.disaster_id, req.resource_id):
        raise ValueError("Not enough available stock for this allocation.")
    need = qty
    for s in sorted(depot_stocks(req.disaster_id, req.resource_id), key=lambda s: -s.available):
        take = min(need, max(0, s.available))
        if take:
            s.reserved += take
            db.session.add(Delivery(request=req, stock=s, quantity=take))
            need -= take
        if not need:
            break
    req.approved_qty = qty
    req.status = "approved" if qty == req.quantity else "partial"
