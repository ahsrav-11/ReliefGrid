from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .. import db
from ..models import Request, Resource
from ..services import assign_deliveries
from ..utils import field, intval, notify, notify_admins

bp = Blueprint("requests", __name__)


@bp.route("/requests")
@login_required
def list_requests():
    q = Request.query.order_by(Request.created.desc())
    if not current_user.is_admin:
        q = q.filter_by(user_id=current_user.id)
    status = request.args.get("status", "")
    if status in ("pending", "approved", "partial", "rejected", "fulfilled"):
        q = q.filter_by(status=status)
    rows = []
    for r in q:
        acts = [("Review", url_for("requests.review", id=r.id), "get")] if current_user.is_admin and r.status == "pending" else []
        rows.append({"cells": [r.id, r.location.name, r.resource.name, f"{r.quantity} {r.resource.unit}", r.urgency, r.status,
                               r.approved_qty or 0, r.unmet, r.explanation or r.note], "actions": acts})
    chips = " | ".join(f'<a href="{url_for("requests.list_requests", status=k)}">{lbl}</a>' for k, lbl in
                       [("", "All"), ("pending", "Pending"), ("approved", "Approved"), ("partial", "Partial"),
                        ("fulfilled", "Fulfilled"), ("rejected", "Rejected")])
    return render_template("crud.html", title="Requests", intro_html=chips, headers=["#", "Location", "Resource", "Requested", "Urgency", "Status", "Approved", "Unmet", "Why / note"],
                           rows=rows, top_link=None if current_user.is_admin else ("New request", url_for("requests.new")))


@bp.route("/requests/new", methods=["GET", "POST"])
@login_required
def new():
    loc = current_user.location
    if current_user.is_admin or not loc:
        abort(403)
    if loc.disaster.status != "active":
        flash("This disaster is closed, so new requests cannot be sent.", "error")
        return redirect(url_for("requests.list_requests"))
    if request.method == "POST":
        f = request.form
        try:
            res = db.session.get(Resource, intval(f.get("resource_id"), 1, 10**9, "Resource"))
            if not res:
                raise ValueError("Pick a valid resource.")
            r = Request(user_id=current_user.id, location_id=loc.id, disaster_id=loc.disaster_id,
                        resource_id=res.id,
                        quantity=intval(f.get("quantity"), 1, 10**9, "Quantity"),
                        urgency=intval(f.get("urgency"), 1, 5, "Urgency"),
                        population=intval(f.get("population"), 1, 10**8, "People affected"), note=f.get("note", ""))
            db.session.add(r)
            notify_admins(f"New request from {loc.name}: {r.quantity} {res.unit} of {res.name}, urgency {r.urgency}.")
            db.session.commit()
            flash("Request sent.", "ok")
            return redirect(url_for("requests.list_requests"))
        except ValueError as e:
            flash(str(e), "error")
    fields = [field("resource_id", "Resource", "select", [(r.id, f"{r.name} ({r.unit})") for r in Resource.query]),
              field("quantity", "Quantity needed", "number", value=1, min=1),
              field("urgency", "Urgency (1 = low, 5 = life-threatening)", "number", value=3, min=1, max=5),
              field("population", "People affected", "number", value=loc.population or 1, min=1), field("note", "Note", "textarea")]
    return render_template("crud.html", title=f"New request for {loc.name}", fields=fields, submit="Send request")


@bp.route("/requests/<int:id>/review", methods=["GET", "POST"])
@login_required
def review(id):
    if not current_user.is_admin:
        abort(403)
    r = db.get_or_404(Request, id)
    if r.status != "pending":
        flash("Only pending requests can be reviewed.", "error")
        return redirect(url_for("requests.list_requests"))
    if request.method == "POST":
        try:
            if request.form.get("decision") == "reject":
                r.status, r.note = "rejected", request.form.get("note", "")
                notify(r.user_id, f"Your request #{r.id} was rejected. {r.note}")
            else:
                qty = intval(request.form.get("qty"), 1, r.quantity, "Approved quantity")
                assign_deliveries(r, qty)
                notify(r.user_id, f"Your request #{r.id} was {r.status}: {qty} of {r.quantity} {r.resource.unit} of {r.resource.name}.")
            db.session.commit()
            flash("Decision saved.", "ok")
            return redirect(url_for("requests.list_requests"))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
    fields = [field("decision", "Decision", "select", [("approve", "Approve (full or partial)"), ("reject", "Reject")]),
              field("qty", f"Approved quantity (max {r.quantity})", "number", value=r.quantity, min=1), field("note", "Note to requester", "textarea")]
    return render_template("crud.html", title=f"Review request #{r.id}", fields=fields, submit="Save decision",
                           intro=f"{r.location.name} asks for {r.quantity} {r.resource.unit} of {r.resource.name}, urgency {r.urgency}/5, {r.population} people.")
