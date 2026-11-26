document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("task-form");
  const feedback = document.getElementById("feedback");
  const submitBtn = document.getElementById("submit-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const statusGroup = document.getElementById("status-group");
  const formTitle = document.getElementById("form-title");
  const taskList = document.getElementById("task-list");

  let editingId = null;

  function showFeedback(message, type) {
    feedback.textContent = message;
    feedback.className = `feedback ${type}`;
  }

  function resetForm() {
    form.reset();
    form.elements.priority.value = "media";
    editingId = null;
    statusGroup.hidden = true;
    cancelBtn.hidden = true;
    submitBtn.textContent = "Registrar tarea";
    formTitle.textContent = "Registrar nueva tarea";
  }

  function startEdit(task) {
    editingId = task.id;
    form.elements.title.value = task.title;
    form.elements.assignee.value = task.assignee;
    form.elements.priority.value = task.priority;
    form.elements.description.value = task.description;
    form.elements.status.value = task.status;
    statusGroup.hidden = false;
    cancelBtn.hidden = false;
    submitBtn.textContent = "Guardar cambios";
    formTitle.textContent = `Editar tarea #${task.id}`;
    feedback.className = "feedback hidden";
    form.scrollIntoView({ behavior: "smooth" });
  }

  function renderTasks(tasks) {
    taskList.replaceChildren();

    if (tasks.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "Aún no hay tareas registradas.";
      taskList.appendChild(empty);
      return;
    }

    tasks.forEach((task) => {
      const item = document.createElement("article");
      item.className = "task-item";

      const info = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `#${task.id} ${task.title}`;
      const meta = document.createElement("p");
      meta.className = "task-meta";
      meta.textContent = `${task.assignee} · prioridad ${task.priority} · ${task.status}`;
      info.append(title, meta);

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn-secondary";
      editBtn.textContent = "Editar";
      editBtn.addEventListener("click", () => startEdit(task));

      item.append(info, editBtn);
      taskList.appendChild(item);
    });
  }

  async function loadTasks() {
    try {
      const response = await fetch("/api/tasks");
      const data = await response.json();
      renderTasks(data.tasks);
    } catch (error) {
      showFeedback("No se pudo cargar la lista de tareas.", "error");
    }
  }

  cancelBtn.addEventListener("click", () => {
    resetForm();
    feedback.className = "feedback hidden";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      title: form.elements.title.value.trim(),
      assignee: form.elements.assignee.value.trim(),
      priority: form.elements.priority.value,
      description: form.elements.description.value.trim(),
    };

    if (!payload.title || !payload.assignee) {
      showFeedback(
        "Por favor completa el título y el responsable de la tarea.",
        "error",
      );
      return;
    }

    const isEditing = editingId !== null;
    if (isEditing) {
      payload.status = form.elements.status.value;
    }

    submitBtn.disabled = true;

    try {
      const response = await fetch(
        isEditing ? `/api/tasks/${editingId}` : "/api/tasks",
        {
          method: isEditing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        showFeedback(
          data.error ||
            (isEditing
              ? "No se pudo actualizar la tarea."
              : "No se pudo registrar la tarea."),
          "error",
        );
        return;
      }

      if (isEditing) {
        showFeedback(
          `Tarea #${data.task.id} "${data.task.title}" actualizada correctamente.`,
          "success",
        );
      } else {
        showFeedback(
          `Tarea #${data.task.id} "${data.task.title}" registrada (estado: ${data.task.status}, prioridad: ${data.task.priority}).`,
          "success",
        );
      }

      resetForm();
      loadTasks();
    } catch (error) {
      showFeedback("Error de conexión con el servidor.", "error");
    } finally {
      submitBtn.disabled = false;
    }
  });

  loadTasks();
});
