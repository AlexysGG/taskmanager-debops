document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("task-form");
    const taskIdInput = document.getElementById("task-id");
    const formTitle = document.getElementById("form-title");
    const formSubtitle = document.getElementById("form-subtitle");
    const feedback = document.getElementById("feedback");
    const submitBtn = document.getElementById("submit-btn");
    const cancelEditBtn = document.getElementById("cancel-edit-btn");
    const tasksList = document.getElementById("tasks-list");
    const tasksSummary = document.getElementById("tasks-summary");
    const filterStatus = document.getElementById("filter-status");
    const filterPriority = document.getElementById("filter-priority");

    let cachedTasks = [];

    function showFeedback(message, type) {
        feedback.textContent = message;
        feedback.className = `feedback ${type}`;
    }

    function resetFormMode() {
        taskIdInput.value = "";
        form.reset();
        form.priority.value = "media";
        formTitle.textContent = "Registrar nueva tarea";
        formSubtitle.textContent = "Complete los datos para agregar una actividad al sistema.";
        submitBtn.textContent = "Registrar tarea";
        cancelEditBtn.classList.add("hidden");
    }

    function enterEditMode(task) {
        taskIdInput.value = task.id;
        form.title.value = task.title;
        form.assignee.value = task.assignee;
        form.priority.value = task.priority;
        form.description.value = task.description || "";
        formTitle.textContent = `Editar tarea #${task.id}`;
        formSubtitle.textContent = "Modifique los campos necesarios y guarde los cambios.";
        submitBtn.textContent = "Guardar cambios";
        cancelEditBtn.classList.remove("hidden");
        form.scrollIntoView({ behavior: "smooth", block: "start" });
    }

        function renderTasks(tasks) {
            const total = tasks.length;
            const pendientes = tasks.filter((t) => t.status === "pendiente").length;
            const enProceso = tasks.filter((t) => t.status === "en_proceso").length;
            const terminadas = tasks.filter((t) => t.status === "terminada").length;

            tasksSummary.textContent =
                `Total: ${total} · Pendientes: ${pendientes} · En proceso: ${enProceso} · Terminadas: ${terminadas}`;

                tasksList.innerHTML = "";

                if (total === 0) {
                    const empty = document.createElement("div");
                    empty.className = "empty-state";
                    empty.textContent = "No hay tareas registradas con los filtros actuales.";
                    tasksList.appendChild(empty);
                    return;
                }

                tasks.forEach((task) => {
                    const item = document.createElement("article");
                    item.className = "task-item";

            const top = document.createElement("div");
            top.className = "task-top";

            const info = document.createElement("div");
            const title = document.createElement("h3");
            title.className = `task-title${task.status === "terminada" ? " done" : ""}`;
            title.textContent = `#${task.id} · ${task.title}`;

            const meta = document.createElement("p");
            meta.className = "task-meta";
            meta.textContent = `Responsable: ${task.assignee}`;

                info.append(title, meta);

                const priorityBadge = document.createElement("span");
                priorityBadge.className = `priority-badge priority-${task.priority}`;
                priorityBadge.textContent = task.priority;

                    top.append(info, priorityBadge);
                    item.appendChild(top);

                    if (task.description) {
                        const desc = document.createElement("p");
                        desc.className = "task-description";
                        desc.textContent = task.description;
                        item.appendChild(desc);
                    }

                    const controls = document.createElement("div");
                    controls.className = "task-controls";

                    const statusSelect = document.createElement("select");
                    statusSelect.className = "status-select";
                    statusSelect.setAttribute("aria-label", `Estado de la tarea ${task.id}`);
                    [
                        { value: "pendiente", label: "Pendiente" },
                        { value: "en_proceso", label: "En proceso" },
                        { value: "terminada", label: "Terminada" },
                    ].forEach((opt) => {
                        const option = document.createElement("option");
                        option.value = opt.value;
                        option.textContent = opt.label;
                        option.selected = task.status === opt.value;
                        statusSelect.appendChild(option);
                    });

                    statusSelect.addEventListener("change", async () => {
                        await changeTaskStatus(task.id, statusSelect.value);
                    });

                    const actions = document.createElement("div");
                    actions.className = "task-actions";

                    const editBtn = document.createElement("button");
                    editBtn.type = "button";
                    editBtn.className = "btn-secondary";
                    editBtn.textContent = "Editar";
                    editBtn.addEventListener("click", () => enterEditMode(task));

                    const deleteBtn = document.createElement("button");
                    deleteBtn.type = "button";
                    deleteBtn.className = "btn-danger";
                    deleteBtn.textContent = "Eliminar";
                    deleteBtn.addEventListener("click", () => deleteTask(task.id));

                    actions.append(editBtn, deleteBtn);
                    controls.append(statusSelect, actions);
                    item.appendChild(controls);
                    tasksList.appendChild(item);
                });
        }

            async function loadTasks() {
                const params = new URLSearchParams();
                if (filterStatus.value) params.set("status", filterStatus.value);
                if (filterPriority.value) params.set("priority", filterPriority.value);

                const query = params.toString() ? `?${params.toString()}` : "";
                try {
                    const response = await fetch(`/api/tasks${query}`);
                    const data = await response.json();
                    if (!response.ok) {
                        showFeedback(data.error || "No se pudieron cargar las tareas.", "error");
                        return;
                    }
                    cachedTasks = data.tasks;
                    renderTasks(cachedTasks);
                } catch (error) {
                    showFeedback("Error al consultar las tareas del servidor.", "error");
                }
            }

            async function changeTaskStatus(taskId, newStatus) {
                try {
                    const response = await fetch(`/api/tasks/${taskId}/status`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ status: newStatus }),
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        showFeedback(data.error || "No se pudo actualizar el estado.", "error");
                        await loadTasks();
                        return;
                    }
                    showFeedback(`Estado de la tarea #${taskId} actualizado a "${newStatus}".`, "success");
                    await loadTasks();
                } catch (error) {
                    showFeedback("Error de conexión al actualizar el estado.", "error");
                }
            }

                async function deleteTask(taskId) {
                    try {
                        const response = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
                        const data = await response.json();
                        if (!response.ok) {
                            showFeedback(data.error || "No se pudo eliminar la tarea.", "error");
                            return;
                        }
                        if (Number(taskIdInput.value) === taskId) {
                            resetFormMode();
                        }
                        showFeedback(`Tarea #${taskId} eliminada correctamente.`, "success");
                        await loadTasks();
                    } catch (error) {
                        showFeedback("Error de conexión al eliminar la tarea.", "error");
                    }
                }

                form.addEventListener("submit", async (event) => {
                    event.preventDefault();

                    const payload = {
                        title: form.title.value.trim(),
                        assignee: form.assignee.value.trim(),
                        priority: form.priority.value,
                        description: form.description.value.trim(),
                    };

                    if (!payload.title || !payload.assignee) {
                        showFeedback("Por favor completa el título y el responsable de la tarea.", "error");
                        return;
                    }

const editingId = taskIdInput.value;
const url = editingId ? `/api/tasks/${editingId}` : "/api/tasks";
const method = editingId ? "PUT" : "POST";

submitBtn.disabled = true;

try {
    const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
        showFeedback(data.error || "No se pudo guardar la tarea.", "error");
        return;
    }

    showFeedback(
        editingId
            ? `Tarea #${data.task.id} actualizada correctamente.`
            : `Tarea #${data.task.id} "${data.task.title}" registrada correctamente.`,
        "success"
    );
    resetFormMode();
    await loadTasks();
} catch (error) {
    showFeedback("Error de conexión con el servidor.", "error");
} finally {
    submitBtn.disabled = false;
}
    });

cancelEditBtn.addEventListener("click", resetFormMode);
filterStatus.addEventListener("change", loadTasks);
filterPriority.addEventListener("change", loadTasks);

loadTasks();
});
