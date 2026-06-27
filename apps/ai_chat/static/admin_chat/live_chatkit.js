(() => {
  const chatkit = document.getElementById("matrix-admin-chatkit");
  const livePanel = document.getElementById("matrix-live-ai");

  if (!chatkit || !livePanel) return;

  window.addEventListener("load", async () => {
    try {
      let bundlePolling = false;
      const pollBundleUntilComplete = async () => {
        if (bundlePolling || !livePanel.dataset.bundleStatusUrl) return;
        bundlePolling = true;
        let sawRunningBundle = false;
        for (let attempt = 0; attempt < 40; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 3000));
          const response = await window.fetch(livePanel.dataset.bundleStatusUrl, {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
          });
          if (!response.ok) break;
          const status = await response.json();
          sawRunningBundle = sawRunningBundle || status.running;
          if (sawRunningBundle && !status.running && status.latest_result_id) {
            window.location.reload();
            return;
          }
          if (!status.running && !sawRunningBundle) break;
        }
        bundlePolling = false;
      };
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
            const headers = new Headers(init.headers || {});
            if (csrfInput) headers.set("X-CSRFToken", csrfInput.value);
            const response = window.fetch(input, { ...init, headers, credentials: "same-origin" });
            if ((init.method || "GET").toUpperCase() === "POST") {
              response.then(() => pollBundleUntilComplete()).catch(() => {});
            }
            return response;
          },
        },
        initialThread: livePanel.dataset.threadId,
        header: { enabled: false },
        history: { enabled: true },
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
    } catch (initializationError) {
      livePanel.classList.add("chatkit-unavailable");
    }
  });
})();
