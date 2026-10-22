from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .. import db
from ..models import Delivery, StockTransaction
from ..utils import field, notify, notify_admins

bp = Blueprint("delivery", __name__)


@bp.route("/deliveries")
@login_required
def list_deliveries():
    q = Delivery.query.join(Delivery.request).order_by(Delivery.created.desc())
    if not current_user.is_admin:
        from ..models import Request
        q = q.filter(Request.user_id == current_user.id)
    rows = []
    for d in q:
        acts = []
        if current_user.is_admin and d.status == "assigned":
            acts = [("Dispatch", url_for("delivery.dispatch", id=d.id), "post")]
        elif current_user.is_admin and d.status == "issue":
            acts = [("Resolve and resend", url_for("delivery.dispatch", id=d.id), "post")]
        elif d.status == "dispatched" and d.request.user_id == current_user.id:
            acts = [("Confirm receipt", url_for("delivery.confirm", id=d.id), "post"),
                    ("Report issue", url_for("delivery.issue", id=d.id), "get")]
        rows.append({"cells": [d.id, d.request_id, d.request.location.name, d.request.resource.name, d.quantity,
                               d.stock.depot.name, d.status, d.updated.strftime("%d %b %H:%M"), d.note], "actions": acts})
    return render_template("crud.html", title="Deliveries",
                           headers=["#", "Request", "To", "Resource", "Qty", "From depot", "Status", "Updated", "Note"], rows=rows)


@bp.route("/deliveries/<int:id>/dispatch", methods=["POST"])
@login_required
def dispatch(id):
    if not current_user.is_admin:
        abort(403)
    d = db.get_or_404(Delivery, id)
    if d.status == "assigned":
        d.stock.quantity -= d.quantity
        d.stock.reserved -= d.quantity
        db.session.add(StockTransaction(stock_id=d.stock_id, kind="dispatched", quantity=d.quantity))
    elif d.status != "issue":
        abort(400)
    d.status, d.updated = "dispatched", datetime.utcnow()
    notify(d.request.user_id, f"{d.quantity} {d.request.resource.unit} of {d.request.resource.name} is on the way from {d.stock.depot.name}.")
    db.session.commit()
    flash("Delivery dispatched.", "ok")
    return redirect(url_for("delivery.list_deliveries"))


def own_delivery(id):
    d = db.get_or_404(Delivery, id)
    if d.request.user_id != current_user.id or d.status != "dispatched":
        abort(403)
    return d


@bp.route("/deliveries/<int:id>/confirm", methods=["POST"])
@login_required
def confirm(id):
    d = own_delivery(id)
    d.status, d.updated = "delivered", datetime.utcnow()
    # Only a request that was approved in full becomes "fulfilled"; a partial one keeps its unmet demand visible.
    if (d.request.approved_qty == d.request.quantity
            and all(x.status == "delivered" for x in Delivery.query.filter_by(request_id=d.request_id))):
        d.request.status = "fulfilled"
    notify_admins(f"Delivery #{d.id} to {d.request.location.name} was confirmed.")
    db.session.commit()
    flash("Receipt confirmed.", "ok")
    return redirect(url_for("delivery.list_deliveries"))


@bp.route("/deliveries/<int:id>/issue", methods=["GET", "POST"])
@login_required
def issue(id):
    d = own_delivery(id)
    if request.method == "POST":
        d.status, d.note, d.updated = "issue", request.form.get("note", "Issue reported"), datetime.utcnow()
        notify_admins(f"Issue reported on delivery #{d.id}: {d.note}")
        db.session.commit()
        flash("Issue reported to the admin team.", "ok")
        return redirect(url_for("delivery.list_deliveries"))
    return render_template("crud.html", title=f"Report issue with delivery #{d.id}", submit="Report issue",
                           fields=[field("note", "What went wrong? (short, damaged, late)", "textarea")])
