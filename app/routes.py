from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask import current_app
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash
from . import db
from .models import User, SiteSetting, FragNightEvent, MachineGroup, Machine, Reservation, ReservationItem, PaymentLog
from .services.mercadopago_service import create_preference, get_payment
from .services import zapi_service

site_bp = Blueprint('site', __name__)
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
payment_bp = Blueprint('payment', __name__)

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

@site_bp.route('/')
def home():
    events = FragNightEvent.query.filter_by(status='published').order_by(FragNightEvent.event_date.desc()).all()
    active_event = FragNightEvent.query.filter_by(is_active=True).first()
    return render_template('site/home.html', events=events, active_event=active_event)

@site_bp.route('/evento/<slug>')
def event_detail(slug):
    event = FragNightEvent.query.filter_by(slug=slug).first_or_404()
    groups = MachineGroup.query.filter_by(event_id=event.id).all()
    selected = set()
    if current_user.is_authenticated:
        selected = {item.machine_id for r in current_user.reservations for item in r.items if r.event_id == event.id and r.payment_status in ['pending', 'paid']}
    return render_template('site/event_detail.html', event=event, groups=groups, selected=selected)

@site_bp.route('/checkout/<slug>', methods=['POST'])
@login_required
def checkout(slug):
    event = FragNightEvent.query.filter_by(slug=slug).first_or_404()
    machine_ids = request.form.getlist('machine_ids')
    payer_name = request.form.get('payer_name') or current_user.name
    payer_phone = request.form.get('payer_phone') or current_user.phone

    if not machine_ids:
        flash('Selecione pelo menos uma máquina.', 'error')
        return redirect(url_for('site.event_detail', slug=slug))

    machines = Machine.query.filter(Machine.id.in_(machine_ids), Machine.event_id == event.id).all()
    if len(machines) != len(machine_ids):
        flash('Algumas máquinas não foram encontradas.', 'error')
        return redirect(url_for('site.event_detail', slug=slug))

    # evita reservar máquinas já pagas/pedidas
    reserved_machine_ids = db.session.query(ReservationItem.machine_id).join(Reservation).filter(
        Reservation.event_id == event.id,
        Reservation.payment_status.in_(['pending', 'paid']),
        ReservationItem.machine_id.in_(machine_ids)
    ).all()
    reserved_machine_ids = {row[0] for row in reserved_machine_ids}
    if reserved_machine_ids:
        flash('Uma ou mais máquinas já foram reservadas. Atualize a página e tente novamente.', 'error')
        return redirect(url_for('site.event_detail', slug=slug))

    total = Decimal('0.00')
    reservation = Reservation(
        event_id=event.id,
        user_id=current_user.id,
        code=uuid4().hex[:12].upper(),
        total_amount=0,
        status='created',
        payment_status='pending',
        payer_name=payer_name,
        payer_phone=payer_phone
    )
    db.session.add(reservation)
    db.session.flush()

    for machine in machines:
        price = machine.group.price
        total += Decimal(price)
        db.session.add(ReservationItem(reservation_id=reservation.id, machine_id=machine.id, price=price))

    reservation.total_amount = total
    db.session.commit()

    try:
        pref = create_preference(reservation, f'Reserva FragNight - {event.title}')
        reservation.payment_reference = pref.get('id') or pref.get('preference_id')
        db.session.commit()
        return redirect(pref.get('init_point', url_for('site.my_reservations', _external=True)))
    except Exception as exc:
        flash(f'Não foi possível iniciar o pagamento agora: {exc}', 'error')
        return redirect(url_for('site.my_reservations'))

@site_bp.route('/minhas-reservas')
@login_required
def my_reservations():
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.created_at.desc()).all()
    return render_template('site/my_reservations.html', reservations=reservations)

