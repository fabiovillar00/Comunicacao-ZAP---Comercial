"""Consulta o estado operacional do número de produção no WhatsApp."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from app import ENV_PATH, load_env


load_env(ENV_PATH)
token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
if not token or not phone_number_id:
    raise SystemExit("Credenciais ausentes no .env.")

query = urllib.parse.urlencode(
    {
        "fields": (
            "display_phone_number,verified_name,code_verification_status,"
            "quality_rating,platform_type,throughput"
        )
    }
)
request = urllib.request.Request(
    f"https://graph.facebook.com/v25.0/{phone_number_id}?{query}",
    headers={"Authorization": f"Bearer {token}"},
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        for key in (
            "display_phone_number",
            "verified_name",
            "code_verification_status",
            "quality_rating",
            "platform_type",
            "throughput",
        ):
            print(f"{key}={data.get(key, 'não informado')}")
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"Meta retornou HTTP {error.code}: {detail}")
