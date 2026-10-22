from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .. import db
from ..models import Disaster, Location, Resource, Stock, StockTransaction, User
from ..utils import field, intval

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@login_required
def guard():
    if not current_user.is_admin:
        abort(403)


def opts(model, label=lambda x: x.name):
    return [(x.id, label(x)) for x in model.query.order_by(model.id)]


def save(action, ok_msg, back):
    try:
        action()
        db.session.commit()
        flash(ok_msg, "ok")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return redirect(url_for(back))


@bp.route("/disasters", methods=["GET", "POST"])
def disasters():
    if request.method == "POST":
        f = request.form

        def add():
            if not f.get("name", "").strip():
                raise ValueError("Name is required.")
            db.session.add(Disaster(name=f["name"].strip(), kind=f.get("kind", "flood"),
                                    severity=intval(f.get("severity"), 1, 5, "Severity"),
                                    description=f.get("description", "")))
        return save(add, "Disaster created.", "admin.disasters")
    fields = [field("name", "Name"), field("kind", "Type", "select", [(k, k.title()) for k in ("flood", "cyclone", "earthquake", "other")]),
              field("severity", "Severity (1-5)", "number", value=3, min=1, max=5), field("description", "Description", "textarea")]
    rows = [{"cells": [d.name, d.kind, d.severity, d.status], "actions": [("Update", url_for("admin.edit_disaster", id=d.id), "get")]}
            for d in Disaster.query.order_by(Disaster.id.desc())]
    return render_template("crud.html", title="Disasters", fields=fields, submit="Create disaster",
                           headers=["Name", "Type", "Severity", "Status"], rows=rows)


@bp.route("/disasters/<int:id>/edit", methods=["GET", "POST"])
def edit_disaster(id):
    d = db.get_or_404(Disaster, id)
    if request.method == "POST":
        def upd():
            d.severity = intval(request.form.get("severity"), 1, 5, "Severity")
            d.status = request.form.get("status", d.status)
            d.description = request.form.get("description", "")
        return save(upd, "Conditions updated.", "admin.disasters")
    fields = [field("severity", "Severity (1-5)", "number", value=d.severity, min=1, max=5),
              field("status", "Status", "select", [("active", "Active"), ("closed", "Closed")], value=d.status),
              field("description", "Conditions", "textarea", value=d.description)]
    return render_template("crud.html", title=f"Update {d.name}", fields=fields, submit="Save conditions")


@bp.route("/locations", methods=["GET", "POST"])
def locations():
    if request.method == "POST":
        f = request.form

        def add():
            if not f.get("name", "").strip():
                raise ValueError("Name is required.")
            db.session.add(Location(disaster_id=intval(f.get("disaster_id"), 1, 10**9, "Disaster"), name=f["name"].strip(),
                                    kind=f.get("kind"), population=intval(f.get("population"), 0, 10**8, "Population"),
                                    severity=intval(f.get("severity"), 1, 5, "Severity")))
        return save(add, "Location added.", "admin.locations")
    fields = [field("disaster_id", "Disaster", "select", opts(Disaster)), field("name", "Name"),
              field("kind", "Kind", "select", [("affected", "Affected area"), ("shelter", "Shelter"), ("center", "Relief center"), ("depot", "Depot")]),
              field("population", "Affected population", "number", value=0), field("severity", "Severity (1-5)", "number", value=3, min=1, max=5)]
    rows = [{"cells": [l.name, l.kind, l.disaster.name, l.population, l.severity],
             "actions": [("Update", url_for("admin.edit_location", id=l.id), "get")]} for l in Location.query.order_by(Location.id)]
    return render_template("crud.html", title="Locations", fields=fields, submit="Add location",
                           headers=["Name", "Kind", "Disaster", "Population", "Severity"], rows=rows)


@bp.route("/locations/<int:id>/edit", methods=["GET", "POST"])
def edit_location(id):
    l = db.get_or_404(Location, id)
    if request.method == "POST":
        def upd():
            l.population = intval(request.form.get("population"), 0, 10**8, "Population")
            l.severity = intval(request.form.get("severity"), 1, 5, "Severity")
        return save(upd, "Location updated.", "admin.locations")
    fields = [field("population", "Affected population", "number", value=l.population),
              field("severity", "Severity (1-5)", "number", value=l.severity, min=1, max=5)]
    return render_template("crud.html", title=f"Update {l.name}", fields=fields)


