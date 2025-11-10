document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector("header");
  const headerHeight = header ? header.offsetHeight : 0;

  // 1) Scroll suave para enlaces con href="#..."
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const hash = a.getAttribute("href");
      if (!hash || hash === "#" || hash.length === 1) return;
      const target = document.querySelector(hash);
      if (!target) return;

      e.preventDefault();

      // Compensa el header fijo
      const targetY =
        target.getBoundingClientRect().top + window.scrollY - headerHeight - 10;

      window.scrollTo({ top: targetY, behavior: "smooth" });

      // Opcional: actualiza el hash sin “salto”
      history.pushState(null, "", hash);
    });
  });

  // 2) Resaltar el link activo según la sección visible
  const navLinks = Array.from(document.querySelectorAll("nav a[href^='#']"));
  const sections = navLinks
    .map((l) => document.querySelector(l.getAttribute("href")))
    .filter(Boolean);

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const id = "#" + entry.target.id;
        const link = navLinks.find((l) => l.getAttribute("href") === id);
        if (!link) return;

        if (entry.isIntersecting) {
          navLinks.forEach((l) => l.classList.remove("active"));
          link.classList.add("active");
        }
      });
    },
    {
      // Más sensible para marcar activo
      threshold: 0.25,
      // Compensa header y hace que “entre” antes
      rootMargin: `-${headerHeight}px 0px -55% 0px`,
    }
  );

  sections.forEach((sec) => io.observe(sec));

  // 3) Sombra en el header solo cuando haces scroll
  const updateHeaderShadow = () => {
    if (!header) return;
    header.classList.toggle("scrolled", window.scrollY > 10);
  };
  updateHeaderShadow();
  window.addEventListener("scroll", updateHeaderShadow, { passive: true });
});

// === Envío del formulario sin recargar (mensaje en la misma página) ===
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#contact-form");
  const statusBox = document.querySelector("#contact-status");
  if (!form || !statusBox) return;

  const setStatus = (msg, ok) => {
    statusBox.textContent = msg || "";
    statusBox.classList.remove("is-success", "is-error");
    statusBox.classList.add(ok ? "is-success" : "is-error");
    statusBox.style.display = msg ? "block" : "none";
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus("Enviando…", true);

    try {
      const formData = new FormData(form);
      const res = await fetch(form.action || "/contact", {
        method: "POST",
        body: formData,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data?.ok) {
        setStatus(data?.error || "No se pudo enviar. Intenta nuevamente.", false);
        return;
      }

      setStatus("¡Mensaje enviado! Te responderemos pronto.", true);
      form.reset();
    } catch (err) {
      setStatus("Error de red. Revisa tu conexión e intenta otra vez.", false);
    }
  });
});
