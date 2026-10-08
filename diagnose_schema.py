"""Lista colunas de data/status usadas para diagnosticar diferenças entre versões do ERP."""

import json
from pathlib import Path

import pyodbc


root = Path(__file__).resolve().parent
config = json.loads((root / "config.json").read_text(encoding="utf-8"))

with pyodbc.connect(config["database"]["connection_string"], timeout=15) as connection:
    rows = connection.cursor().execute(
        """
        SELECT t.name AS tabela, c.name AS coluna
        FROM sys.tables t
        JOIN sys.columns c ON c.object_id = t.object_id
        WHERE t.name IN (
            'CM_ORDENSVENDA',
            'CM_ORDEMVENDAITENS',
            'CM_OPERACOESFATURAMENTO'
        )
        ORDER BY t.name, c.column_id
        """
    ).fetchall()

for table, column in rows:
    if "DATA" in column.upper() or "STATUS" in column.upper():
        print(f"{table}.{column}")
