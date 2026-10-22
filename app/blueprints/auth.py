from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .. import db
from ..models import User
from ..utils import field, intval

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if u and u.check_password(request.form.get("password", "")):
            login_user(u)
            return redirect(url_for("core.dashboard"))
        flash("Wrong username or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_view"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    u = current_user
    if request.method == "POST":
        u.full_name = request.form.get("full_name", "").strip()
        u.phone = request.form.get("phone", "").strip()
        if u.location and request.form.get("population") not in (None, ""):
            try:
                u.location.population = intval(request.form.get("population"), 0, 10**8, "Affected population")
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("auth.profile"))
        pw = request.form.get("password", "")
        if pw:
            if len(pw) < 6:
                flash("Password must have at least 6 characters.", "error")
                return redirect(url_for("auth.profile"))
            u.set_password(pw)
        db.session.commit()
        flash("Profile saved.", "ok")
        return redirect(url_for("auth.profile"))
    fields = [field("full_name", "Full name", value=u.full_name), field("phone", "Phone", value=u.phone),
              *([field("population", f"People currently affected at {u.location.name}", "number", value=u.location.population or 0, min=0)] if u.location else []),
              field("password", "New password (leave blank to keep)", "password")]
    return render_template("crud.html", title="Profile", fields=fields, submit="Save profile",
                           intro=f"Signed in as {u.username} ({u.role})"
                                 + (f" for {u.location.name}" if u.location else ""))
