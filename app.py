from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyodbc


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
ENV_PATH = ROOT / ".env"
HISTORY_PATH = ROOT / "data" / "envios.db"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def normalize_value(value: Any) -> str:
    if value is None:
        return "0"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, (Decimal, float)):
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        return f"{decimal_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


def query_database(config: dict[str, Any]) -> dict[str, str]:
    database = config["database"]
    with pyodbc.connect(database["connection_string"], timeout=15) as connection:
        cursor = connection.cursor()
        cursor.execute(database["query"])
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("A consulta SQL não retornou nenhuma linha.")
        if cursor.fetchone() is not None:
            raise RuntimeError("A consulta SQL deve retornar exatamente uma linha.")
        columns = [column[0] for column in cursor.description]
        return {name: normalize_value(value) for name, value in zip(columns, row)}


@dataclass
class SendResult:
    status: str
    message_id: str | None = None
    detail: str | None = None


class WhatsAppClient:
    def __init__(self, config: dict[str, Any], dry_run: bool) -> None:
        self.config = config
        self.dry_run = dry_run
        self.token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    def send(self, phone: str, values: dict[str, str]) -> SendResult:
        parameters = [
            {"type": "text", "text": values[field]}
            for field in self.config["template_parameters"]
        ]
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "template",
            "template": {
                "name": self.config["template_name"],
                "language": {"code": self.config["template_language"]},
                "components": [{"type": "body", "parameters": parameters}],
            },
        }
        if self.dry_run:
            return SendResult("SIMULADO", detail=json.dumps(payload, ensure_ascii=False))
        if not self.token or not self.phone_number_id:
            raise RuntimeError("Credenciais do WhatsApp não configuradas no arquivo .env.")

        version = self.config["graph_api_version"]
        url = f"https://graph.facebook.com/{version}/{self.phone_number_id}/messages"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                message_id = body.get("messages", [{}])[0].get("id")
                return SendResult("ENVIADO", message_id=message_id)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            return SendResult("ERRO", detail=f"HTTP {error.code}: {detail}")
        except urllib.error.URLError as error:
            return SendResult("ERRO", detail=str(error.reason))


def open_history() -> sqlite3.Connection:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(HISTORY_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executado_em TEXT NOT NULL,
            destinatario TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status TEXT NOT NULL,
            mensagem_id TEXT,
            detalhe TEXT
        )
        """
    )
    return connection


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["database", "whatsapp", "recipients", "preview_message"]
    for key in required:
        if key not in config:
            errors.append(f"Campo obrigatório ausente: {key}")
    whatsapp = config.get("whatsapp", {})
    for field in ("graph_api_version", "template_name", "template_language", "template_parameters"):
        if not whatsapp.get(field):
            errors.append(f"Configuração do WhatsApp ausente: {field}")
    for recipient in config.get("recipients", []):
        phone = str(recipient.get("phone", ""))
        if recipient.get("enabled") and (not phone.isdigit() or len(phone) < 10):
            errors.append(f"Telefone inválido para {recipient.get('name', 'destinatário')}: {phone}")
    return errors


def run_once(config: dict[str, Any]) -> int:
    values = query_database(config)
    missing = [field for field in config["whatsapp"]["template_parameters"] if field not in values]
    if missing:
        raise RuntimeError(f"Colunas não retornadas pela consulta: {', '.join(missing)}")

    preview = config["preview_message"].format_map(values)
    print(f"Mensagem: {preview}")
    enabled = [recipient for recipient in config["recipients"] if recipient.get("enabled")]
    if not enabled:
        print("Nenhum destinatário habilitado; nenhum envio foi realizado.")
        return 0

    client = WhatsAppClient(config["whatsapp"], bool(config.get("dry_run", True)))
    failures = 0
    with open_history() as history:
        for recipient in enabled:
            result = client.send(str(recipient["phone"]), values)
            history.execute(
                "INSERT INTO envios (executado_em, destinatario, telefone, status, mensagem_id, detalhe) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), recipient["name"], str(recipient["phone"]), result.status, result.message_id, result.detail),
            )
            print(f"{recipient['name']} ({recipient['phone']}): {result.status}")
            if result.status == "ERRO":
                failures += 1
                print(result.detail, file=sys.stderr)
    return 1 if failures else 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Envia indicadores comerciais pelo WhatsApp.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Valida a configuração sem consultar ou enviar.")
    action.add_argument("--run-once", action="store_true", help="Consulta e executa o disparo uma vez.")
    args = parser.parse_args()

    load_env(ENV_PATH)
    config = load_config()
    errors = validate_config(config)
    if errors:
        for error in errors:
            print(f"ERRO: {error}", file=sys.stderr)
        return 2
    if args.check:
        print("Configuração válida.")
        return 0
    try:
        return run_once(config)
    except Exception as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
