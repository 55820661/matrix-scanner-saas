(() => {
  const livePanel = document.getElementById("matrix-live-ai");
  const chatkitBody = livePanel ? livePanel.querySelector(".matrix-live-ai-body") : null;
  const bundleIndicator = document.getElementById("matrix-live-ai-bundle-indicator");

  if (!chatkitBody || !livePanel) return;

  window.addEventListener("load", async () => {
    try {
      await Promise.race([
        customElements.whenDefined("openai-chatkit"),
        new Promise((_, reject) => setTimeout(() => reject(new Error("ChatKit CDN timeout")), 10000)),
      ]);
      const csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
      const POLL_INTERVAL_MS = 3000;
      const MAX_POLL_ATTEMPTS = 40;
      let chatkit = null;
      let bundlePollingPromise = null;
      let lastCompletedBundleExecutionId = "";

      const setBundleIndicator = (running) => {
        if (!bundleIndicator) return;
        bundleIndicator.classList.toggle("is-visible", running);
        bundleIndicator.setAttribute("aria-hidden", running ? "false" : "true");
      };

      const fetchBundleStatus = async () => {
        if (!livePanel.dataset.bundleStatusUrl) {
          return null;
        }
        const response = await window.fetch(livePanel.dataset.bundleStatusUrl, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) {
          return null;
        }
        return response.json();
      };

      const chatkitOptions = () => ({
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

      const mountChatKit = async () => {
        const nextChatkit = document.createElement("openai-chatkit");
        nextChatkit.id = "matrix-admin-chatkit";
        nextChatkit.setAttribute("dir", "auto");
        chatkitBody.replaceChildren(nextChatkit);
        chatkit = nextChatkit;
        chatkit.setOptions(chatkitOptions());
        await new Promise((resolve) => window.setTimeout(resolve, 0));
      };

      const refreshChatHistory = async () => {
        await mountChatKit();
      };

      const pollBundleUntilComplete = async () => {
        if (bundlePollingPromise || !livePanel.dataset.bundleStatusUrl) {
          return bundlePollingPromise;
        }
        bundlePollingPromise = (async () => {
          let activeBundleExecutionId = "";
          for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
            const status = await fetchBundleStatus().catch(() => null);
            if (!status) {
              break;
            }
            if (status.running && status.running_execution_id) {
              activeBundleExecutionId = status.running_execution_id;
            }
            setBundleIndicator(Boolean(status.running));
            const finalizedCurrentBundle =
              activeBundleExecutionId &&
              !status.running &&
              status.latest_result_id &&
              status.latest_result_execution_id === activeBundleExecutionId &&
              ["succeeded", "partial", "timeout", "failed"].includes(status.latest_result_state) &&
              status.latest_result_execution_id !== lastCompletedBundleExecutionId;
            if (finalizedCurrentBundle) {
              lastCompletedBundleExecutionId = status.latest_result_execution_id;
              await refreshChatHistory();
              setBundleIndicator(false);
              return;
            }
            if (!status.running && !activeBundleExecutionId) {
              setBundleIndicator(false);
              return;
            }
            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
          }
          setBundleIndicator(false);
        })();
        try {
          await bundlePollingPromise;
        } finally {
          bundlePollingPromise = null;
        }
      };

      await mountChatKit();
      const initialBundleStatus = await fetchBundleStatus().catch(() => null);
      if (initialBundleStatus && initialBundleStatus.running) {
        setBundleIndicator(true);
        pollBundleUntilComplete().catch(() => {});
      }
    } catch (initializationError) {
      livePanel.classList.add("chatkit-unavailable");
    }
  });
})();