@bp.route("/resources", methods=["GET", "POST"])
def resources():
    if request.method == "POST":
        def add():
            n, u = request.form.get("name", "").strip(), request.form.get("unit", "").strip()
            if not n or not u:
                raise ValueError("Name and unit are required.")
            if Resource.query.filter_by(name=n).first():
                raise ValueError("That resource already exists.")
            db.session.add(Resource(name=n, unit=u))
        return save(add, "Resource added.", "admin.resources")
    return render_template("crud.html", title="Resources", fields=[field("name", "Name"), field("unit", "Unit (litres, kits, pieces)")],
                           submit="Add resource", headers=["Name", "Unit"], rows=[{"cells": [r.name, r.unit]} for r in Resource.query])


@bp.route("/inventory", methods=["GET", "POST"])
def inventory():
    if request.method == "POST":
        f = request.form

        def add():
            d, r = intval(f.get("depot_id"), 1, 10**9, "Depot"), intval(f.get("resource_id"), 1, 10**9, "Resource")
            q = intval(f.get("quantity"), 0, 10**9, "Quantity")
            s = Stock.query.filter_by(depot_id=d, resource_id=r).first() or Stock(depot_id=d, resource_id=r, quantity=0)
            s.threshold = intval(f.get("threshold"), 0, 10**9, "Low-stock level")
            s.quantity += q
            db.session.add(s)
            db.session.flush()
            if q:
                db.session.add(StockTransaction(stock_id=s.id, kind="received", quantity=q))
        return save(add, "Stock recorded.", "admin.inventory")
    depots = [(l.id, f"{l.name} ({l.disaster.name})") for l in Location.query.filter_by(kind="depot")]
    fields = [field("depot_id", "Depot", "select", depots), field("resource_id", "Resource", "select", opts(Resource)),
              field("quantity", "Quantity received", "number", value=0), field("threshold", "Low-stock alert at", "number", value=0)]
    rows = [{"cells": [s.depot.name, s.resource.name, f"{s.quantity} {s.resource.unit}", s.reserved, s.available,
                       "LOW" if s.available <= s.threshold else "OK"]} for s in Stock.query.order_by(Stock.depot_id)]
    return render_template("crud.html", title="Inventory", fields=fields, submit="Record received stock",
                           intro="Reserved stock is promised to approved deliveries. Available = on hand minus reserved.",
                           headers=["Depot", "Resource", "On hand", "Reserved", "Available", "Level"], rows=rows)


@bp.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        f = request.form

        def add():
            un, pw = f.get("username", "").strip(), f.get("password", "")
            if not un or len(pw) < 6:
                raise ValueError("Username is required and the password needs at least 6 characters.")
            if User.query.filter_by(username=un).first():
                raise ValueError("That username is taken.")
            u = User(username=un, role=f.get("role", "center"), full_name=f.get("full_name", ""),
                     location_id=int(f["location_id"]) if f.get("location_id") else None)
            u.set_password(pw)
            db.session.add(u)
        return save(add, "User created.", "admin.users")
    locs = [("", "None (admin)")] + [(l.id, l.name) for l in Location.query.filter(Location.kind != "depot")]
    fields = [field("username", "Username"), field("password", "Password", "password"), field("full_name", "Full name"),
              field("role", "Role", "select", [("center", "Relief center"), ("admin", "Admin")]), field("location_id", "Relief center location", "select", locs)]
    rows = [{"cells": [u.username, u.full_name, u.role, u.location.name if u.location else "-"]} for u in User.query]
    return render_template("crud.html", title="Users", fields=fields, submit="Create user",
                           headers=["Username", "Name", "Role", "Location"], rows=rows)


@bp.route("/stock-log")
def stock_log():
    rows = [{"cells": [t.ts.strftime("%d %b %H:%M"), t.stock.depot.name, t.stock.resource.name, t.kind, f"{t.quantity} {t.stock.resource.unit}"]}
            for t in StockTransaction.query.order_by(StockTransaction.id.desc()).limit(200)]
    return render_template("crud.html", title="Stock movements", intro="Every quantity received at or dispatched from a depot (latest 200).",
                           headers=["When", "Depot", "Resource", "Movement", "Quantity"], rows=rows)
