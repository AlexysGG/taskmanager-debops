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
