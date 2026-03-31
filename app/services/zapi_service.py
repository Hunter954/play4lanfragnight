import os
import requests
from ..models import SiteSetting

def _config():
    return {
        'base_url': SiteSetting.get('zapi_base_url', 'https://api.z-api.io') or os.getenv('ZAPI_BASE_URL', 'https://api.z-api.io'),
        'instance_id': SiteSetting.get('zapi_instance_id') or os.getenv('ZAPI_INSTANCE_ID', ''),
        'instance_token': SiteSetting.get('zapi_instance_token') or os.getenv('ZAPI_INSTANCE_TOKEN', ''),
        'client_token': SiteSetting.get('zapi_client_token') or os.getenv('ZAPI_CLIENT_TOKEN', ''),
        'notify_phone': SiteSetting.get('zapi_notify_phone', ''),
    }

def _headers(client_token):
    headers = {'Content-Type': 'application/json'}
    if client_token:
        headers['Client-Token'] = client_token
    return headers

def status():
    cfg = _config()
    if not cfg['instance_id'] or not cfg['instance_token']:
        return {'connected': False, 'message': 'Credenciais Z-API não configuradas.'}
    url = f"{cfg['base_url']}/instances/{cfg['instance_id']}/token/{cfg['instance_token']}/status"
    response = requests.get(url, headers=_headers(cfg['client_token']), timeout=30)
    response.raise_for_status()
    return response.json()

def get_qr():
    cfg = _config()
    if not cfg['instance_id'] or not cfg['instance_token']:
        return {'value': None, 'message': 'Credenciais Z-API não configuradas.'}
    url = f"{cfg['base_url']}/instances/{cfg['instance_id']}/token/{cfg['instance_token']}/qr-code/image"
    response = requests.get(url, headers=_headers(cfg['client_token']), timeout=30)
    response.raise_for_status()
    return response.json()

def send_text(phone, message):
    cfg = _config()
    if not cfg['instance_id'] or not cfg['instance_token']:
        return {'mock': True, 'message': 'Z-API não configurada.'}
    url = f"{cfg['base_url']}/instances/{cfg['instance_id']}/token/{cfg['instance_token']}/send-text"
    payload = {'phone': phone, 'message': message}
    response = requests.post(url, json=payload, headers=_headers(cfg['client_token']), timeout=30)
    response.raise_for_status()
    return response.json()

def notify_admin(message):
    cfg = _config()
    if not cfg['notify_phone']:
        return {'skipped': True, 'message': 'Nenhum telefone de notificação cadastrado.'}
    return send_text(cfg['notify_phone'], message)
