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
    assert "Tareas registradas" in html


def test_health_endpoint(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_cp01_registrar_una_tarea(client):
    """CP01: Registrar una tarea -> La tarea se guarda correctamente."""
    test_client, db_file = client
    payload = {
        "title": "Realizar actividad DevOps",
        "assignee": "Ana López",
        "description": "Configurar pruebas automatizadas en GitHub Actions.",
    }
    response = test_client.post("/api/tasks", json=payload)
    assert response.status_code == 201

    task = response.get_json()["task"]
    assert task["id"] == 1
    assert task["title"] == "Realizar actividad DevOps"
    assert task["assignee"] == "Ana López"
    assert task["status"] == "pendiente"
    assert task["priority"] == "media"

    conn = sqlite3.connect(db_file)
    row = conn.execute("SELECT title, assignee, status FROM tasks WHERE id = 1").fetchone()
    conn.close()
    assert row == ("Realizar actividad DevOps", "Ana López", "pendiente")


def test_cp02_registrar_tarea_sin_nombre(client):
    """CP02: Registrar una tarea sin nombre -> El sistema muestra una validación."""
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": "   ", "assignee": "Ana López"},
    )
    assert response.status_code == 400
    assert "título" in response.get_json()["error"].lower()


def test_cp03_consultar_tareas(client):
    """CP03: Consultar tareas -> Se muestra el listado."""
    test_client, _ = client
    test_client.post("/api/tasks", json={"title": "Tarea 1", "assignee": "Ana"})
    test_client.post("/api/tasks", json={"title": "Tarea 2", "assignee": "Carlos"})

    response = test_client.get("/api/tasks")
    assert response.status_code == 200
    tasks = response.get_json()["tasks"]
    assert len(tasks) == 2
    assert [t["title"] for t in tasks] == ["Tarea 2", "Tarea 1"]


def test_cp04_editar_una_tarea(client):
    """CP04: Editar una tarea -> Se actualiza la información."""
    test_client, _ = client
    created = test_client.post(
        "/api/tasks",
        json={"title": "Tarea original", "assignee": "Ana", "description": "Detalle inicial"},
    ).get_json()["task"]

    response = test_client.put(
        f"/api/tasks/{created['id']}",
        json={
            "title": "Tarea editada",
            "assignee": "Carlos Ruiz",
            "description": "Detalle actualizado",
            "priority": "alta",
        },
    )
    assert response.status_code == 200
    updated = response.get_json()["task"]
    assert updated["title"] == "Tarea editada"
    assert updated["assignee"] == "Carlos Ruiz"
    assert updated["description"] == "Detalle actualizado"
    assert updated["priority"] == "alta"


def test_cp05_eliminar_una_tarea(client):
    """CP05: Eliminar una tarea -> La tarea desaparece del listado."""
    test_client, _ = client
    created = test_client.post(
        "/api/tasks",
        json={"title": "Tarea temporal", "assignee": "Ana"},
    ).get_json()["task"]

    delete_res = test_client.delete(f"/api/tasks/{created['id']}")
    assert delete_res.status_code == 200

    list_res = test_client.get("/api/tasks")
    assert list_res.get_json()["tasks"] == []


def test_cp06_cambiar_estado(client):
    """CP06: Cambiar estado -> Se actualiza el estado."""
    test_client, _ = client
    created = test_client.post(
        "/api/tasks",
        json={"title": "Implementar CI", "assignee": "Ana"},
    ).get_json()["task"]
    assert created["status"] == "pendiente"

    for new_status in ("en_proceso", "terminada", "pendiente"):
        res = test_client.patch(
            f"/api/tasks/{created['id']}/status",
            json={"status": new_status},
        )
        assert res.status_code == 200
        assert res.get_json()["task"]["status"] == new_status


@pytest.mark.parametrize("priority", ["alta", "media", "baja"])
def test_cp07_seleccionar_prioridad(client, priority):
    """CP07: Seleccionar prioridad -> Se guarda la prioridad elegida."""
    test_client, _ = client
    response = test_client.post(
        "/api/tasks",
        json={"title": f"Tarea {priority}", "assignee": "Ana", "priority": priority},
    )
    assert response.status_code == 201
    assert response.get_json()["task"]["priority"] == priority


def test_validaciones_y_errores(client):
    test_client, _ = client

    res_assignee = test_client.post("/api/tasks", json={"title": "Sin responsable", "assignee": ""})
    assert res_assignee.status_code == 400

    res_priority = test_client.post(
        "/api/tasks",
        json={"title": "Prioridad inválida", "assignee": "Ana", "priority": "urgente"},
    )
    assert res_priority.status_code == 400

    created = test_client.post("/api/tasks", json={"title": "Valida", "assignee": "Ana"}).get_json()["task"]
    res_status = test_client.patch(f"/api/tasks/{created['id']}/status", json={"status": "bloqueada"})
    assert res_status.status_code == 400

    assert test_client.put("/api/tasks/999", json={"title": "No existe"}).status_code == 404
    assert test_client.patch("/api/tasks/999/status", json={"status": "terminada"}).status_code == 404
    assert test_client.delete("/api/tasks/999").status_code == 404
