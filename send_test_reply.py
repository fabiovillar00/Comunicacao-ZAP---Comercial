"""Envia uma resposta de teste dentro da janela de atendimento de 24 horas."""

import json
import os
import urllib.error
import urllib.request

from app import ENV_PATH, load_env


load_env(ENV_PATH)
token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
if not token or not phone_number_id:
    raise SystemExit("Credenciais ausentes no .env.")

payload = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": os.environ["WHATSAPP_TEST_RECIPIENT"],
    "type": "text",
    "text": {
        "preview_url": False,
        "body": "Teste de comunicação do Robô DMB realizado com sucesso.",
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
        print(f"Resposta aceita pela Meta. ID: {message_id}")
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"Meta retornou HTTP {error.code}: {detail}")
