import os
import sqlite3
from flask import Flask, g, jsonify, render_template, request

VALID_PRIORITIES = {"alta", "media", "baja"}
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")


def create_app(test_config=None):
    """Crea y configura la instancia principal de la aplicación TaskManager."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("TASKMANAGER_DB", DEFAULT_DB_PATH),
    )

    if test_config is not None:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                assignee TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'media',
                status TEXT NOT NULL DEFAULT 'pendiente',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()

    with app.app_context():
        init_db()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/api/tasks")
    def create_task():
        """RF01: Registrar una nueva tarea."""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "El cuerpo de la solicitud debe ser JSON válido."}), 400

        title = (data.get("title") or "").strip() if isinstance(data.get("title"), str) else ""
        assignee = (data.get("assignee") or "").strip() if isinstance(data.get("assignee"), str) else ""
        description = (data.get("description") or "").strip() if isinstance(data.get("description"), str) else ""
        raw_priority = data.get("priority", "media")
        priority = raw_priority.strip().lower() if isinstance(raw_priority, str) else ""

        if not title:
            return jsonify({"error": "El título de la tarea es obligatorio."}), 400
        if not assignee:
            return jsonify({"error": "El responsable de la tarea es obligatorio."}), 400
        if priority not in VALID_PRIORITIES:
            return jsonify({"error": "La prioridad debe ser 'alta', 'media' o 'baja'."}), 400

        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO tasks (title, description, assignee, priority, status)
            VALUES (?, ?, ?, ?, 'pendiente')
            """,
            (title, description, assignee, priority),
        )
        db.commit()

        row = db.execute(
            "SELECT id, title, description, assignee, priority, status, created_at FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return jsonify({
            "message": "Tarea registrada correctamente.",
            "task": dict(row),
        }), 201

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
