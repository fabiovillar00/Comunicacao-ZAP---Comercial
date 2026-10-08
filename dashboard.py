from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app import (
    CONFIG_PATH,
    ENV_PATH,
    HISTORY_PATH,
    load_config,
    load_env,
    query_database,
    run_once,
    validate_config,
)


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8765
FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|EXEC(?:UTE)?|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
RUN_LOCK = threading.Lock()


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) in (10, 11):
        digits = "55" + digits
    if not digits.startswith("55") or len(digits) not in (12, 13):
        raise ValueError("Informe um telefone brasileiro válido com DDD.")
    return digits


def validate_select(query: str) -> str:
    cleaned = query.strip().rstrip(";").strip()
    if not cleaned.upper().startswith(("SELECT", "WITH")):
        raise ValueError("A consulta deve começar com SELECT ou WITH.")
    if FORBIDDEN_SQL.search(cleaned):
        raise ValueError("Somente consultas de leitura são permitidas.")
    return cleaned


def save_config(config: dict[str, Any]) -> None:
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CONFIG_PATH)


def history_rows() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    with sqlite3.connect(HISTORY_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT executado_em, destinatario, telefone, status, mensagem_id, detalhe
            FROM envios
            ORDER BY id DESC
            LIMIT 50
            """
        ).fetchall()
    return [dict(row) for row in rows]


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": config.get("dry_run", True),
        "database": {"query": config["database"]["query"]},
        "schedule": config.get("schedule", {"time": "18:00"}),
        "preview_message": config["preview_message"],
        "recipients": config.get("recipients", []),
        "template": {
            "name": config["whatsapp"]["template_name"],
            "language": config["whatsapp"]["template_language"],
        },
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "DmbDashboard/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _valid_host(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].lower()
        return host in {"127.0.0.1", "localhost"}

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Conteúdo inválido.")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("Tamanho da solicitação inválido.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        if not self._valid_host():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            config = load_config()
            self._json({"config": public_config(config), "history": history_rows()})
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        if not self._valid_host():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        try:
            data = self._body()
            path = urlparse(self.path).path
            if path == "/api/recipients":
                self._add_recipient(data)
            elif path == "/api/recipients/update":
                self._update_recipient(data)
            elif path == "/api/recipients/delete":
                self._delete_recipient(data)
            elif path == "/api/settings":
                self._update_settings(data)
            elif path == "/api/preview":
                self._preview()
            elif path == "/api/run-now":
                self._run_now()
            else:
                self._json({"error": "Rota não encontrada."}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._json({"error": f"Não foi possível concluir: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _add_recipient(self, data: dict[str, Any]) -> None:
        name = str(data.get("name", "")).strip()
        if len(name) < 2 or len(name) > 80:
            raise ValueError("Informe um nome entre 2 e 80 caracteres.")
        phone = normalize_phone(str(data.get("phone", "")))
        config = load_config()
        if any(item["phone"] == phone for item in config["recipients"]):
            raise ValueError("Esse telefone já está cadastrado.")
        config["recipients"].append(
            {"id": uuid.uuid4().hex, "name": name, "phone": phone, "enabled": True}
        )
        save_config(config)
        self._json({"ok": True, "config": public_config(config)}, HTTPStatus.CREATED)

    def _find_recipient(self, config: dict[str, Any], recipient_id: str) -> dict[str, Any]:
        for recipient in config["recipients"]:
            if recipient.get("id") == recipient_id:
                return recipient
        raise ValueError("Destinatário não encontrado.")

    def _update_recipient(self, data: dict[str, Any]) -> None:
        config = load_config()
        recipient = self._find_recipient(config, str(data.get("id", "")))
        recipient["enabled"] = bool(data.get("enabled"))
        save_config(config)
        self._json({"ok": True, "config": public_config(config)})

    def _delete_recipient(self, data: dict[str, Any]) -> None:
        recipient_id = str(data.get("id", ""))
        config = load_config()
        before = len(config["recipients"])
        config["recipients"] = [
            item for item in config["recipients"] if item.get("id") != recipient_id
        ]
        if len(config["recipients"]) == before:
            raise ValueError("Destinatário não encontrado.")
        save_config(config)
        self._json({"ok": True, "config": public_config(config)})

    def _update_settings(self, data: dict[str, Any]) -> None:
        query = validate_select(str(data.get("query", "")))
        message = str(data.get("message", "")).strip()
        if not message or len(message) > 1000:
            raise ValueError("A mensagem deve ter entre 1 e 1.000 caracteres.")
        config = load_config()
        config["database"]["query"] = query
        config["preview_message"] = message
        save_config(config)
        self._json({"ok": True, "config": public_config(config)})

    def _preview(self) -> None:
        config = load_config()
        values = query_database(config)
        message = config["preview_message"].format_map(values)
        self._json({"values": values, "message": message})

    def _run_now(self) -> None:
        if not RUN_LOCK.acquire(blocking=False):
            self._json(
                {"error": "Já existe um envio em andamento. Aguarde a conclusão."},
                HTTPStatus.CONFLICT,
            )
            return
        try:
            load_env(ENV_PATH)
            config = load_config()
            errors = validate_config(config)
            if errors:
                raise ValueError(" ".join(errors))
            enabled = [item for item in config["recipients"] if item.get("enabled")]
            if not enabled:
                raise ValueError("Não há destinatários ativos para receber a mensagem.")
            result = run_once(config)
            if result:
                self._json(
                    {
                        "error": "O envio terminou com erro. Consulte o histórico para ver os detalhes.",
                        "history": history_rows(),
                    },
                    HTTPStatus.BAD_GATEWAY,
                )
                return
            self._json({"ok": True, "sent": len(enabled), "history": history_rows()})
        finally:
            RUN_LOCK.release()

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in target.parents or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Painel DMB disponível em http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), DashboardHandler).serve_forever()
