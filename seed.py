from app import create_app, db
from app.models import User, FragNightEvent, MachineGroup, Machine
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta

app = create_app()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@play4lan.local').first():
        admin = User(
            name='Administrador',
            email='admin@play4lan.local',
            password_hash=generate_password_hash('123456'),
            is_admin=True,
            phone='5545999999999'
        )
        db.session.add(admin)

    if not FragNightEvent.query.first():
        event = FragNightEvent(
            title='FragNight 31/03/2026',
            slug='fragnight-31-03-2026',
            event_date=date.today() + timedelta(days=5),
            starts_at=datetime.now() + timedelta(days=5, hours=3),
            ends_at=datetime.now() + timedelta(days=5, hours=11),
            status='published',
            is_active=True,
            description='Reserve sua máquina e garanta seu lugar no FragNight.',
            hero_text='Escolha sua máquina igual cinema, pague online e confirme na hora.'
        )
        db.session.add(event)
        db.session.flush()

        groups = [
            ('Sala Alienware 360Hz', 'Dentro da sala', 10, 35.0, 'PCs premium com monitor Alienware 360Hz, baixa latência, setup competitivo.', '#b91c1c'),
            ('Área Externa A', 'Fora - lote 1', 10, 25.0, 'PCs gamer com excelente desempenho para competitivo.', '#ef4444'),
            ('Área Externa B', 'Fora - lote 2', 10, 20.0, 'PCs gamer custo-benefício com ótimo desempenho.', '#f97316'),
        ]
        number = 1
        for name, location, qty, price, specs, color in groups:
            group = MachineGroup(
                event_id=event.id,
                name=name,
                location_label=location,
                quantity=qty,
                price=price,
                specs=specs,
                color=color
            )
            db.session.add(group)
            db.session.flush()
            for i in range(qty):
                db.session.add(Machine(
                    event_id=event.id,
                    group_id=group.id,
                    label=str(number),
                    status='available'
                ))
                number += 1

    db.session.commit()
    print('Seed concluído.')
