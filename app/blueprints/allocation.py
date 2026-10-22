from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .. import db
from ..allocation_engine import allocate
from ..models import Disaster, Resource, Request
from ..services import available, assign_deliveries
from ..utils import intval, notify

bp = Blueprint("allocation", __name__)


@bp.before_request
@login_required
def guard():
    if not current_user.is_admin:
        abort(403)


def plan_for(disaster_id, resource_id, mode, demand_pct=100, supply_pct=100):
    reqs = Request.query.filter_by(disaster_id=disaster_id, resource_id=resource_id, status="pending").all()
    supply = available(disaster_id, resource_id)
    items = [dict(id=r.id, quantity=max(1, round(r.quantity * demand_pct / 100)), urgency=r.urgency,
                  population=r.population, severity=r.location.severity) for r in reqs]
    plan = allocate(items, int(supply * supply_pct / 100), mode)
    by_id = {r.id: r for r in reqs}
    for p in plan:
        p["location"] = by_id[p["id"]].location.name
    return plan, int(supply * supply_pct / 100), by_id


def choices():
    return Disaster.query.filter_by(status="active").all(), Resource.query.all()


def read_params(src):
    return (intval(src.get("disaster_id"), 1, 10**9, "Disaster"), intval(src.get("resource_id"), 1, 10**9, "Resource"),
            src.get("mode", "priority") if src.get("mode") in ("priority", "proportional") else "priority")


@bp.route("/allocation", methods=["GET", "POST"])
def run():
    ds, rs = choices()
    ctx = dict(ds=ds, rs=rs, plan=None, form=request.values)
    if request.values.get("disaster_id"):
        try:
            d, r, mode = read_params(request.values)
            ctx["plan"], ctx["supply"], _ = plan_for(d, r, mode)
            ctx["chart"] = {"labels": [p["location"] for p in ctx["plan"]], "asked": [p["quantity"] for p in ctx["plan"]],
                            "given": [p["allocated"] for p in ctx["plan"]]}
        except ValueError as e:
            flash(str(e), "error")
    return render_template("plan.html", **ctx)


@bp.route("/allocation/apply", methods=["POST"])
def apply():
    try:
        d, r, mode = read_params(request.form)
        plan, supply, by_id = plan_for(d, r, mode)
        for p in plan:
            req = by_id[p["id"]]
            req.score, req.explanation = p["score"], p["explanation"]
            if p["allocated"] > 0:
                assign_deliveries(req, p["allocated"])
                notify(req.user_id, f"Request #{req.id} is {req.status}: {p['allocated']} of {req.quantity} {req.resource.unit}.")
        db.session.commit()
        flash("Plan applied. Deliveries were created and stock was reserved.", "ok")
        return redirect(url_for("delivery.list_deliveries"))
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(url_for("allocation.run"))


@bp.route("/simulation", methods=["GET", "POST"])
def simulate():
    ds, rs = choices()
    ctx = dict(ds=ds, rs=rs, form=request.values, cmp=None)
    if request.values.get("disaster_id"):
        try:
            d, r, mode = read_params(request.values)
            dp = intval(request.values.get("demand_pct", 100), 10, 500, "Demand")
            sp = intval(request.values.get("supply_pct", 100), 0, 500, "Supply")
            base, bsup, _ = plan_for(d, r, mode)
            scen, ssup, _ = plan_for(d, r, mode, dp, sp)
            bmap = {p["id"]: p for p in base}
            rows = [dict(p, base_alloc=bmap[p["id"]]["allocated"], base_unmet=bmap[p["id"]]["unmet"],
                         base_rank=bmap[p["id"]]["rank"]) for p in scen]
            ctx["cmp"] = dict(rows=rows, bsup=bsup, ssup=ssup, base_unmet=sum(p["unmet"] for p in base),
                              scen_unmet=sum(p["unmet"] for p in scen))
            ctx["chart"] = {"labels": [x["location"] for x in rows], "base": [x["base_alloc"] for x in rows],
                            "scen": [x["allocated"] for x in rows]}
        except ValueError as e:
            flash(str(e), "error")
    return render_template("simulation.html", **ctx)
