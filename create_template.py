"""Cria o template de faturamento na conta WhatsApp Business da DMB."""

import json
import os
import urllib.error
import urllib.request

from app import ENV_PATH, load_env


load_env(ENV_PATH)
token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
waba_id = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
if not token or not waba_id:
    raise SystemExit("Token ou WhatsApp Business Account ID ausente no .env.")

payload = {
    "name": "resumo_faturamento_diario",
    "language": "pt_BR",
    "category": "UTILITY",
    "components": [
        {
            "type": "BODY",
            "text": (
                "Olá, sou o Robô DMB, aqui segue uma Informação Importante:\n"
                "==> Venda ref. ao Dia ({{1}}) : R$ {{2}}.\n"
                "Consulta realizada automaticamente no ERP."
            ),
            "example": {
                "body_text": [["24/08/2026", "434.422,84"]]
            },
        }
    ],
}
request = urllib.request.Request(
    f"https://graph.facebook.com/v25.0/{waba_id}/message_templates",
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
        print(
            "Template criado. "
            f"ID: {result.get('id', 'não retornado')} | "
            f"Status: {result.get('status', 'em análise')} | "
            f"Categoria: {result.get('category', payload['category'])}"
        )
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"Meta retornou HTTP {error.code}: {detail}")
