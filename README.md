# Play4Lan FragNight Reservas

Projeto Flask + PostgreSQL para venda/reserva de máquinas do FragNight, com:

- escolha de máquinas estilo cinema
- hover/touch com configuração da máquina
- login de usuário
- painel admin
- criação de eventos FragNight
- grupos de máquinas por lote de 10
- preço por grupo
- integração base com Mercado Pago
- integração base com Z-API
- webhook de pagamento para marcar reserva como paga
- disparo de atualização para WhatsApp quando pagamento aprovar
- tela para configurar credenciais com máscara visual
- preparado para deploy no Railway + volume para uploads

## Rodando local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env  # no Windows
# ou cp .env.example .env
flask db init
flask db migrate -m "init"
flask db upgrade
python seed.py
flask run
```

## Deploy Railway

- Crie serviço com este repositório
- Adicione Postgres
- Configure volume montado em `/data`
- Variáveis importantes:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `APP_BASE_URL`
  - `MP_ACCESS_TOKEN`
  - `MP_PUBLIC_KEY`
  - `ZAPI_INSTANCE_ID`
  - `ZAPI_INSTANCE_TOKEN`
  - `ZAPI_CLIENT_TOKEN`

## Fluxo Mercado Pago

1. Admin cria evento e grupos/máquinas
2. Usuário escolhe máquinas
3. Sistema cria uma preferência de pagamento
4. Mercado Pago chama `/payments/webhook/mercadopago`
5. Se pago, reservas viram `paid`
6. Sistema envia atualização pelo Z-API para o número configurado

## Fluxo Z-API

- Em **Admin > APIs > Z-API**
- Salve instance id, instance token e client token
- Use o botão para consultar status/QR
- O QR é mostrado no admin para conectar a instância do WhatsApp

## Observações

- O login por QR de usuário final não é um fluxo nativo do Z-API como OAuth. Neste projeto deixei:
  - **conexão da instância Z-API por QR no admin**
  - **login rápido do usuário por WhatsApp** preparado na estrutura para evolução futura
- As integrações reais dependem das credenciais válidas e webhooks configurados no provedor.
