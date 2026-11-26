import sqlite3
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_tasks.db"
    app = create_app({"TESTING": True, "DATABASE": str(db_file)})
    with app.test_client() as client:
        yield client, db_file


def test_index_loads(client):
    test_client, _ = client
    response = test_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "TaskManager" in html
    assert "Registrar nueva tarea" in html


def test_health_endpoint(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_task_success(client):
    test_client, db_file = client
    payload = {
        "title": "Configurar CI en GitHub Actions",
        "assignee": "Ana López",
        "priority": "alta",
        "description": "Agregar workflow de pruebas automáticas.",
    }
    response = test_client.post("/api/tasks", json=payload)
    assert response.status_code == 201

    body = response.get_json()
    task = body["task"]
    assert task["id"] == 1
    assert task["title"] == "Configurar CI en GitHub Actions"
    assert task["assignee"] == "Ana López"
    assert task["priority"] == "alta"
    assert task["description"] == "Agregar workflow de pruebas automáticas."
    assert task["status"] == "pendiente"

    conn = sqlite3.connect(db_file)
    row = conn.execute("SELECT title, assignee, priority, status FROM tasks WHERE id = 1").fetchone()
    conn.close()
    assert row == ("Configurar CI en GitHub Actions", "Ana López", "alta", "pendiente")


def test_create_task_default_priority(client):
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": "Documentar endpoints", "assignee": "Carlos Ruiz"},
    )
    assert response.status_code == 201
    assert response.get_json()["task"]["priority"] == "media"
    assert response.get_json()["task"]["status"] == "pendiente"


def test_create_task_missing_title(client):
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": "   ", "assignee": "Ana López"},
    )
    assert response.status_code == 400
    assert "título" in response.get_json()["error"].lower()


def test_create_task_missing_assignee(client):
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": "Revisar PR", "assignee": ""},
    )
    assert response.status_code == 400
    assert "responsable" in response.get_json()["error"].lower()


def test_create_task_invalid_priority(client):
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": "Revisar PR", "assignee": "Ana López", "priority": "urgente"},
    )
    assert response.status_code == 400
    assert "prioridad" in response.get_json()["error"].lower()

def _crear_tarea(test_client, **extra):
    payload = {"title": "Configurar CI", "assignee": "Ana López", "priority": "alta",
               "description": "Agregar workflow"}
    payload.update(extra)
    return test_client.post("/api/tasks", json=payload).get_json()["task"]


def test_list_tasks_empty(client):
    test_client, _ = client
    response = test_client.get("/api/tasks")
    assert response.status_code == 200
    assert response.get_json()["tasks"] == []


def test_list_tasks_returns_created(client):
    test_client, _ = client
    _crear_tarea(test_client)
    _crear_tarea(test_client, title="Documentar endpoints")
    tasks = test_client.get("/api/tasks").get_json()["tasks"]
    assert [t["title"] for t in tasks] == ["Documentar endpoints", "Configurar CI"]


def test_update_task_success(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={
        "title": "Configurar CI/CD", "assignee": "Carlos Ruiz", "priority": "baja",
        "description": "Nueva descripción", "status": "en progreso"})
    assert response.status_code == 200
    updated = response.get_json()["task"]
    assert updated["id"] == task["id"]
    assert updated["title"] == "Configurar CI/CD"
    assert updated["assignee"] == "Carlos Ruiz"
    assert updated["priority"] == "baja"
    assert updated["description"] == "Nueva descripción"
    assert updated["status"] == "en progreso"


def test_update_task_partial_keeps_other_fields(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={"status": "completada"})
    assert response.status_code == 200
    updated = response.get_json()["task"]
    assert updated["status"] == "completada"
    assert updated["title"] == "Configurar CI"
    assert updated["assignee"] == "Ana López"


def test_update_task_persists_in_database(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    test_client.put(f"/api/tasks/{task['id']}", json={"title": "Título editado"})
    tasks = test_client.get("/api/tasks").get_json()["tasks"]
    assert tasks[0]["title"] == "Título editado"


def test_update_task_not_found(client):
    test_client, _ = client
    response = test_client.put("/api/tasks/999", json={"title": "X"})
    assert response.status_code == 404


def test_update_task_empty_title(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={"title": "   "})
    assert response.status_code == 400


def test_update_task_invalid_priority(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={"priority": "urgente"})
    assert response.status_code == 400


def test_update_task_invalid_status(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={"status": "terminada"})
    assert response.status_code == 400


def test_update_task_invalid_json(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", data="no es json",
                               content_type="text/plain")
    assert response.status_code == 400


def test_update_task_without_valid_fields(client):
    test_client, _ = client
    task = _crear_tarea(test_client)
    response = test_client.put(f"/api/tasks/{task['id']}", json={"foo": "bar"})
    assert response.status_code == 400
