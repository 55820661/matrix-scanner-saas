(() => {
  const livePanel = document.getElementById("matrix-live-ai");
  const chatkitBody = livePanel ? livePanel.querySelector(".matrix-live-ai-body") : null;
  const bundleIndicator = document.getElementById("matrix-live-ai-bundle-indicator");
  const fallbackResults = document.getElementById("matrix-live-ai-fallback-results");

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
      const FINAL_STATES = ["succeeded", "partial", "timeout", "failed"];
      let chatkit = null;
      let bundlePollingPromise = null;
      const completedBundleIds = new Set();
      const fetchedBundleIds = new Set();
      let fallbackNoticeShownForBundleId = "";

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

      const bundleExecutionStatusUrl = (bundleExecutionId) => {
        if (!livePanel.dataset.bundleStatusTemplate || !bundleExecutionId) {
          return "";
        }
        return livePanel.dataset.bundleStatusTemplate.replace("BUNDLE_EXECUTION_ID", encodeURIComponent(bundleExecutionId));
      };

      const fetchBundleExecutionStatus = async (bundleExecutionId) => {
        const url = bundleExecutionStatusUrl(bundleExecutionId);
        if (!url) {
          return null;
        }
        const response = await window.fetch(url, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) {
          return null;
        }
        return response.json();
      };

      const hasRenderedFallback = (chatkitItemId) => {
        if (!fallbackResults || !chatkitItemId) {
          return false;
        }
        return Boolean(fallbackResults.querySelector(`[data-chatkit-item-id="${CSS.escape(chatkitItemId)}"]`));
      };

      const renderFallbackCard = (payload) => {
        if (!fallbackResults || !payload || !payload.chatkit_item_id || hasRenderedFallback(payload.chatkit_item_id)) {
          return;
        }
        const card = document.createElement("article");
        card.className = "matrix-live-ai-fallback-card";
        card.dataset.chatkitItemId = payload.chatkit_item_id;
        card.innerHTML = `<strong>Matrix Live Admin AI</strong><div class="body"></div>`;
        card.querySelector(".body").textContent = payload.body || "";
        fallbackResults.appendChild(card);
      };

      const renderFallbackNotice = (bundleExecutionId) => {
        if (!fallbackResults || !bundleExecutionId || fallbackNoticeShownForBundleId === bundleExecutionId) {
          return;
        }
        fallbackNoticeShownForBundleId = bundleExecutionId;
        const note = document.createElement("article");
        note.className = "matrix-live-ai-fallback-note";
        note.dataset.bundleExecutionId = bundleExecutionId;
        note.innerHTML =
          `<strong>Matrix Live Admin AI</strong><div class="body">تعذر تحديث نتيجة الفحص تلقائيًا. يمكنك تحديث الصفحة لعرض آخر حالة.</div>`;
        fallbackResults.appendChild(note);
      };

      const syncChatKitUpdates = async (bundleExecutionId) => {
        if (!chatkit || !bundleExecutionId || fetchedBundleIds.has(bundleExecutionId)) {
          return true;
        }
        if (typeof chatkit.fetchUpdates !== "function") {
          console.warn("ChatKit fetchUpdates() is unavailable for diagnostic bundle sync.", {
            bundleExecutionId,
          });
          return false;
        }
        try {
          await chatkit.fetchUpdates();
          fetchedBundleIds.add(bundleExecutionId);
          return true;
        } catch (error) {
          console.warn("ChatKit fetchUpdates() failed for diagnostic bundle sync.", {
            bundleExecutionId,
            error,
          });
          return false;
        }
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
            const finalizedCurrentBundle = activeBundleExecutionId && !status.running;
            if (finalizedCurrentBundle) {
              const bundleStatus = await fetchBundleExecutionStatus(activeBundleExecutionId).catch(() => null);
              if (
                bundleStatus &&
                FINAL_STATES.includes(bundleStatus.state) &&
                !completedBundleIds.has(bundleStatus.bundle_execution_id)
              ) {
                completedBundleIds.add(bundleStatus.bundle_execution_id);
                const updatesSynced = await syncChatKitUpdates(bundleStatus.bundle_execution_id);
                if (!updatesSynced) {
                  renderFallbackCard(bundleStatus.final_message);
                }
              }
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
          if (activeBundleExecutionId && !completedBundleIds.has(activeBundleExecutionId)) {
            renderFallbackNotice(activeBundleExecutionId);
          }
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
