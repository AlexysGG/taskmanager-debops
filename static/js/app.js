document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("task-form");
    const feedback = document.getElementById("feedback");
    const submitBtn = document.getElementById("submit-btn");

    function showFeedback(message, type) {
        feedback.textContent = message;
        feedback.className = `feedback ${type}`;
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

        submitBtn.disabled = true;

        try {
            const response = await fetch("/api/tasks", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                showFeedback(data.error || "No se pudo registrar la tarea.", "error");
                return;
            }

            showFeedback(
                `Tarea #${data.task.id} "${data.task.title}" registrada (estado: ${data.task.status}, prioridad: ${data.task.priority}).`,
                "success"
            );
            form.reset();
            form.priority.value = "media";
        } catch (error) {
            showFeedback("Error de conexión con el servidor.", "error");
        } finally {
            submitBtn.disabled = false;
        }
    });
});
