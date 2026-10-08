"""Envia o template oficial de teste da Meta pelo número de produção."""

import json
import os
import urllib.error
import urllib.request

from app import ENV_PATH, load_env


load_env(ENV_PATH)
token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
if not token or not phone_number_id:
    raise SystemExit("Token ou Phone Number ID não configurado no .env.")

payload = {
    "messaging_product": "whatsapp",
    "to": os.environ["WHATSAPP_TEST_RECIPIENT"],
    "type": "template",
    "template": {
        "name": "3p_direct_integration_test_template",
        "language": {"code": "en_US"},
    },
}
request = urllib.request.Request(
    f"https://graph.facebook.com/v25.0/{phone_number_id}/messages",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
        message_id = result.get("messages", [{}])[0].get("id", "não retornado")
        print(f"Mensagem aceita pela Meta. ID: {message_id}")
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"Meta retornou HTTP {error.code}: {detail}")
