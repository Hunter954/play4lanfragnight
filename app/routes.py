from decimal import Decimal
import re
import unicodedata
from datetime import datetime, timedelta
import calendar
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

FIXED_LAYOUTS = {
    'sala_gamer': ['25', '24', '23', '22', '21', '26', '27', '28', '29', '30'],
    'fora_meio': ['15', '14', '13', '12', '11', '06', '07', '08', '09', '10'],
    'fora_parede': ['16', '17', '18', '19', '20', '05', '04', '03', '02', '01'],
}

SECTION_META = {
    'sala_gamer': {'title': 'SALA ALIENWARE', 'order': 1, 'short_title': 'Alienware'},
    'fora_meio': {'title': 'PC GAMER', 'order': 2, 'short_title': 'PC Gamer'},
    'fora_parede': {'title': 'PC DELL', 'order': 3, 'short_title': 'PC Dell'},
    'outros': {'title': 'OUTROS', 'order': 99, 'short_title': 'Outros'},
}

def split_location_label(value):
    value = (value or '').strip()
    if '|' in value:
        key, display = value.split('|', 1)
        return key.strip(), display.strip()
    normalized = value.lower().strip()
    if 'sala' in normalized or 'gamer' in normalized:
        return 'sala_gamer', value
    if 'parede' in normalized:
        return 'fora_parede', value
    if 'fora' in normalized or 'meio' in normalized:
        return 'fora_meio', value
    return 'outros', value


def format_specs_lines(specs):
    specs = (specs or '').strip()
    if not specs:
        return ['Configuração não cadastrada.']
    if '\n' in specs:
        lines = [line.strip() for line in specs.splitlines() if line.strip()]
    else:
        lines = [line.strip() for line in specs.split(',') if line.strip()]
    return lines or ['Configuração não cadastrada.']



def summarize_event(event):
    groups = MachineGroup.query.filter_by(event_id=event.id).all()
    reserved_rows = db.session.query(ReservationItem.machine_id).join(Reservation).filter(
        Reservation.event_id == event.id,
        Reservation.payment_status.in_(['pending', 'paid'])
    ).all()
    unavailable_machine_ids = {row[0] for row in reserved_rows}
    sections = build_machine_sections(groups, unavailable_machine_ids)
    total_machines = sum(len(group.machines) for group in groups)
    reserved_count = len(unavailable_machine_ids)
    available_count = max(total_machines - reserved_count, 0)
    lowest_price = min((float(group.price) for group in groups), default=0)
    weekday_names = {
        0: 'SEGUNDA-FEIRA',
        1: 'TERCA-FEIRA',
        2: 'QUARTA-FEIRA',
        3: 'QUINTA-FEIRA',
        4: 'SEXTA-FEIRA',
        5: 'SABADO',
        6: 'DOMINGO',
    }
    section_counts = {section['short_title']: section['available_count'] for section in sections}
    section_map = {
        section['key']: {
            'title': section['title'],
            'short_title': section['short_title'],
            'available_count': section['available_count'],
            'price': float(section['group'].price or 0),
        }
        for section in sections
    }
    return {
        'event': event,
        'total_machines': total_machines,
        'reserved_count': reserved_count,
        'available_count': available_count,
        'lowest_price': lowest_price,
        'weekday_label': weekday_names.get(event.event_date.weekday(), event.event_date.strftime('%A').upper()),
        'section_counts': section_counts,
        'section_map': section_map,
    }


def build_machine_sections(groups, unavailable_machine_ids=None):
    unavailable_machine_ids = unavailable_machine_ids or set()
    sections = []
    for group in groups:
        section_key, display_label = split_location_label(group.location_label or group.name)
        ordered_labels = FIXED_LAYOUTS.get(section_key, [m.label for m in group.machines])
        machine_by_label = {m.label.zfill(2): m for m in group.machines}
        machine_by_label.update({m.label: m for m in group.machines})
        ordered_machines = []
        for label in ordered_labels:
            machine = machine_by_label.get(label)
            if machine:
                ordered_machines.append(machine)
        if section_key not in FIXED_LAYOUTS:
            remainder = [m for m in group.machines if m not in ordered_machines]
            remainder.sort(key=lambda m: m.label)
            ordered_machines.extend(remainder)
        spec_lines = format_specs_lines(group.specs)
        specs_html = '<br>'.join(spec_lines)
        total_count = len(ordered_machines)
        available_count = sum(1 for machine in ordered_machines if machine.id not in unavailable_machine_ids)
        sections.append({
            'key': section_key,
            'title': SECTION_META.get(section_key, SECTION_META['outros'])['title'],
            'short_title': SECTION_META.get(section_key, SECTION_META['outros'])['short_title'],
            'display_label': display_label or group.name,
            'group': group,
            'machines': ordered_machines,
            'spec_lines': spec_lines,
            'specs_html': specs_html,
            'total_count': total_count,
            'available_count': available_count,
            'reserved_count': max(total_count - available_count, 0),
        })
    sections.sort(key=lambda item: (SECTION_META.get(item['key'], SECTION_META['outros'])['order'], item['group'].id))
    return sections



