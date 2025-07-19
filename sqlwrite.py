# postgres_tool.py
import os, psycopg2
from psycopg2.extras import RealDictCursor
from crewai_tools import BaseTool

DB_URL = os.getenv("DATABASE_URL")  # e.g.  postgres://user:pwd@localhost:5432/mydb


class PostgresWriteTool(BaseTool):
    """
    A CrewAI tool that executes WRITE queries (INSERT/UPDATE/DELETE) safely
    on the Postgres database pointed to by $DATABASE_URL.

    Input must be a JSON string:
      {"sql": "UPDATE users SET address = %s WHERE id = %s",
       "params": ["132 Elm Ave", 42]}
    """
    name = "postgres_write"
    description = ("Use ONLY for modifications that have already been validated. "
                   "Return 'OK' if no rows, else return affected rowcount.")

    def _run(self, input: str):
        import json
        payload = json.loads(input)
        sql, params = payload["sql"], payload["params"]

        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                conn.commit()
                return f"rows_affected={cur.rowcount}"
