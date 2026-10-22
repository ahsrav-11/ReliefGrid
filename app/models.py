from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="center")  # admin | center
    full_name = db.Column(db.String(120), default="")
    phone = db.Column(db.String(30), default="")
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    location = db.relationship("Location")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def is_admin(self):
        return self.role == "admin"


@login.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


class Disaster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    severity = db.Column(db.Integer, nullable=False, default=3)  # 1-5
    status = db.Column(db.String(10), nullable=False, default="active")  # active | closed
    description = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disaster.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # affected | shelter | center | depot
    population = db.Column(db.Integer, default=0)
    severity = db.Column(db.Integer, default=3)  # 1-5
    disaster = db.relationship("Disaster")


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    unit = db.Column(db.String(20), nullable=False)


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    depot_id = db.Column(db.Integer, db.ForeignKey("location.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved = db.Column(db.Integer, nullable=False, default=0)  # promised to deliveries
    threshold = db.Column(db.Integer, nullable=False, default=0)
    depot = db.relationship("Location")
    resource = db.relationship("Resource")

    @property
    def available(self):
        return self.quantity - self.reserved


class StockTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    kind = db.Column(db.String(12), nullable=False)  # received | dispatched
    quantity = db.Column(db.Integer, nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    stock = db.relationship("Stock")


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), nullable=False)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disaster.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    urgency = db.Column(db.Integer, nullable=False)  # 1-5
    population = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(12), default="pending")  # pending|approved|partial|rejected|fulfilled
    approved_qty = db.Column(db.Integer, default=0)
    score = db.Column(db.Float)
    explanation = db.Column(db.Text, default="")
    note = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")
    location = db.relationship("Location")
    disaster = db.relationship("Disaster")
    resource = db.relationship("Resource")

    @property
    def unmet(self):
        return 0 if self.status in ("rejected", "fulfilled") else self.quantity - (self.approved_qty or 0)


class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("request.id"), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(12), default="assigned")  # assigned|dispatched|delivered|issue
    note = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    request = db.relationship("Request")
    stock = db.relationship("Stock")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