def parse_local_datetime(value):
    value = (value or '').strip()
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%dT%H:%M')


def build_default_event_times(event_date_value):
    start = datetime.combine(event_date_value, datetime.min.time()).replace(hour=22, minute=0)
    end = start + timedelta(hours=8)
    return start, end


def clone_event_groups(source_event, target_event):
    group_map = {}
    source_groups = MachineGroup.query.filter_by(event_id=source_event.id).order_by(MachineGroup.id.asc()).all()
    for source_group in source_groups:
        new_group = MachineGroup(
            event_id=target_event.id,
            name=source_group.name,
            location_label=source_group.location_label,
            quantity=source_group.quantity,
            price=source_group.price,
            specs=source_group.specs,
            color=source_group.color,
        )
        db.session.add(new_group)
        db.session.flush()
        group_map[source_group.id] = new_group.id

    source_machines = Machine.query.filter_by(event_id=source_event.id).order_by(Machine.id.asc()).all()
    for source_machine in source_machines:
        db.session.add(Machine(
            event_id=target_event.id,
            group_id=group_map[source_machine.group_id],
            label=source_machine.label,
            status='available',
        ))

@site_bp.route('/')
def home():
    events = FragNightEvent.query.filter_by(status='published').order_by(FragNightEvent.event_date.desc()).all()
    active_event = FragNightEvent.query.filter_by(is_active=True).first()
    featured_events = sorted(events, key=lambda event: (not event.is_active, event.event_date))[:2]
    featured_event_summaries = [summarize_event(event) for event in featured_events]
    return render_template('site/home.html', events=events, active_event=active_event, featured_event_summaries=featured_event_summaries)

@site_bp.route('/evento/<slug>')
def event_detail(slug):
    event = FragNightEvent.query.filter_by(slug=slug).first_or_404()
    groups = MachineGroup.query.filter_by(event_id=event.id).order_by(MachineGroup.id.asc()).all()
    reserved_rows = db.session.query(ReservationItem.machine_id).join(Reservation).filter(
        Reservation.event_id == event.id,
        Reservation.payment_status.in_(['pending', 'paid'])
    ).all()
    unavailable_machine_ids = {row[0] for row in reserved_rows}
    sections = build_machine_sections(groups, unavailable_machine_ids)
    weekday_names = {
        0: 'SEGUNDA-FEIRA',
        1: 'TERCA-FEIRA',
        2: 'QUARTA-FEIRA',
        3: 'QUINTA-FEIRA',
        4: 'SEXTA-FEIRA',
        5: 'SABADO',
        6: 'DOMINGO',
    }
    total_available_count = sum(section['available_count'] for section in sections)
    weekday_label = weekday_names.get(event.event_date.weekday(), event.event_date.strftime('%A').upper())
    return render_template(
        'site/event_detail.html',
        event=event,
        groups=groups,
        sections=sections,
        unavailable_machine_ids=unavailable_machine_ids,
        total_available_count=total_available_count,
        weekday_label=weekday_label,
    )

@site_bp.route('/checkout/<slug>', methods=['POST'])
@login_required
def checkout(slug):
    event = FragNightEvent.query.filter_by(slug=slug).first_or_404()
    machine_ids = request.form.getlist('machine_ids')
    payer_name = current_user.name
    payer_phone = current_user.phone

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
        pref = create_preference(reservation, f'Reserva Frag-Night - {event.title}')
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



