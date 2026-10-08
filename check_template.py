"""Consulta o status do template de faturamento sem expor credenciais."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from app import ENV_PATH, load_env


load_env(ENV_PATH)
token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
waba_id = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
if not token or not waba_id:
    raise SystemExit("Credenciais ausentes no .env.")

query = urllib.parse.urlencode(
    {
        "name": "resumo_faturamento_diario",
        "fields": "id,name,status,category,language,rejected_reason",
    }
)
request = urllib.request.Request(
    f"https://graph.facebook.com/v25.0/{waba_id}/message_templates?{query}",
    headers={"Authorization": f"Bearer {token}"},
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
        templates = payload.get("data", [])
        if not templates:
            raise SystemExit("Template não encontrado na conta da Meta.")
        for template in templates:
            print(
                f"{template.get('name')} | {template.get('status')} | "
                f"{template.get('category')} | {template.get('language')} | "
                f"motivo={template.get('rejected_reason', '')}"
            )
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"Meta retornou HTTP {error.code}: {detail}")
