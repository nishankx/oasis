"""
SQLite audit store for oasis-agent run histories.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from oasis_agent.models import ReviewReport


class HistoryStore:
    """Persists run reports and metadata in a local SQLite database."""

    def __init__(self, db_path: str = ".oasis-agent/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    repo_url TEXT,
                    issue_number INTEGER,
                    issue_title TEXT,
                    status TEXT,
                    meaningful INTEGER,
                    confidence REAL,
                    recommended_action TEXT,
                    pr_url TEXT,
                    branch_name TEXT,
                    json_path TEXT,
                    md_path TEXT,
                    metrics_summary TEXT
                )
            """)
            conn.commit()

    def save_run(self, report: ReviewReport, json_path: Path, md_path: Path):
        """Insert or update a run entry in local database and global user database."""
        row_tuple = (
            report.run_id,
            report.timestamp,
            report.repo_url,
            report.issue_number,
            report.issue_title,
            report.status.value,
            1 if report.meaningfulness.meaningful else 0,
            report.meaningfulness.confidence,
            report.meaningfulness.recommended_action,
            report.pr_url,
            report.branch_name,
            str(json_path),
            str(md_path),
            report.metrics.summary_string(),
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, timestamp, repo_url, issue_number, issue_title,
                    status, meaningful, confidence, recommended_action,
                    pr_url, branch_name, json_path, md_path, metrics_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row_tuple,
            )
            conn.commit()

        # Also mirror to global user history store in ~/.oasis-agent/history.db
        try:
            home_db = Path.home() / ".oasis-agent" / "history.db"
            if self.db_path.resolve() != home_db.resolve():
                home_db.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(str(home_db)) as hconn:
                    hconn.execute("""
                        CREATE TABLE IF NOT EXISTS runs (
                            run_id TEXT PRIMARY KEY,
                            timestamp TEXT,
                            repo_url TEXT,
                            issue_number INTEGER,
                            issue_title TEXT,
                            status TEXT,
                            meaningful INTEGER,
                            confidence REAL,
                            recommended_action TEXT,
                            pr_url TEXT,
                            branch_name TEXT,
                            json_path TEXT,
                            md_path TEXT,
                            metrics_summary TEXT
                        )
                    """)
                    hconn.execute(
                        """
                        INSERT OR REPLACE INTO runs (
                            run_id, timestamp, repo_url, issue_number, issue_title,
                            status, meaningful, confidence, recommended_action,
                            pr_url, branch_name, json_path, md_path, metrics_summary
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        row_tuple,
                    )
                    hconn.commit()
        except Exception:
            pass

    def get_recent_runs(self, limit: int = 20) -> List[Dict[str, any]]:
        """Retrieve recent runs ordered by newest first."""
        if self.db_path.exists():
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
                    )
                    return [dict(row) for row in cursor.fetchall()]
            except Exception:
                pass

        # Convenience fallback to home database only if local DB does not exist
        try:
            home_db = Path.home() / ".oasis-agent" / "history.db"
            if home_db.exists() and self.db_path.resolve() != home_db.resolve():
                with sqlite3.connect(str(home_db)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
                    )
                    return [dict(row) for row in cursor.fetchall()]
        except Exception:
            pass

        return []
