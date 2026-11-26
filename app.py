import os
import sqlite3
from flask import Flask, g, jsonify, render_template, request

VALID_PRIORITIES = {"alta", "media", "baja"}
VALID_STATUSES = {"pendiente", "en_proceso", "terminada"}
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")


def _validate_task_payload(data, require_core_fields=True):
    """Valida y normaliza los campos de una tarea para creación o edición."""
    if not isinstance(data, dict):
        return None, "El cuerpo de la solicitud debe ser JSON válido."

    cleaned = {}

    if "title" in data or require_core_fields:
        raw_title = data.get("title")
        title = raw_title.strip() if isinstance(raw_title, str) else ""
        if not title:
            return None, "El título de la tarea es obligatorio."
        cleaned["title"] = title

    if "assignee" in data or require_core_fields:
        raw_assignee = data.get("assignee")
        assignee = raw_assignee.strip() if isinstance(raw_assignee, str) else ""
        if not assignee:
            return None, "El responsable de la tarea es obligatorio."
        cleaned["assignee"] = assignee

    if "description" in data or require_core_fields:
        raw_desc = data.get("description", "")
        if raw_desc is None:
            raw_desc = ""
        if not isinstance(raw_desc, str):
            return None, "La descripción debe ser texto válido."
        cleaned["description"] = raw_desc.strip()

    if "priority" in data or require_core_fields:
        raw_priority = data.get("priority", "media")
        priority = raw_priority.strip().lower() if isinstance(raw_priority, str) else ""
        if priority not in VALID_PRIORITIES:
            return None, "La prioridad debe ser 'alta', 'media' o 'baja'."
        cleaned["priority"] = priority

    if "status" in data:
        raw_status = data.get("status")
        status = raw_status.strip().lower() if isinstance(raw_status, str) else ""
        if status not in VALID_STATUSES:
            return None, "El estado debe ser 'pendiente', 'en_proceso' o 'terminada'."
        cleaned["status"] = status

    return cleaned, None


def create_app(test_config=None):
    """Crea y configura la instancia principal de la aplicación TaskManager."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("TASKMANAGER_DB", DEFAULT_DB_PATH),
        SEND_FILE_MAX_AGE_DEFAULT=0,
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

    def fetch_task(task_id):
        return get_db().execute(
            "SELECT id, title, description, assignee, priority, status, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    with app.app_context():
        init_db()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/api/tasks")
    def list_tasks():
        """RF02: Consultar todas las tareas registradas."""
        status_filter = request.args.get("status", "").strip().lower()
        priority_filter = request.args.get("priority", "").strip().lower()

        query = "SELECT id, title, description, assignee, priority, status, created_at FROM tasks"
        conditions = []
        params = []

        if status_filter:
            if status_filter not in VALID_STATUSES:
                return jsonify({"error": "Filtro de estado inválido."}), 400
            conditions.append("status = ?")
            params.append(status_filter)

        if priority_filter:
            if priority_filter not in VALID_PRIORITIES:
                return jsonify({"error": "Filtro de prioridad inválido."}), 400
            conditions.append("priority = ?")
            params.append(priority_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC"

        rows = get_db().execute(query, params).fetchall()
        return jsonify({"tasks": [dict(row) for row in rows]}), 200

    @app.post("/api/tasks")
    def create_task():
        """RF01 y RF06: Registrar una nueva tarea con prioridad."""
        cleaned, error = _validate_task_payload(request.get_json(silent=True), require_core_fields=True)
        if error:
            return jsonify({"error": error}), 400

        status = cleaned.get("status", "pendiente")
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO tasks (title, description, assignee, priority, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cleaned["title"], cleaned["description"], cleaned["assignee"], cleaned["priority"], status),
        )
        db.commit()

        return jsonify({
            "message": "Tarea registrada correctamente.",
            "task": dict(fetch_task(cursor.lastrowid)),
        }), 201

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id):
        """RF03, RF05 y RF06: Editar la información, estado o prioridad de una tarea."""
        existing = fetch_task(task_id)
        if existing is None:
            return jsonify({"error": "Tarea no encontrada."}), 404

        cleaned, error = _validate_task_payload(request.get_json(silent=True), require_core_fields=False)
        if error:
            return jsonify({"error": error}), 400
        if not cleaned:
            return jsonify({"error": "No se proporcionaron campos para actualizar."}), 400

        updated = {
            "title": cleaned.get("title", existing["title"]),
            "description": cleaned.get("description", existing["description"]),
            "assignee": cleaned.get("assignee", existing["assignee"]),
            "priority": cleaned.get("priority", existing["priority"]),
            "status": cleaned.get("status", existing["status"]),
        }

        db = get_db()
        db.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, assignee = ?, priority = ?, status = ?
            WHERE id = ?
            """,
            (
                updated["title"],
                updated["description"],
                updated["assignee"],
                updated["priority"],
                updated["status"],
                task_id,
            ),
        )
        db.commit()

        return jsonify({
            "message": "Tarea actualizada correctamente.",
            "task": dict(fetch_task(task_id)),
        }), 200

    @app.patch("/api/tasks/<int:task_id>/status")
    def update_task_status(task_id):
        """RF05: Cambiar el estado de una tarea entre pendiente, en_proceso y terminada."""
        existing = fetch_task(task_id)
        if existing is None:
            return jsonify({"error": "Tarea no encontrada."}), 404

        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            return jsonify({"error": "Debe indicar un estado válido."}), 400

        status = data["status"].strip().lower()
        if status not in VALID_STATUSES:
            return jsonify({"error": "El estado debe ser 'pendiente', 'en_proceso' o 'terminada'."}), 400

        db = get_db()
        db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        db.commit()

        return jsonify({
            "message": "Estado actualizado correctamente.",
            "task": dict(fetch_task(task_id)),
        }), 200

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        """RF04: Eliminar una tarea existente."""
        existing = fetch_task(task_id)
        if existing is None:
            return jsonify({"error": "Tarea no encontrada."}), 404

        db = get_db()
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()

        return jsonify({"message": "Tarea eliminada correctamente."}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
