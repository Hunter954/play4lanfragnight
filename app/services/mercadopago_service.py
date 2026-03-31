import os
import requests
from flask import current_app
from ..models import SiteSetting

def _token():
    return SiteSetting.get('mp_access_token') or os.getenv('MP_ACCESS_TOKEN', '')

def create_preference(reservation, title, success_url=None):
    token = _token()
    if not token:
        return {'mock': True, 'init_point': f"{current_app.config['APP_BASE_URL']}/minhas-reservas", 'preference_id': f"mock-{reservation.code}"}

    base_url = 'https://api.mercadopago.com/checkout/preferences'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    callback_url = f"{current_app.config['APP_BASE_URL']}/payments/webhook/mercadopago"
    payload = {
        'items': [{
            'title': title,
            'quantity': 1,
            'currency_id': 'BRL',
            'unit_price': float(reservation.total_amount),
        }],
        'external_reference': reservation.code,
        'notification_url': callback_url,
        'back_urls': {
            'success': success_url or f"{current_app.config['APP_BASE_URL']}/checkout/sucesso/{reservation.code}",
            'failure': f"{current_app.config['APP_BASE_URL']}/checkout/falha/{reservation.code}",
            'pending': f"{current_app.config['APP_BASE_URL']}/checkout/pendente/{reservation.code}",
        },
        'auto_return': 'approved',
    }
    response = requests.post(base_url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def get_payment(payment_id):
    token = _token()
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'https://api.mercadopago.com/v1/payments/{payment_id}', headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()
