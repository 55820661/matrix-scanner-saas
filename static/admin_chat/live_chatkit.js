(() => {
  const chatkit = document.getElementById("matrix-admin-chatkit");
  const livePanel = document.getElementById("matrix-live-ai");
  const fallback = document.getElementById("deterministic-fallback");
  const status = document.getElementById("matrix-live-ai-status");
  const error = document.getElementById("matrix-live-ai-error");
  const fallbackButton = document.getElementById("show-deterministic-fallback");

  if (!chatkit || !livePanel || !fallback || !status || !error || !fallbackButton) return;

  function showFallback(message) {
    fallback.classList.remove("is-hidden");
    if (message) {
      error.textContent = message;
      error.hidden = false;
    }
  }

  fallbackButton.addEventListener("click", () => {
    fallback.classList.toggle("is-hidden");
  });

  window.addEventListener("load", async () => {
    try {
      await Promise.race([
        customElements.whenDefined("openai-chatkit"),
        new Promise((_, reject) => setTimeout(() => reject(new Error("ChatKit CDN timeout")), 10000)),
      ]);
      const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
      chatkit.setOptions({
        apiURL: livePanel.dataset.apiUrl,
        initialThread: livePanel.dataset.threadId,
        header: false,
        history: { enabled: false },
        locale: document.documentElement.lang || navigator.language || "en-US",
        theme: {
          colorScheme: "dark",
          color: { accent: { primary: "#22d3ee", level: 2 } },
          radius: "round",
          density: "compact",
          typography: { fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif" },
        },
        composer: { placeholder: "Ask about the selected account, server, findings, or reports..." },
        fetch: (input, init = {}) => {
          const headers = new Headers(init.headers || {});
          if (csrfInput) headers.set("X-CSRFToken", csrfInput.value);
          return window.fetch(input, { ...init, headers, credentials: "same-origin" });
        },
      });
      status.textContent = "Live AI ready. Responses use fresh, capped, redacted Safe Context.";
      chatkit.addEventListener("chatkit.error", () => {
        showFallback("Live AI UI failed. The deterministic fallback remains available below.");
      });
    } catch (initializationError) {
      livePanel.classList.add("chatkit-unavailable");
      showFallback("ChatKit could not load. The deterministic fallback remains available below.");
    }
  });
})();