@site_bp.route('/checkout/<status>/<code>')
def checkout_status(status, code):
    reservation = Reservation.query.filter_by(code=code).first_or_404()
    msg = {
        'sucesso': 'Pagamento aprovado com sucesso.',
        'falha': 'Pagamento não aprovado.',
        'pendente': 'Pagamento pendente.'
    }.get(status, 'Status atualizado.')
    flash(msg, 'success' if status == 'sucesso' else 'warning')
    return redirect(url_for('site.my_reservations'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login realizado com sucesso.', 'success')
            return redirect(url_for('site.home'))
        flash('Credenciais inválidas.', 'error')
    return render_template('auth/login.html')

@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'error')
            return redirect(url_for('auth.register'))
        user = User(
            name=request.form.get('name', ''),
            email=email,
            phone=request.form.get('phone', ''),
            password_hash=generate_password_hash(request.form.get('password', ''))
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Conta criada com sucesso.', 'success')
        return redirect(url_for('site.home'))
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da conta.', 'success')
    return redirect(url_for('site.home'))

@admin_bp.route('/')
@login_required
def dashboard():
    admin_required()
    events = FragNightEvent.query.order_by(FragNightEvent.event_date.desc()).all()
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).limit(10).all()
    total_paid = db.session.query(db.func.coalesce(db.func.sum(Reservation.total_amount), 0)).filter(Reservation.payment_status == 'paid').scalar()
    return render_template('admin/dashboard.html', events=events, reservations=reservations, total_paid=total_paid)

@admin_bp.route('/eventos', methods=['GET', 'POST'])
@login_required
def events():
    admin_required()
    if request.method == 'POST':
        if request.form.get('action') == 'create':
            slug = request.form.get('slug') or request.form.get('title', '').lower().replace(' ', '-').replace('/', '-')
            if request.form.get('make_active'):
                FragNightEvent.query.update({'is_active': False})
            event = FragNightEvent(
                title=request.form.get('title'),
                slug=slug,
                event_date=datetime.strptime(request.form.get('event_date'), '%Y-%m-%d').date(),
                starts_at=datetime.strptime(request.form.get('starts_at'), '%Y-%m-%dT%H:%M') if request.form.get('starts_at') else None,
                ends_at=datetime.strptime(request.form.get('ends_at'), '%Y-%m-%dT%H:%M') if request.form.get('ends_at') else None,
                description=request.form.get('description'),
                hero_text=request.form.get('hero_text'),
                status=request.form.get('status', 'draft'),
                is_active=bool(request.form.get('make_active'))
            )
            db.session.add(event)
            db.session.commit()
            flash('Evento criado.', 'success')
        elif request.form.get('action') == 'activate':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            FragNightEvent.query.update({'is_active': False})
            event.is_active = True
            db.session.commit()
            flash('Evento definido como ativo.', 'success')
        elif request.form.get('action') == 'delete':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            db.session.delete(event)
            db.session.commit()
            flash('Evento removido.', 'success')
        return redirect(url_for('admin.events'))
    events = FragNightEvent.query.order_by(FragNightEvent.event_date.desc()).all()
    return render_template('admin/events.html', events=events)

@admin_bp.route('/evento/<int:event_id>/grupos', methods=['GET', 'POST'])
@login_required
def event_groups(event_id):
    admin_required()
    event = FragNightEvent.query.get_or_404(event_id)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_group':
            group = MachineGroup(
                event_id=event.id,
                name=request.form.get('name'),
                location_label=request.form.get('location_label'),
                quantity=int(request.form.get('quantity', 10)),
                price=request.form.get('price', 0),
                specs=request.form.get('specs'),
                color=request.form.get('color', '#ef4444'),
            )
            db.session.add(group)
            db.session.flush()

            existing_count = Machine.query.filter_by(event_id=event.id).count()
            for i in range(group.quantity):
                label = str(existing_count + i + 1)
                db.session.add(Machine(event_id=event.id, group_id=group.id, label=label, status='available'))
            db.session.commit()
            flash('Grupo e máquinas criados.', 'success')
        elif action == 'delete_group':
            group = MachineGroup.query.get_or_404(request.form.get('group_id'))
            db.session.delete(group)
            db.session.commit()
            flash('Grupo removido.', 'success')
        return redirect(url_for('admin.event_groups', event_id=event.id))
    groups = MachineGroup.query.filter_by(event_id=event.id).all()
    machines = Machine.query.filter_by(event_id=event.id).order_by(db.cast(Machine.label, db.Integer)).all()
    return render_template('admin/event_groups.html', event=event, groups=groups, machines=machines)

@admin_bp.route('/vendas')
@login_required
def sales():
    admin_required()
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template('admin/sales.html', reservations=reservations)

@admin_bp.route('/apis', methods=['GET', 'POST'])
@login_required
def apis():
    admin_required()
    if request.method == 'POST':
        for key in ['mp_access_token', 'mp_public_key', 'zapi_base_url', 'zapi_instance_id', 'zapi_instance_token', 'zapi_client_token', 'zapi_notify_phone']:
            SiteSetting.set(key, request.form.get(key, ''), is_secret=('token' in key or 'key' in key))
        db.session.commit()
        flash('Credenciais atualizadas.', 'success')
        return redirect(url_for('admin.apis'))
    return render_template('admin/apis.html')

@admin_bp.route('/apis/zapi/status')
@login_required
def zapi_status():
    admin_required()
    try:
        data = zapi_service.status()
    except Exception as exc:
        data = {'error': str(exc)}
    return jsonify(data)

@admin_bp.route('/apis/zapi/qr')
@login_required
def zapi_qr():
    admin_required()
    try:
        data = zapi_service.get_qr()
    except Exception as exc:
        data = {'error': str(exc)}
    return jsonify(data)

@payment_bp.route('/webhook/mercadopago', methods=['POST'])
def mercadopago_webhook():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    payment_id = None
    action = payload.get('action')
    data = payload.get('data') or {}
    if isinstance(data, dict):
        payment_id = data.get('id')
    payment_id = payment_id or payload.get('id') or request.args.get('id')
    log = PaymentLog(provider='mercadopago', external_id=str(payment_id) if payment_id else None, payload=str(payload), status='received')
    db.session.add(log)
    db.session.commit()

    if not payment_id:
        return jsonify({'ok': True, 'message': 'Webhook recebido sem payment id'}), 200

    try:
        payment = get_payment(payment_id)
        external_reference = payment.get('external_reference')
        status = payment.get('status')
        reservation = Reservation.query.filter_by(code=external_reference).first()
        if reservation:
            reservation.payment_status = 'paid' if status == 'approved' else status
            reservation.status = 'confirmed' if status == 'approved' else reservation.status
            reservation.payment_reference = str(payment_id)
            log.reservation_id = reservation.id
            log.status = status
            db.session.commit()

            if status == 'approved':
                items = ', '.join([item.machine.label for item in reservation.items])
                message = (
                    f"✅ Novo pagamento aprovado no FragNight\n"
                    f"Evento: {reservation.event.title}\n"
                    f"Cliente: {reservation.payer_name or reservation.user.name}\n"
                    f"Telefone: {reservation.payer_phone or reservation.user.phone or '-'}\n"
                    f"Máquinas: {items}\n"
                    f"Total: R$ {reservation.total_amount}"
                )
                try:
                    zapi_service.notify_admin(message)
                except Exception:
                    pass
        return jsonify({'ok': True}), 200
    except Exception as exc:
        log.status = f'error: {exc}'
        db.session.commit()
        return jsonify({'ok': False, 'error': str(exc)}), 200
