from collections import defaultdict
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .. import db
from ..models import Disaster, Request, Delivery, Stock, Resource, Notification
from ..services import available

bp = Blueprint("core", __name__)


def admin_only():
    from flask import abort
    if not current_user.is_admin:
        abort(403)


@bp.route("/")
def index():
    return redirect(url_for("core.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        open_reqs = Request.query.filter(Request.status.in_(("pending", "approved", "partial"))).all()
        tiles = [("Active disasters", Disaster.query.filter_by(status="active").count()),
                 ("Pending requests", Request.query.filter_by(status="pending").count()),
                 ("Deliveries in progress", Delivery.query.filter(Delivery.status.in_(("assigned", "dispatched"))).count()),
                 ("Open issues", Delivery.query.filter_by(status="issue").count())]
        alerts, demand = [], defaultdict(int)
        pend = defaultdict(int)
        for r in open_reqs:
            demand[r.resource_id] += r.unmet
            if r.status == "pending":
                pend[(r.disaster_id, r.resource_id)] += r.quantity
        for (d, rid), q in pend.items():
            a = available(d, rid)
            if q > a:
                res, dis = db.session.get(Resource, rid), db.session.get(Disaster, d)
                alerts.append(f"Shortage: {dis.name} needs {q} {res.unit} of {res.name} but only {a} is available.")
        for s in Stock.query.all():
            if s.available <= s.threshold:
                alerts.append(f"Low stock: {s.depot.name} has {s.available} {s.resource.unit} of {s.resource.name} left.")
        res = Resource.query.all()
        chart = {"labels": [r.name for r in res],
                 "stock": [sum(max(0, s.available) for s in Stock.query.filter_by(resource_id=r.id)) for r in res],
                 "unmet": [demand[r.id] for r in res]}
        return render_template("dashboard.html", tiles=tiles, alerts=alerts, chart=chart)
    mine = Request.query.filter_by(user_id=current_user.id).order_by(Request.created.desc()).all()
    tiles = [("My requests", len(mine)), ("Pending", sum(r.status == "pending" for r in mine)),
             ("Approved or partial", sum(r.status in ("approved", "partial") for r in mine)),
             ("Fulfilled", sum(r.status == "fulfilled" for r in mine))]
    dels = (Delivery.query.join(Request).filter(Request.user_id == current_user.id)
            .order_by(Delivery.created.desc()).limit(8).all())
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created.desc()).limit(5).all()
    return render_template("dashboard.html", tiles=tiles, mine=mine[:8], dels=dels, notes=notes)


@bp.route("/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    from flask import request
    if request.method == "POST":
        Notification.query.filter_by(user_id=current_user.id, read=False).update({"read": True})
        db.session.commit()
        return redirect(url_for("core.notifications"))
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created.desc()).limit(100).all()
    return render_template("crud.html", title="Notifications", headers=["When", "Message", "Status"],
                           rows=[{"cells": [n.created.strftime("%d %b %H:%M"), n.message, "Read" if n.read else "New"]} for n in rows],
                           post_button=("Mark all as read", url_for("core.notifications")))


@bp.route("/reports")
@login_required
def reports():
    admin_only()
    out, labels, req_q, got_q = [], [], [], []
    for r in Resource.query.all():
        rs = Request.query.filter(Request.resource_id == r.id, Request.status != "rejected").all()
        asked, given = sum(x.quantity for x in rs), sum(x.approved_qty or 0 for x in rs)
        labels.append(r.name); req_q.append(asked); got_q.append(given)
        out.append([r.name, asked, given, f"{round(100 * given / asked) if asked else 0}%", asked - given])
    statuses = ["assigned", "dispatched", "delivered", "issue"]
    counts = [Delivery.query.filter_by(status=s).count() for s in statuses]
    done = Delivery.query.filter_by(status="delivered").all()
    avg = round(sum((d.updated - d.created).total_seconds() for d in done) / len(done) / 3600, 1) if done else 0
    return render_template("reports.html", rows=out, avg=avg, statuses=statuses, counts=counts,
                           chart={"labels": labels, "requested": req_q, "allocated": got_q})


@bp.route("/reports.csv")
@login_required
def reports_csv():
    import csv, io
    from flask import Response
    admin_only()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Resource", "Requested", "Allocated", "Fulfilment", "Unmet"])
    for r in Resource.query.all():
        rs = Request.query.filter(Request.resource_id == r.id, Request.status != "rejected").all()
        asked, given = sum(x.quantity for x in rs), sum(x.approved_qty or 0 for x in rs)
        w.writerow([r.name, asked, given, f"{round(100 * given / asked) if asked else 0}%", asked - given])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=reliefgrid_report.csv"})