def delete_event_and_dependencies(event):
    default_template_id = SiteSetting.get('default_event_template_id', '')
    if default_template_id and str(default_template_id) == str(event.id):
        SiteSetting.set('default_event_template_id', '')

    reservations = Reservation.query.filter_by(event_id=event.id).all()
    reservation_ids = [reservation.id for reservation in reservations]

    if reservation_ids:
        ReservationItem.query.filter(ReservationItem.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
        PaymentLog.query.filter(PaymentLog.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
        Reservation.query.filter(Reservation.id.in_(reservation_ids)).delete(synchronize_session=False)

    Machine.query.filter_by(event_id=event.id).delete(synchronize_session=False)
    MachineGroup.query.filter_by(event_id=event.id).delete(synchronize_session=False)
    db.session.delete(event)


@admin_bp.route('/eventos', methods=['GET', 'POST'])
@login_required
def events():
    admin_required()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            slug = unique_event_slug(request.form.get('slug') or request.form.get('title'))
            event_date_value = datetime.strptime(request.form.get('event_date'), '%Y-%m-%d').date()
            starts_at = parse_local_datetime(request.form.get('starts_at'))
            ends_at = parse_local_datetime(request.form.get('ends_at'))
            if request.form.get('use_default_time') and not starts_at and not ends_at:
                starts_at, ends_at = build_default_event_times(event_date_value)
            if request.form.get('make_active'):
                FragNightEvent.query.update({'is_active': False})
            event = FragNightEvent(
                title=request.form.get('title'),
                slug=slug,
                event_date=event_date_value,
                starts_at=starts_at,
                ends_at=ends_at,
                description=request.form.get('description'),
                hero_text=request.form.get('hero_text'),
                status=request.form.get('status', 'draft'),
                is_active=bool(request.form.get('make_active'))
            )
            db.session.add(event)
            db.session.commit()
            flash('Evento criado.', 'success')

        elif action == 'create_from_default':
            template_id = request.form.get('template_event_id') or SiteSetting.get('default_event_template_id', '')
            source_event = FragNightEvent.query.get_or_404(int(template_id))
            event_date_value = datetime.strptime(request.form.get('event_date'), '%Y-%m-%d').date()
            starts_at, ends_at = build_default_event_times(event_date_value)
            slug_seed = request.form.get('slug') or request.form.get('title') or f"{source_event.title} {event_date_value.strftime('%d-%m-%Y')}"
            slug = unique_event_slug(slug_seed)
            if request.form.get('make_active'):
                FragNightEvent.query.update({'is_active': False})
            event = FragNightEvent(
                title=request.form.get('title') or f"{source_event.title} {event_date_value.strftime('%d/%m/%Y')}",
                slug=slug,
                event_date=event_date_value,
                starts_at=starts_at,
                ends_at=ends_at,
                description=request.form.get('description') or source_event.description,
                hero_text=request.form.get('hero_text') or source_event.hero_text,
                status=request.form.get('status', source_event.status or 'draft'),
                is_active=bool(request.form.get('make_active'))
            )
            db.session.add(event)
            db.session.flush()
            clone_event_groups(source_event, event)
            db.session.commit()
            flash('Evento criado a partir do padrão.', 'success')

        elif action == 'update':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            event_date_value = datetime.strptime(request.form.get('event_date'), '%Y-%m-%d').date()
            starts_at = parse_local_datetime(request.form.get('starts_at'))
            ends_at = parse_local_datetime(request.form.get('ends_at'))
            if request.form.get('use_default_time'):
                starts_at, ends_at = build_default_event_times(event_date_value)
            event.title = request.form.get('title')
            event.slug = unique_event_slug(request.form.get('slug') or request.form.get('title'), current_event_id=event.id)
            event.event_date = event_date_value
            event.starts_at = starts_at
            event.ends_at = ends_at
            event.description = request.form.get('description')
            event.hero_text = request.form.get('hero_text')
            event.status = request.form.get('status', 'draft')
            if request.form.get('make_active'):
                FragNightEvent.query.update({'is_active': False})
                event.is_active = True
            else:
                event.is_active = False
            db.session.commit()
            flash('Evento atualizado.', 'success')

        elif action == 'set_template':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            SiteSetting.set('default_event_template_id', str(event.id))
            db.session.commit()
            flash('Evento definido como padrão.', 'success')

        elif action == 'activate':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            FragNightEvent.query.update({'is_active': False})
            event.is_active = True
            db.session.commit()
            flash('Evento definido como ativo.', 'success')

        elif action == 'deactivate':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            event.is_active = False
            db.session.commit()
            flash('Evento desativado.', 'success')

        elif action == 'delete':
            event = FragNightEvent.query.get_or_404(request.form.get('event_id'))
            try:
                delete_event_and_dependencies(event)
                db.session.commit()
                flash('Evento removido.', 'success')
            except Exception:
                db.session.rollback()
                flash('Não foi possível excluir este evento. Verifique se existem reservas ou vínculos pendentes.', 'error')

        return redirect(url_for('admin.events'))

    events = FragNightEvent.query.order_by(FragNightEvent.event_date.desc()).all()
    default_template_id = SiteSetting.get('default_event_template_id', '')
    return render_template('admin/events.html', events=events, default_template_id=default_template_id)

@admin_bp.route('/evento/<int:event_id>/grupos', methods=['GET', 'POST'])
@login_required
def event_groups(event_id):
    admin_required()
    event = FragNightEvent.query.get_or_404(event_id)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_group':
            layout_key = request.form.get('layout_key', '').strip()
            location_label = request.form.get('location_label', '').strip()
            fixed_labels = FIXED_LAYOUTS.get(layout_key, [])
            quantity = len(fixed_labels) if fixed_labels else int(request.form.get('quantity', 10))

            encoded_location = f"{layout_key}|{location_label}" if layout_key else location_label
            group = MachineGroup(
                event_id=event.id,
                name=request.form.get('name'),
                location_label=encoded_location,
                quantity=quantity,
                price=request.form.get('price', 0),
                specs=request.form.get('specs'),
                color=request.form.get('color', '#0057e1'),
            )
            db.session.add(group)
            db.session.flush()

            used_labels = {machine.label.zfill(2) for machine in Machine.query.filter_by(event_id=event.id).all()}
            labels_to_create = [label for label in fixed_labels if label.zfill(2) not in used_labels] if fixed_labels else []
            if not labels_to_create and fixed_labels:
                labels_to_create = fixed_labels

            if labels_to_create:
                for label in labels_to_create:
                    db.session.add(Machine(event_id=event.id, group_id=group.id, label=label, status='available'))
            else:
                existing_count = Machine.query.filter_by(event_id=event.id).count()
                for i in range(group.quantity):
                    label = str(existing_count + i + 1).zfill(2)
                    db.session.add(Machine(event_id=event.id, group_id=group.id, label=label, status='available'))
            db.session.commit()
            flash('Grupo e máquinas criados.', 'success')

        elif action == 'update_group':
            group = MachineGroup.query.get_or_404(request.form.get('group_id'))
            old_layout_key, _ = split_location_label(group.location_label or group.name)
            new_layout_key = request.form.get('layout_key', '').strip()
            location_label = request.form.get('location_label', '').strip()
            group.name = request.form.get('name')
            group.location_label = f"{new_layout_key}|{location_label}" if new_layout_key else location_label
            group.quantity = int(request.form.get('quantity', group.quantity or 1))
            group.price = request.form.get('price', group.price or 0)
            group.specs = request.form.get('specs')
            group.color = request.form.get('color', group.color or '#0057e1')

            if new_layout_key != old_layout_key:
                existing_machines = Machine.query.filter_by(group_id=group.id).order_by(Machine.id.asc()).all()
                desired_labels = FIXED_LAYOUTS.get(new_layout_key, [])
                if desired_labels:
                    reserved_elsewhere = {m.label.zfill(2) for m in Machine.query.filter(Machine.event_id == event.id, Machine.group_id != group.id).all()}
                    allowed_labels = [label for label in desired_labels if label.zfill(2) not in reserved_elsewhere]
                    if len(allowed_labels) != len(desired_labels):
                        flash('Não foi possível trocar o mapa fixo porque já existem máquinas usando algumas posições.', 'error')
                        db.session.rollback()
                        return redirect(url_for('admin.event_groups', event_id=event.id))
                    for index, machine in enumerate(existing_machines):
                        if index < len(desired_labels):
                            machine.label = desired_labels[index]
                    if len(existing_machines) < len(desired_labels):
                        for label in desired_labels[len(existing_machines):]:
                            db.session.add(Machine(event_id=event.id, group_id=group.id, label=label, status='available'))
                    elif len(existing_machines) > len(desired_labels):
                        for machine in existing_machines[len(desired_labels):]:
                            db.session.delete(machine)
                    group.quantity = len(desired_labels)

            db.session.commit()
            flash('Grupo atualizado.', 'success')

        elif action == 'delete_group':
            group = MachineGroup.query.get_or_404(request.form.get('group_id'))
            db.session.delete(group)
            db.session.commit()
            flash('Grupo removido.', 'success')
        return redirect(url_for('admin.event_groups', event_id=event.id))
    groups = MachineGroup.query.filter_by(event_id=event.id).order_by(MachineGroup.id.asc()).all()
    sections = build_machine_sections(groups, unavailable_machine_ids=set())
    return render_template('admin/event_groups.html', event=event, groups=groups, sections=sections)

@admin_bp.route('/vendas')
@login_required
def sales():
    admin_required()
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template('admin/sales.html', reservations=reservations)



@admin_bp.route('/minha-conta', methods=['GET', 'POST'])
@login_required
def account():
    admin_required()
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('Este e-mail já está em uso por outro usuário.', 'error')
            return redirect(url_for('admin.account'))

        current_user.email = email

        if password:
            if len(password) < 6:
                flash('A nova senha precisa ter pelo menos 6 caracteres.', 'error')
                return redirect(url_for('admin.account'))
            if password != password_confirm:
                flash('A confirmação da senha não confere.', 'error')
                return redirect(url_for('admin.account'))
            current_user.set_password(password)

        db.session.commit()
        flash('Conta atualizada com sucesso.', 'success')
        return redirect(url_for('admin.account'))

    return render_template('admin/account.html')

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
                    f"✅ Novo pagamento aprovado no Frag-Night\n"
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
