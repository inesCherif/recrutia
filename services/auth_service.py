import os
import sqlite3
import uuid
import threading
from typing import Optional, List, Dict
import bcrypt
from models.user import User
from utils.logger import AgenticLogger


class AuthService:
    """Authentication service backed by SQLite (thread-safe, concurrent-access safe)."""

    def __init__(self, db_path: str = "data/agentichire.db"):
        self.db_path = db_path
        self.logger = AgenticLogger("AuthService")
        self._local = threading.local()
        self._ensure_db()
        self.current_user: Optional[User] = None

    # --- Connection management ---

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
        return self._local.conn

    def _ensure_db(self):
        """Create the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path) or "data", exist_ok=True)
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'USER',
                email TEXT,
                company_name TEXT,
                school_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                type_flux TEXT DEFAULT 'entrepreneur',
                data_json TEXT,
                artifacts_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pii_vault (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, token)
            )
        """)
        conn.commit()


    # --- Password hashing (bcrypt directly — no passlib) ---

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    # --- User operations ---

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert a sqlite3.Row to a User model."""
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            email=row["email"],
            company_name=row["company_name"],
            school_name=row["school_name"],
        )

    def register(self, username: str, password: str, email: str = None) -> Optional[User]:
        """Register a new user. Returns None if username already exists."""
        conn = self._get_conn()
        try:
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            conn.execute(
                "INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, password_hash, "USER", email),
            )
            conn.commit()
            self.logger.success(f"Nouvel utilisateur inscrit: {username}")
            return User(
                id=user_id,
                username=username,
                password_hash=password_hash,
                role="USER",
                email=email,
            )
        except sqlite3.IntegrityError:
            self.logger.warning(f"Tentative d'inscription échouée: {username} existe déjà")
            return None

    def login(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user. Returns None on failure."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if row and self._verify_password(password, row["password_hash"]):
            user = self._row_to_user(row)
            self.current_user = user
            self.logger.success(f"Connexion réussie: {username}")
            return user

        self.logger.warning(f"Échec connexion: {username}")
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Look up a user by their ID (used by JWT validation)."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            return self._row_to_user(row)
        return None

    def logout(self):
        if self.current_user:
            self.logger.info(f"Déconnexion: {self.current_user.username}")
        self.current_user = None

    def get_current_user_id(self) -> Optional[str]:
        return self.current_user.id if self.current_user else None

    # --- Offers operations (moved from recruiter.py JSON files) ---

    def load_user_offers(self, user_id: str) -> List[dict]:
        """Load all offers for a user from SQLite."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM offers WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ).fetchall()

        import json
        results = []
        for row in rows:
            entry = {
                "id": row["id"],
                "user_id": row["user_id"],
                "date": row["date"],
                "type_flux": row["type_flux"],
                "data": json.loads(row["data_json"]) if row["data_json"] else {},
                "artifacts": json.loads(row["artifacts_json"]) if row["artifacts_json"] else {},
            }
            results.append(entry)
        return results

    def save_offer(self, user_id: str, job_data: dict, linkedin_post: str, offer_id: str, form_url: str):
        """Save an offer to SQLite."""
        import json
        from datetime import datetime

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO offers (user_id, date, type_flux, data_json, artifacts_json) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "entrepreneur",
                json.dumps(job_data, ensure_ascii=False),
                json.dumps({
                    "offer_id": offer_id,
                    "form_link": form_url,
                    "linkedin_post": linkedin_post,
                }, ensure_ascii=False),
            ),
        )
        conn.commit()

    def save_vault_entry(self, user_id: str, token: str, encrypted_value: str):
        """Save/update an encrypted PII token mapping to SQLite."""
        from datetime import datetime
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO pii_vault (id, user_id, token, encrypted_value, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                token,
                encrypted_value,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()

    def get_vault_entries(self, user_id: str) -> Dict[str, str]:
        """Load all token -> encrypted_value mappings for a user."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT token, encrypted_value FROM pii_vault WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        return {row["token"]: row["encrypted_value"] for row in rows}

