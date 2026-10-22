
import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from email_validator import validate_email, EmailNotValidError

from .. import db
from ..models import User
from ..utils import field, intval

bp = Blueprint("auth", __name__)


def validate_username(username):
    """Validate email format without restricting the email provider."""
    if not username:
        return None

    try:
        result = validate_email(
            username.strip(),
            check_deliverability=False,
        )
        return result.normalized
    except EmailNotValidError:
        return None


def is_strong_password(password):
    """Require 12 characters, uppercase, lowercase, digit and symbol."""
    return (
        len(password) >= 12
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[^A-Za-z0-9]", password)
    )


@bp.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        email = validate_username(username)

        if not email:
            flash(
                "Enter a valid email address, such as "
                "name@gmail.com or name@outlook.com.",
                "error",
            )
            return render_template("login.html")

        # Find the account using the validated email.
        user = User.query.filter_by(username=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("core.dashboard"))

        flash("Wrong email or password.", "error")

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_view"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user

    if request.method == "POST":
        user.full_name = request.form.get(
            "full_name", ""
        ).strip()

        user.phone = request.form.get(
            "phone", ""
        ).strip()

        if (
            user.location
            and request.form.get("population") not in (None, "")
        ):
            try:
                user.location.population = intval(
                    request.form.get("population"),
                    0,
                    10**8,
                    "Affected population",
                )
            except ValueError as error:
                flash(str(error), "error")
                return redirect(url_for("auth.profile"))

        password = request.form.get("password", "")

        if password:
            if not is_strong_password(password):
                flash(
                    "Password must contain at least 12 characters, "
                    "including uppercase and lowercase letters, "
                    "a number, and a special character.",
                    "error",
                )
                return redirect(url_for("auth.profile"))

            user.set_password(password)

        db.session.commit()

        flash("Profile saved.", "ok")
        return redirect(url_for("auth.profile"))

    fields = [
        field("full_name", "Full name", value=user.full_name),
        field("phone", "Phone", value=user.phone),
        *(
            [
                field(
                    "population",
                    f"People currently affected at {user.location.name}",
                    "number",
                    value=user.location.population or 0,
                    min=0,
                )
            ]
            if user.location
            else []
        ),
        field(
            "password",
            "New password (leave blank to keep)",
            "password",
        ),
    ]

    return render_template(
        "crud.html",
        title="Profile",
        fields=fields,
        submit="Save profile",
        intro=(
            f"Signed in as {user.username} ({user.role})"
            + (
                f" for {user.location.name}"
                if user.location
                else ""
            )
        ),
    )
