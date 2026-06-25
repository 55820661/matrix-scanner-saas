(() => {
  const chatkit = document.getElementById("matrix-admin-chatkit");
  const livePanel = document.getElementById("matrix-live-ai");
  const status = document.getElementById("matrix-live-ai-status");
  const error = document.getElementById("matrix-live-ai-error");

  if (!chatkit || !livePanel || !status || !error) return;

  function showError(message) {
    if (message) {
      error.textContent = message;
      error.hidden = false;
    }
  }

  function clearError() {
    error.textContent = "";
    error.hidden = true;
  }

  window.addEventListener("load", async () => {
    try {
      await Promise.race([
        customElements.whenDefined("openai-chatkit"),
        new Promise((_, reject) => setTimeout(() => reject(new Error("ChatKit CDN timeout")), 10000)),
      ]);
      const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
      chatkit.setOptions({
        api: {
          url: livePanel.dataset.apiUrl,
          domainKey: livePanel.dataset.domainKey,
          fetch: (input, init = {}) => {
            clearError();
            const headers = new Headers(init.headers || {});
            if (csrfInput) headers.set("X-CSRFToken", csrfInput.value);
            return window.fetch(input, { ...init, headers, credentials: "same-origin" }).then((response) => {
              if (response.ok) clearError();
              return response;
            });
          },
        },
        initialThread: livePanel.dataset.threadId,
        header: { enabled: false },
        history: { enabled: false },
        locale: document.documentElement.lang || navigator.language || "en-US",
        theme: {
          colorScheme: "dark",
          color: { accent: { primary: "#22d3ee", level: 2 } },
          radius: "round",
          density: "compact",
          typography: { fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif" },
        },
        composer: {
          placeholder: "Ask about the selected account, server, findings, or reports...",
          attachments: { enabled: false },
          tools: [],
        },
      });
      status.textContent = "Live AI ready. Responses use fresh, capped, redacted Safe Context.";
      chatkit.addEventListener("chatkit.error", () => {
        showError("Live AI is temporarily unavailable. Please try again.");
      });
    } catch (initializationError) {
      livePanel.classList.add("chatkit-unavailable");
      showError("Live AI could not load. Please refresh and try again.");
    }
  });
})();
