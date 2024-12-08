document.addEventListener("DOMContentLoaded", function () {
    const notificacionesContainer = document.getElementById("notificaciones-container");

    if (notificacionesContainer) {
        const notificaciones = JSON.parse(notificacionesContainer.dataset.notificaciones);

        notificaciones.forEach((notificacion) => {
            const alerta = document.createElement("div");
            alerta.className = `alert alert-${notificacion.tipo} fade show alert-dismissible`;
            alerta.role = "alert";
            alerta.innerHTML = `
                <strong>${notificacion.titulo || "Notificación"}</strong> ${notificacion.mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            notificacionesContainer.appendChild(alerta);

            // Desaparecer automáticamente después de 5 segundos
            setTimeout(() => alerta.remove(), 5000);
        });
    }
});