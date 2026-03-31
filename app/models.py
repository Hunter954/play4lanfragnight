from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from . import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class User(UserMixin, db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SiteSetting(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    is_secret = db.Column(db.Boolean, default=False)

    @classmethod
    def get(cls, key, default=''):
        item = cls.query.filter_by(key=key).first()
        return item.value if item and item.value is not None else default

    @classmethod
    def set(cls, key, value, is_secret=False):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key)
            db.session.add(item)
        item.value = value
        item.is_secret = is_secret
        return item

    @classmethod
    def get_dict(cls):
        items = cls.query.all()
        return {item.key: item.value for item in items}

class FragNightEvent(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(170), unique=True, nullable=False)
    event_date = db.Column(db.Date, nullable=False, default=date.today)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    hero_text = db.Column(db.Text, nullable=True)
    hero_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default='draft')
    is_active = db.Column(db.Boolean, default=False)
    groups = db.relationship('MachineGroup', backref='event', lazy=True, cascade='all, delete-orphan')
    machines = db.relationship('Machine', backref='event', lazy=True, cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='event', lazy=True)

class MachineGroup(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('frag_night_event.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    location_label = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, default=10)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    specs = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(20), default='#ef4444')
    machines = db.relationship('Machine', backref='group', lazy=True, cascade='all, delete-orphan')

class Machine(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('frag_night_event.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('machine_group.id'), nullable=False)
    label = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default='available')
    reservations = db.relationship('ReservationItem', backref='machine', lazy=True)

class Reservation(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('frag_night_event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(30), default='pending')
    payment_status = db.Column(db.String(30), default='pending')
    payment_provider = db.Column(db.String(30), default='mercadopago')
    payment_reference = db.Column(db.String(120), nullable=True)
    payer_name = db.Column(db.String(120), nullable=True)
    payer_phone = db.Column(db.String(30), nullable=True)
    items = db.relationship('ReservationItem', backref='reservation', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('PaymentLog', backref='reservation', lazy=True)

class ReservationItem(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)

class PaymentLog(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'), nullable=True)
    provider = db.Column(db.String(30), nullable=False, default='mercadopago')
    external_id = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), nullable=True)
    payload = db.Column(db.Text, nullable=True)
