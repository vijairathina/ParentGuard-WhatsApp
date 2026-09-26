// ParentGuard WhatsApp - Client Application & Safety Guardian
document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let accounts = [];
    let activeAccountId = "";
    let activeContactJid = "";
    let contacts = [];
    let activeFilter = "all"; // "all", "chats", "groups"
    let qrSessionId = "";
    let eventSource = null;
    let currentAccountSettings = null;
    let unreadAlertCount = 0;

    // DOM Elements - Main Layout
    const dropdown = document.getElementById("account-dropdown");
    const activeAvatar = document.getElementById("active-account-avatar");
    const btnAddAccount = document.getElementById("btn-add-account");
    const btnDeleteAccount = document.getElementById("btn-delete-account");
    const btnOpenSettings = document.getElementById("btn-open-settings");
    const btnOpenLogs = document.getElementById("btn-open-logs");
    const alertCounterBadge = document.getElementById("alert-counter-badge");
    const chatSearch = document.getElementById("chat-search");
    const contactsList = document.getElementById("contacts-list");
    
    const emptyState = document.getElementById("empty-state");
    const chatWindow = document.getElementById("chat-window");
    const chatAvatar = document.getElementById("chat-avatar");
    const chatContactName = document.getElementById("chat-contact-name");
    const chatContactJid = document.getElementById("chat-contact-jid");
    const messagePanel = document.getElementById("message-panel");
    const messageForm = document.getElementById("message-form");
    const messageInput = document.getElementById("message-input");

    // Add Account / QR Modal Elements
    const addAccountModal = document.getElementById("add-account-modal");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const qrLoading = document.getElementById("qr-loading");
    const qrImage = document.getElementById("qr-image");
    const qrStatusText = document.getElementById("qr-status-text");
    const qrStatusDot = document.getElementById("qr-status-dot");
    const btnEmptyAddAccount = document.getElementById("btn-empty-add-account");

    // Settings Modal Elements
    const settingsModal = document.getElementById("settings-modal");
    const btnCloseSettings = document.getElementById("btn-close-settings");
    const btnCancelSettings = document.getElementById("btn-cancel-settings");
    const btnSaveSettings = document.getElementById("btn-save-settings");
    const modalAccountBadge = document.getElementById("modal-account-badge");
    const settingAccountId = document.getElementById("setting-account-id");
    const settingAccountPhone = document.getElementById("setting-account-phone");
    const settingAccountStatus = document.getElementById("setting-account-status");
    const btnAccountLogin = document.getElementById("btn-account-login");
    const btnAccountLogout = document.getElementById("btn-account-logout");

    // Keywords & AI Elements
    const settingKeywordsEnabled = document.getElementById("setting-keywords-enabled");
    const settingMonitorDirection = document.getElementById("setting-monitor-direction");
    const settingKeywordsList = document.getElementById("setting-keywords-list");
    const settingGeminiEnabled = document.getElementById("setting-gemini-enabled");
    const settingGeminiKey = document.getElementById("setting-gemini-key");
    const btnToggleKeyVisibility = document.getElementById("btn-toggle-key-visibility");
    const settingGeminiSensitivity = document.getElementById("setting-gemini-sensitivity");
    const testGeminiInput = document.getElementById("test-gemini-input");
    const btnTestGemini = document.getElementById("btn-test-gemini");
    const testGeminiResult = document.getElementById("test-gemini-result");

    // Logs Elements
    const logsTableBody = document.getElementById("logs-table-body");
    const btnRefreshLogs = document.getElementById("btn-refresh-logs");
    const btnClearLogs = document.getElementById("btn-clear-logs");
    const btnExportLogs = document.getElementById("btn-export-logs");
    const toastContainer = document.getElementById("security-toast-container");

    // Webhooks & API Elements
    const webhookUrlInput = document.getElementById("webhook-url-input");
    const btnRegisterWebhook = document.getElementById("btn-register-webhook");
    const webhooksListContainer = document.getElementById("webhooks-list");

    // Initialize App
    init();

    async function init() {
        setupSSE();
        await loadAccounts();

        // Event Listeners
        dropdown.addEventListener("change", handleAccountSwitch);
        btnAddAccount.addEventListener("click", openAddAccountModal);
        btnEmptyAddAccount.addEventListener("click", openAddAccountModal);
        btnDeleteAccount.addEventListener("click", handleDeleteAccount);
        btnCloseModal.addEventListener("click", closeAddAccountModal);
        chatSearch.addEventListener("input", handleSearch);
        chatSearch.addEventListener("keydown", handleNewChatSearchEnter);
        messageForm.addEventListener("submit", handleSendMessage);

        // Filter Pills
        document.querySelectorAll(".filter-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activeFilter = pill.getAttribute("data-filter") || "all";
                applyFiltersAndRender();
            });
        });

        // Settings & Logs Modal Listeners
        btnOpenSettings.addEventListener("click", () => openSettingsModal("tab-theme"));
        btnOpenLogs.addEventListener("click", () => openSettingsModal("tab-logs"));
        btnCloseSettings.addEventListener("click", closeSettingsModal);
        btnCancelSettings.addEventListener("click", closeSettingsModal);
        btnSaveSettings.addEventListener("click", handleSaveSettings);

        btnAccountLogin.addEventListener("click", handleAccountLogin);
        btnAccountLogout.addEventListener("click", handleAccountLogout);

        btnRefreshLogs.addEventListener("click", loadAuditLogs);
        btnClearLogs.addEventListener("click", handleClearLogs);
        btnExportLogs.addEventListener("click", handleExportLogs);

        // Webhook Button
        if (btnRegisterWebhook) {
            btnRegisterWebhook.addEventListener("click", handleRegisterWebhook);
        }

        // Tab Navigation
        document.querySelectorAll(".modal-tabs .tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                switchSettingsTab(targetTab);
            });
        });

        // Theme live preview on radio change
        document.querySelectorAll("input[name='account-theme']").forEach(radio => {
            radio.addEventListener("change", (e) => {
                applyTheme(e.target.value);
            });
        });

        // Toggle Key Visibility
        btnToggleKeyVisibility.addEventListener("click", () => {
            if (settingGeminiKey.type === "password") {
                settingGeminiKey.type = "text";
                btnToggleKeyVisibility.textContent = "Hide";
            } else {
                settingGeminiKey.type = "password";
                btnToggleKeyVisibility.textContent = "Show";
            }
        });

        // Test Gemini AI
        btnTestGemini.addEventListener("click", handleTestGemini);
    }

    // --- SSE Event Stream Setup ---
    function setupSSE() {
        if (eventSource) {
            eventSource.close();
        }

        console.log("[SSE] Connecting to /api/events...");
        eventSource = new EventSource("/api/events");

        eventSource.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                if (payload.event === "welcome" || payload.event === "ping") {
                    return;
                }

                const { event: type, account_id, data } = payload;

                // Handle QR Event
                if (type === "qr") {
                    if (account_id === qrSessionId) {
                        qrLoading.style.display = "none";
                        qrImage.src = `data:image/png;base64,${data.qr}`;
                        qrImage.style.display = "block";
                        qrStatusDot.className = "status-dot warning";
                        qrStatusText.innerText = "Status: Scan session ready.";
                    }
                }

                // Handle Status Change Event
                else if (type === "status") {
                    updateAccountStatus(account_id, data.status, data);

                    if (account_id === qrSessionId && data.status === "Connected") {
                        closeAddAccountModal();
                        activeAccountId = account_id;
                        loadAccounts().then(() => {
                            dropdown.value = activeAccountId;
                            handleAccountSelectionChange();
                        });
                    } else if (account_id === activeAccountId) {
                        updateActiveAccountUI();
                        if (data.status === "Connected") {
                            loadContacts();
                        }
                    }
                }

                // Handle Message Event
                else if (type === "message") {
                    const { chat_jid, message } = data;
                    if (account_id === activeAccountId) {
                        updateContactLastMessage(chat_jid, message);
                    }

                    const normalizeLocal = (j) => (j || "").toString().split('@')[0];
                    const sameChat = (chat_jid === activeContactJid) || (
                        activeContactJid && normalizeLocal(chat_jid) === normalizeLocal(activeContactJid)
                    );

                    if (sameChat && account_id === activeAccountId) {
                        appendMessageBubble(message);
                        scrollToBottom();
                    }
                }

                // Handle Message Revoked (Anti-Delete Event!)
                else if (type === "message_revoked") {
                    const { chat_jid, target_id, message } = data;
                    if (account_id === activeAccountId) {
                        handleMessageRevokedUI(chat_jid, target_id, message);
                    }
                }

                // Handle Media Ready Event (Asynchronous Download Finished)
                else if (type === "media_ready") {
                    const { chat_jid, msg_id, local_url, type: mediaType } = data;
                    if (account_id === activeAccountId && chat_jid === activeContactJid) {
                        handleMediaReadyUI(msg_id, local_url, mediaType);
                    }
                }

                // Handle Realtime Security Alert Event (Parental Alert!)
                else if (type === "security_alert") {
                    handleSecurityAlertNotification(account_id, data);
                }

                // Handle Contacts Updated
                else if (type === "contacts_updated") {
                    if (account_id === activeAccountId) {
                        loadContacts();
                    }
                }

                // Handle Account Deleted Event
                else if (type === "deleted") {
                    if (account_id === qrSessionId) closeAddAccountModal();
                    if (account_id === activeAccountId) {
                        activeAccountId = "";
                        activeContactJid = "";
                        hideChatWindow();
                    }
                    loadAccounts();
                }

            } catch (err) {
                console.error("[SSE] Error parsing payload:", err);
            }
        };

        eventSource.onerror = (err) => {
            console.error("[SSE] Connection error. Retrying in 5s...", err);
            setTimeout(setupSSE, 5000);
        };
    }

    // --- Accounts Management ---
    async function loadAccounts() {
        try {
            const res = await fetch("/api/accounts");
            accounts = await res.json();
            renderAccountsDropdown();

            if (!activeAccountId && accounts && accounts.length) {
                const firstConnected = accounts.find(a => a.status === 'Connected') || accounts[0];
                if (firstConnected) {
                    activeAccountId = firstConnected.id;
                    dropdown.value = activeAccountId;
                    handleAccountSelectionChange();
                }
            }
        } catch (err) {
            console.error("Failed to load accounts:", err);
        }
    }

    function renderAccountsDropdown() {
        dropdown.innerHTML = '<option value="" disabled selected>Select Account</option>';
        accounts.forEach(acc => {
            const opt = document.createElement("option");
            opt.value = acc.id;
            opt.textContent = `${acc.name} (${acc.status})`;
            dropdown.appendChild(opt);
        });

        if (activeAccountId && accounts.some(a => a.id === activeAccountId)) {
            dropdown.value = activeAccountId;
            updateActiveAccountUI();
        } else {
            dropdown.value = "";
            activeAvatar.innerText = "PG";
            btnDeleteAccount.disabled = true;
            btnOpenSettings.disabled = true;
            btnOpenLogs.disabled = true;
            contactsList.innerHTML = `
                <div class="list-empty">
                    <p>Select a WhatsApp account to load chats.</p>
                </div>`;
        }
    }

    function handleAccountSwitch(e) {
        activeAccountId = e.target.value;
        activeContactJid = "";
        hideChatWindow();
        handleAccountSelectionChange();
    }

    async function handleAccountSelectionChange() {
        updateActiveAccountUI();
        await loadAccountSettings();
        loadContacts();
        loadAuditLogs();
        loadWebhooks();
        updateApiAccountLabels();
    }

    function updateActiveAccountUI() {
        const activeAcc = accounts.find(a => a.id === activeAccountId);
        if (activeAcc) {
            btnDeleteAccount.disabled = false;
            btnOpenSettings.disabled = false;
            btnOpenLogs.disabled = false;
            
            const name = activeAcc.name || "PG";
            activeAvatar.innerText = name.substring(0, 2).toUpperCase();
            
            if (activeAcc.status !== "Connected") {
                contactsList.innerHTML = `
                    <div class="list-empty">
                        <p>Status: <strong>${escapeHTML(activeAcc.status)}</strong></p>
                        ${activeAcc.status === "Waiting for Scan" ? 
                          `<button id="btn-reopen-qr" class="btn btn-primary">Scan QR Code</button>` : 
                          `<button id="btn-reconnect-now" class="btn btn-primary">Reconnect Session</button>`}
                    </div>`;
                
                const btnReopenQr = document.getElementById("btn-reopen-qr");
                if (btnReopenQr) {
                    btnReopenQr.addEventListener("click", () => {
                        qrSessionId = activeAcc.id;
                        openAddAccountModalDirect(activeAcc.qr);
                    });
                }

                const btnReconnectNow = document.getElementById("btn-reconnect-now");
                if (btnReconnectNow) {
                    btnReconnectNow.addEventListener("click", handleAccountLogin);
                }
            }
        } else {
            btnDeleteAccount.disabled = true;
            btnOpenSettings.disabled = true;
            btnOpenLogs.disabled = true;
            activeAvatar.innerText = "PG";
        }
    }

    function updateAccountStatus(accId, status, info) {
        const acc = accounts.find(a => a.id === accId);
        if (acc) {
            acc.status = status;
            if (info) {
                acc.name = info.name || acc.name;
                acc.phone = info.phone || acc.phone;
                acc.jid = info.jid || acc.jid;
            }
            renderAccountsDropdown();
        } else {
            loadAccounts();
        }
    }

    // --- Per-Account Settings & Theme ---
    async function loadAccountSettings() {
        if (!activeAccountId) return;
        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/settings`);
            currentAccountSettings = await res.json();
            
            const theme = currentAccountSettings.theme || "dark";
            applyTheme(theme);

            const activeAcc = accounts.find(a => a.id === activeAccountId) || {};
            modalAccountBadge.textContent = activeAcc.name || activeAccountId;
            settingAccountId.textContent = activeAccountId;
            settingAccountPhone.textContent = activeAcc.phone || "Not connected";
            settingAccountStatus.textContent = activeAcc.status || "Disconnected";
            settingAccountStatus.style.color = activeAcc.status === "Connected" ? "var(--wa-green)" : "var(--danger)";

            const themeRadio = document.querySelector(`input[name='account-theme'][value='${theme}']`);
            if (themeRadio) themeRadio.checked = true;

            const mon = currentAccountSettings.monitoring || {};
            settingKeywordsEnabled.checked = mon.keywords_enabled !== false;
            settingMonitorDirection.value = mon.direction || "all";
            settingKeywordsList.value = (mon.keywords || []).join(", ");
            settingGeminiEnabled.checked = !!mon.gemini_enabled;
            settingGeminiKey.value = mon.gemini_api_key || "";
            settingGeminiSensitivity.value = mon.gemini_sensitivity || "moderate";

        } catch (err) {
            console.error("Failed to load account settings:", err);
        }
    }

    function applyTheme(themeName) {
        document.body.setAttribute("data-theme", themeName);
    }

    async function handleSaveSettings() {
        if (!activeAccountId) return;

        const selectedThemeRadio = document.querySelector("input[name='account-theme']:checked");
        const theme = selectedThemeRadio ? selectedThemeRadio.value : "dark";

        const keywordsStr = settingKeywordsList.value || "";
        const keywords = keywordsStr.split(",")
            .map(k => k.trim())
            .filter(k => k.length > 0);

        const newSettings = {
            theme: theme,
            monitoring: {
                enabled: true,
                direction: settingMonitorDirection.value,
                keywords_enabled: settingKeywordsEnabled.checked,
                keywords: keywords,
                gemini_enabled: settingGeminiEnabled.checked,
                gemini_api_key: settingGeminiKey.value.trim(),
                gemini_sensitivity: settingGeminiSensitivity.value,
                notify_on_violation: true
            }
        };

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newSettings)
            });
            const data = await res.json();
            if (data.success) {
                currentAccountSettings = data.settings;
                applyTheme(theme);
                closeSettingsModal();
                showNotificationToast("Settings Saved", "Safety rules & appearance updated successfully.", "var(--wa-green)");
            }
        } catch (err) {
            console.error("Error saving settings:", err);
            alert("Failed to save settings.");
        }
    }

    // --- Session Lifecycle (Login / Logout / Delete) ---
    async function handleAccountLogin() {
        if (!activeAccountId) return;
        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/login`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                settingAccountStatus.textContent = "Connecting...";
                showNotificationToast("Connecting", "Initiating WhatsApp connection...", "var(--wa-green)");
            }
        } catch (err) {
            console.error("Error logging in:", err);
        }
    }

    async function handleAccountLogout() {
        if (!activeAccountId) return;
        const confirmLogout = confirm("Disconnect and log out of this WhatsApp session?");
        if (!confirmLogout) return;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/logout`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                settingAccountStatus.textContent = "Disconnected";
                showNotificationToast("Disconnected", "Account logged out.", "var(--warning)");
            }
        } catch (err) {
            console.error("Error logging out:", err);
        }
    }

    async function handleDeleteAccount() {
        if (!activeAccountId) return;
        const confirmDelete = confirm("Are you sure you want to permanently delete this account credentials and session?");
        if (!confirmDelete) return;

        try {
            const res = await fetch("/api/accounts/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ account_id: activeAccountId })
            });
            const data = await res.json();
            if (data.success) {
                activeAccountId = "";
                activeContactJid = "";
                hideChatWindow();
                loadAccounts();
            }
        } catch (err) {
            console.error("Error deleting account:", err);
        }
    }

    // --- Safety & Incident Logs ---
    async function loadAuditLogs() {
        if (!activeAccountId) return;
        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/logs?limit=100`);
            const logs = await res.json();
            renderLogsTable(logs);
        } catch (err) {
            console.error("Error loading safety logs:", err);
        }
    }

    function renderLogsTable(logs) {
        if (!logs || logs.length === 0) {
            logsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-secondary">
                        No safety violations or flagged messages recorded. Account is secure!
                    </td>
                </tr>`;
            return;
        }

        logsTableBody.innerHTML = "";
        logs.forEach(log => {
            const tr = document.createElement("tr");
            
            const isAi = log.detection_type && log.detection_type.includes("Gemini");
            const isAntiDelete = log.detection_type && log.detection_type.includes("Anti-Delete");
            let typeBadge = `<span class="badge-type-kw">Keyword</span>`;
            if (isAi) typeBadge = `<span class="badge-type-ai">Gemini AI</span>`;
            else if (isAntiDelete) typeBadge = `<span class="badge-sev-high">Anti-Delete</span>`;

            let sevClass = "badge-sev-medium";
            if (log.severity === "High") sevClass = "badge-sev-high";
            else if (log.severity === "Low") sevClass = "badge-sev-low";
            const sevBadge = `<span class="${sevClass}">${escapeHTML(log.severity || 'Medium')}</span>`;

            const directionClass = log.is_outgoing ? "color: var(--wa-green);" : "color: var(--text-primary);";

            tr.innerHTML = `
                <td style="white-space: nowrap;">${escapeHTML(log.datetime || '')}</td>
                <td style="${directionClass}; font-weight: 500;">${escapeHTML(log.direction || (log.is_outgoing ? 'Outgoing' : 'Incoming'))}</td>
                <td><strong>${escapeHTML(log.sender_name || log.sender || '')}</strong><br><small class="text-secondary">${escapeHTML(log.chat_jid || '')}</small></td>
                <td style="word-break: break-word;">${escapeHTML(log.message || '')}</td>
                <td>${typeBadge}</td>
                <td>${sevBadge}</td>
                <td style="font-size: 12px; color: var(--text-secondary);">${escapeHTML(log.reason || '')}</td>
            `;
            logsTableBody.appendChild(tr);
        });
    }

    async function handleClearLogs() {
        if (!activeAccountId) return;
        if (!confirm("Clear all recorded safety incident logs for this account?")) return;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/logs/clear`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                loadAuditLogs();
                unreadAlertCount = 0;
                alertCounterBadge.style.display = "none";
            }
        } catch (err) {
            console.error("Error clearing logs:", err);
        }
    }

    async function handleExportLogs() {
        if (!activeAccountId) return;
        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/logs?limit=500`);
            const logs = await res.json();
            if (!logs || !logs.length) {
                alert("No logs available to export.");
                return;
            }

            let csv = "Timestamp,Direction,Chat,Sender,Message,Detection Type,Severity,Reason\n";
            logs.forEach(l => {
                const row = [
                    `"${l.datetime || ''}"`,
                    `"${l.direction || (l.is_outgoing ? 'Outgoing' : 'Incoming')}"`,
                    `"${l.chat_jid || ''}"`,
                    `"${(l.sender_name || l.sender || '').replace(/"/g, '""')}"`,
                    `"${(l.message || '').replace(/"/g, '""')}"`,
                    `"${l.detection_type || ''}"`,
                    `"${l.severity || ''}"`,
                    `"${(l.reason || '').replace(/"/g, '""')}"`
                ];
                csv += row.join(",") + "\n";
            });

            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `safety_audit_${activeAccountId}_${Date.now()}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error("Error exporting logs:", err);
        }
    }

    // --- Webhooks Management ---
    async function loadWebhooks() {
        if (!webhooksListContainer) return;
        try {
            const res = await fetch("/api/v1/webhooks");
            const data = await res.json();
            renderWebhooksList(data.webhooks || []);
        } catch (err) {
            console.error("Error loading webhooks:", err);
        }
    }

    function renderWebhooksList(webhooks) {
        if (!webhooksListContainer) return;
        if (!webhooks || !webhooks.length) {
            webhooksListContainer.innerHTML = `<small class="text-secondary">No external webhooks subscribed.</small>`;
            return;
        }

        webhooksListContainer.innerHTML = "";
        webhooks.forEach(wh => {
            const div = document.createElement("div");
            div.className = "webhook-item";
            div.innerHTML = `
                <div>
                    <strong class="font-mono">${escapeHTML(wh.url)}</strong>
                    <br><small class="text-secondary">Events: ${(wh.events || ['all']).join(', ')}</small>
                </div>
                <button class="btn btn-outline" style="font-size: 11px; padding: 3px 8px;">Remove</button>
            `;
            div.querySelector("button").addEventListener("click", () => handleUnsubscribeWebhook(wh.url));
            webhooksListContainer.appendChild(div);
        });
    }

    async function handleRegisterWebhook() {
        const url = webhookUrlInput.value.trim();
        if (!url) return;

        try {
            const res = await fetch("/api/v1/webhooks/subscribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url, events: ["all"] })
            });
            const data = await res.json();
            if (data.success) {
                webhookUrlInput.value = "";
                loadWebhooks();
                showNotificationToast("Webhook Subscribed", url, "var(--wa-green)");
            }
        } catch (e) {
            console.error("Error registering webhook:", e);
        }
    }

    async function handleUnsubscribeWebhook(url) {
        try {
            const res = await fetch("/api/v1/webhooks/unsubscribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();
            if (data.success) {
                loadWebhooks();
            }
        } catch (e) {
            console.error("Error removing webhook:", e);
        }
    }

    function updateApiAccountLabels() {
        document.querySelectorAll(".api-active-acc").forEach(el => {
            el.textContent = activeAccountId || "acc_xxxxxxxx";
        });
    }

    // --- Realtime Security Alert Notification ---
    function handleSecurityAlertNotification(accountId, incident) {
        unreadAlertCount++;
        alertCounterBadge.textContent = unreadAlertCount;
        alertCounterBadge.style.display = "flex";

        showSecurityAlertToast(incident);

        if (accountId === activeAccountId && settingsModal.style.display === "flex") {
            loadAuditLogs();
        }
    }

    function showSecurityAlertToast(incident) {
        const toast = document.createElement("div");
        toast.className = "security-toast";
        
        toast.innerHTML = `
            <div class="security-toast-header">
                <span class="security-toast-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 6h2v6h-2V7zm0 8h2v2h-2v-2z"/></svg>
                    ${escapeHTML(incident.detection_type || 'Safety Alert')}
                </span>
                <button class="modal-close" style="font-size: 16px;">&times;</button>
            </div>
            <div class="security-toast-body">
                "${escapeHTML((incident.message || '').substring(0, 80))}"
            </div>
            <div class="security-toast-reason">
                ${escapeHTML(incident.reason || '')}
            </div>
        `;

        const closeBtn = toast.querySelector(".modal-close");
        closeBtn.addEventListener("click", () => toast.remove());

        toast.addEventListener("click", (e) => {
            if (e.target !== closeBtn) {
                openSettingsModal("tab-logs");
                toast.remove();
            }
        });

        toastContainer.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 7000);
    }

    function showNotificationToast(title, body, color) {
        const toast = document.createElement("div");
        toast.className = "security-toast";
        toast.style.borderColor = color || "var(--wa-green)";
        toast.innerHTML = `
            <div class="security-toast-header">
                <span class="security-toast-title" style="color: ${color || 'var(--wa-green)'}">${escapeHTML(title)}</span>
            </div>
            <div class="security-toast-body">${escapeHTML(body)}</div>
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 3500);
    }

    // --- Gemini Test Handler ---
    async function handleTestGemini() {
        const text = testGeminiInput.value.trim();
        if (!text) return;

        testGeminiResult.style.display = "block";
        testGeminiResult.innerHTML = "<em>Analyzing message with Gemini AI Guardian...</em>";

        const apiKey = settingGeminiKey.value.trim();

        try {
            const kwList = settingKeywordsList.value.split(',').map(s => s.trim().toLowerCase());
            const textLower = text.toLowerCase();
            const matchedKw = kwList.filter(k => k && textLower.includes(k));

            if (matchedKw.length > 0) {
                testGeminiResult.innerHTML = `
                    <strong style="color: var(--warning);">Keyword Match:</strong> Matched sensitive keyword(s): <code>${matchedKw.join(', ')}</code>.
                    <br><small>This message would trigger an instant Parental Safety Log.</small>
                `;
            } else if (apiKey) {
                const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
                const prompt = `Analyze if this message contains illegal acts, violence, drugs, harassment, or adult content: "${text}". Reply with JSON {"flagged": true/false, "reason": "short explanation"}`;
                const resp = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
                });
                const resData = await resp.json();
                const aiRaw = resData.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
                testGeminiResult.innerHTML = `<strong style="color: var(--wa-green);">Gemini AI Result:</strong> <pre style="font-size: 11.5px; margin-top: 4px;">${escapeHTML(aiRaw)}</pre>`;
            } else {
                testGeminiResult.innerHTML = `
                    <strong style="color: var(--wa-green);">Safety Check Passed:</strong> No keyword violations detected.
                    <br><small>Tip: Enter your Google Gemini API key above to enable deep AI semantic analysis.</small>
                `;
            }
        } catch (e) {
            testGeminiResult.innerHTML = `<span style="color: var(--danger);">Test Error: ${escapeHTML(e.message)}</span>`;
        }
    }

    // --- Modal Management ---
    function openSettingsModal(activeTabId = "tab-theme") {
        if (!activeAccountId) return;
        settingsModal.style.display = "flex";
        switchSettingsTab(activeTabId);
        loadAccountSettings();
        if (activeTabId === "tab-logs") {
            loadAuditLogs();
            unreadAlertCount = 0;
            alertCounterBadge.style.display = "none";
        }
    }

    function closeSettingsModal() {
        settingsModal.style.display = "none";
    }

    function switchSettingsTab(tabId) {
        document.querySelectorAll(".modal-tabs .tab-btn").forEach(btn => {
            btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
        });
        document.querySelectorAll(".modal-tabs-content .tab-pane").forEach(pane => {
            pane.classList.toggle("active", pane.id === tabId);
        });
        if (tabId === "tab-logs") {
            loadAuditLogs();
        } else if (tabId === "tab-api") {
            loadWebhooks();
            updateApiAccountLabels();
        }
    }

    async function openAddAccountModal() {
        addAccountModal.style.display = "flex";
        qrLoading.style.display = "flex";
        qrImage.style.display = "none";
        qrStatusDot.className = "status-dot warning";
        qrStatusText.innerText = "Status: Initializing session...";
        qrSessionId = "";

        try {
            const res = await fetch("/api/accounts/add", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                qrSessionId = data.account_id;
            } else {
                qrStatusDot.className = "status-dot danger";
                qrStatusText.innerText = "Error: Failed to request session.";
            }
        } catch (err) {
            console.error("Failed to add account:", err);
            qrStatusDot.className = "status-dot danger";
            qrStatusText.innerText = "Error: Network failure.";
        }
    }

    function openAddAccountModalDirect(qrBase64) {
        addAccountModal.style.display = "flex";
        if (qrBase64) {
            qrLoading.style.display = "none";
            qrImage.src = `data:image/png;base64,${qrBase64}`;
            qrImage.style.display = "block";
            qrStatusDot.className = "status-dot warning";
            qrStatusText.innerText = "Status: Scan session ready.";
        } else {
            qrLoading.style.display = "flex";
            qrImage.style.display = "none";
            qrStatusDot.className = "status-dot warning";
            qrStatusText.innerText = "Status: Generating session...";
        }
    }

    function closeAddAccountModal() {
        addAccountModal.style.display = "none";
        qrSessionId = "";
    }

    // --- Contacts & Chats Logic ---
    async function loadContacts() {
        if (!activeAccountId) return;
        const activeAcc = accounts.find(a => a.id === activeAccountId);
        if (!activeAcc || activeAcc.status !== "Connected") return;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/contacts`);
            contacts = await res.json();
            applyFiltersAndRender();
        } catch (err) {
            console.error("Error fetching contacts:", err);
        }
    }

    function applyFiltersAndRender() {
        let filtered = contacts;
        
        // Tab Filter: all, chats, groups
        if (activeFilter === "chats") {
            filtered = contacts.filter(c => !c.is_group);
        } else if (activeFilter === "groups") {
            filtered = contacts.filter(c => c.is_group);
        }

        // Search Filter
        const query = chatSearch.value.toLowerCase().trim();
        if (query) {
            filtered = filtered.filter(c => {
                const name = (c.name || "").toLowerCase();
                const jid = (c.jid || "").toLowerCase();
                return name.includes(query) || jid.includes(query);
            });
        }

        renderContacts(filtered);
    }

    function renderContacts(contactsListToRender) {
        contactsList.innerHTML = "";
        
        if (contactsListToRender.length === 0) {
            contactsList.innerHTML = `
                <div class="list-empty">
                    <p>No conversations found.</p>
                    <p class="secondary-text">Type a phone number in search box and press Enter to start chatting.</p>
                </div>`;
            return;
        }

        contactsListToRender.forEach(c => {
            const item = document.createElement("div");
            item.className = `contact-item ${c.jid === activeContactJid ? 'active' : ''}`;
            
            const initials = c.name ? c.name.substring(0, 2).toUpperCase() : "WA";
            const avatarClass = c.is_group ? "contact-avatar group-avatar" : "contact-avatar";

            let timeStr = "";
            if (c.timestamp && c.timestamp > 0) {
                timeStr = formatChatTimestamp(c.timestamp);
            }

            // Preview snippet icon formatting
            let previewText = c.last_message || 'Start chatting...';
            let previewClass = "preview-text";
            if (previewText.includes("🚫")) {
                previewClass += " preview-deleted";
            }

            item.innerHTML = `
                <div class="${avatarClass}">${initials}</div>
                <div class="contact-info">
                    <div class="contact-info-row">
                        <span class="contact-name">${escapeHTML(c.name || c.jid.split('@')[0])}</span>
                        <span class="contact-time">${timeStr}</span>
                    </div>
                    <div class="contact-preview">
                        ${c.is_group ? '<span class="tag-badge">Group</span>' : ''}
                        <span class="${previewClass}">${escapeHTML(previewText)}</span>
                    </div>
                </div>
            `;

            item.addEventListener("click", () => handleSelectContact(c));
            contactsList.appendChild(item);
        });
    }

    function handleSelectContact(contact) {
        activeContactJid = contact.jid;
        
        document.querySelectorAll(".contact-item").forEach(item => {
            item.classList.remove("active");
        });
        
        applyFiltersAndRender();

        chatContactName.innerText = contact.name || contact.jid.split('@')[0];
        chatContactJid.innerText = contact.is_group ? contact.jid : formatDisplayJid(contact.jid);
        
        const initials = contact.name ? contact.name.substring(0, 2).toUpperCase() : "WA";
        chatAvatar.innerText = initials;
        chatAvatar.className = contact.is_group ? "avatar group-avatar" : "avatar";

        emptyState.style.display = "none";
        chatWindow.style.display = "flex";

        loadMessages();
    }

    function hideChatWindow() {
        chatWindow.style.display = "none";
        emptyState.style.display = "flex";
    }

    async function loadMessages() {
        if (!activeAccountId || !activeContactJid) return;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/messages?contact=${encodeURIComponent(activeContactJid)}`);
            const messages = await res.json();
            
            messagePanel.innerHTML = "";
            messages.forEach(msg => {
                appendMessageBubble(msg);
            });
            scrollToBottom();
        } catch (err) {
            console.error("Error loading messages:", err);
        }
    }

    // ========================================================
    // MESSAGE BUBBLE RENDERING: AUDIO, IMAGE, ANTI-DELETE
    // ========================================================
    function appendMessageBubble(msg) {
        const bubble = document.createElement("div");
        const isOut = Boolean(msg.is_outgoing);
        const isDeleted = Boolean(msg.is_deleted);
        
        bubble.className = `message ${isOut ? 'message-out' : 'message-in'} ${isDeleted ? 'is-deleted-msg' : ''}`;
        bubble.setAttribute("data-msg-id", msg.id || "");

        const contact = contacts.find(c => c.jid === activeContactJid) || {};
        const isGroup = contact.is_group || (activeContactJid && activeContactJid.endsWith("@g.us"));
        
        // In group chats, display participant name for incoming messages
        let headerLabel = "";
        if (!isOut && isGroup) {
            const displayName = msg.sender_name || (msg.sender ? msg.sender.split('@')[0] : 'Member');
            headerLabel = `<span class="message-group-sender">${escapeHTML(displayName)}</span>`;
        }

        // Anti-delete safeguard banner (Preserves deleted message for parental audit!)
        let deletedBanner = "";
        if (isDeleted) {
            deletedBanner = `
                <div class="deleted-banner">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/></svg>
                    Deleted by sender (Anti-Delete Preserved)
                </div>`;
        }

        const timeStr = formatTime(msg.timestamp);

        // Double checkmarks for outgoing messages
        const ticksSvg = isOut 
            ? `<span class="message-status">
                <svg viewBox="0 0 16 11" width="15" height="10" class="svg-icon inline-icon">
                    <path fill="currentColor" d="M15 1.2l-8.5 8.5-3.5-3.5 1.2-1.2 2.3 2.3 7.3-7.3 1.2 1.2zm-4.7 0l-7.3 7.3-3.1-3.1 1.2-1.2 1.9 1.9 6.1-6.1 1.2 1.2z"></path>
                </svg>
               </span>`
            : '';

        const attachmentHtml = renderAttachmentHtml(msg.attachment);
        const textClass = isDeleted ? "message-text deleted-text" : "message-text";

        bubble.innerHTML = `
            ${headerLabel}
            ${deletedBanner}
            ${msg.body ? `<div class="${textClass}">${escapeHTML(msg.body)}</div>` : ''}
            ${attachmentHtml}
            <span class="message-time">
                ${timeStr}
                ${ticksSvg}
            </span>
        `;

        messagePanel.appendChild(bubble);
    }

    function renderAttachmentHtml(attachment) {
        if (!attachment) return '';

        const type = attachment.type || 'attachment';
        const mediaUrl = attachment.local_url || attachment.url || '';
        const preview = attachment.preview || '';
        const caption = attachment.caption ? `<div class="attachment-caption">${escapeHTML(attachment.caption)}</div>` : '';

        // 1. Audio / Voice Note Player
        if (type === 'audio') {
            return `
                <div class="media-container audio-media">
                    <audio controls preload="metadata" src="${escapeHTML(mediaUrl)}">
                        Your browser does not support audio element.
                    </audio>
                    <div class="audio-info">
                        <span>🎵 Voice message</span>
                        <span>${formatDuration(attachment.duration)}</span>
                    </div>
                    ${caption}
                </div>
            `;
        }

        // 2. Image / Photo
        if (type === 'image') {
            const displaySrc = mediaUrl || preview;
            return `
                <div class="media-container image-media">
                    <img src="${escapeHTML(displaySrc)}" class="chat-photo" loading="lazy" alt="WhatsApp Photo" onclick="window.open(this.src, '_blank')">
                    ${caption}
                </div>
            `;
        }

        // 3. Video Player
        if (type === 'video') {
            return `
                <div class="media-container video-media">
                    <video controls preload="metadata" src="${escapeHTML(mediaUrl)}"></video>
                    ${caption}
                </div>
            `;
        }

        // 4. Document / File
        if (type === 'document') {
            const fileName = attachment.file_name || 'Document';
            return `
                <div class="media-container document-media">
                    <span class="doc-icon">📄</span>
                    <div class="doc-info">
                        <span class="doc-name">${escapeHTML(fileName)}</span>
                        ${mediaUrl ? `<a href="${escapeHTML(mediaUrl)}" download="${escapeHTML(fileName)}" class="btn-download-doc">Download File</a>` : ''}
                    </div>
                </div>
                ${caption}
            `;
        }

        // 5. Sticker
        if (type === 'sticker' && (mediaUrl || preview)) {
            return `
                <div class="media-container" style="max-width: 140px;">
                    <img src="${escapeHTML(mediaUrl || preview)}" style="width: 100%; border-radius: 6px;" alt="Sticker">
                </div>
            `;
        }

        return '';
    }

    // Handle Live Anti-Delete SSE Event
    function handleMessageRevokedUI(chatJid, targetId, message) {
        // Find existing bubble by data-msg-id
        const bubble = document.querySelector(`.message[data-msg-id="${targetId}"]`);
        if (bubble) {
            bubble.classList.add("is-deleted-msg");
            if (!bubble.querySelector(".deleted-banner")) {
                const banner = document.createElement("div");
                banner.className = "deleted-banner";
                banner.innerHTML = `<svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8 0-1.85.63-3.55 1.69-4.9L16.9 18.31C15.55 19.37 13.85 20 12 20zm6.31-3.1L7.1 5.69C8.45 4.63 10.15 4 12 4c4.42 0 8 3.58 8 8 0 1.85-.63 3.55-1.69 4.9z"/></svg> Deleted by sender (Anti-Delete Preserved)`;
                bubble.insertBefore(banner, bubble.firstChild);
            }
            const textEl = bubble.querySelector(".message-text");
            if (textEl) textEl.className = "message-text deleted-text";
        }

        // Update contacts snippet
        updateContactLastMessage(chatJid, {
            body: "🚫 This message was deleted",
            timestamp: Math.floor(Date.now() / 1000)
        });
    }

    // Handle Live Media Downloaded SSE Event
    function handleMediaReadyUI(msgId, localUrl, mediaType) {
        const bubble = document.querySelector(`.message[data-msg-id="${msgId}"]`);
        if (bubble) {
            if (mediaType === 'image') {
                const img = bubble.querySelector(".chat-photo");
                if (img) img.src = localUrl;
            } else if (mediaType === 'audio') {
                const audio = bubble.querySelector("audio");
                if (audio) audio.src = localUrl;
            }
        }
    }

    function formatDuration(seconds) {
        if (seconds == null || isNaN(seconds)) return '';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function updateContactLastMessage(chatJid, msg) {
        let contact = contacts.find(c => c.jid === chatJid);
        
        let snippet = msg.body || '';
        if (msg.is_deleted) {
            snippet = "🚫 This message was deleted";
        } else if (msg.attachment) {
            const icons = { image: "📷 Photo", audio: "🎵 Voice note", video: "🎥 Video", document: "📄 Document" };
            snippet = icons[msg.attachment.type] || `[${msg.attachment.type}]`;
        }

        if (!contact) {
            const isGroup = chatJid.endsWith("@g.us");
            contact = {
                jid: chatJid,
                name: msg.is_outgoing ? chatJid.split('@')[0] : (msg.sender_name || chatJid.split('@')[0]),
                is_group: isGroup,
                timestamp: msg.timestamp || Math.floor(Date.now() / 1000),
                last_message: snippet
            };
            contacts.unshift(contact);
        } else {
            contact.last_message = snippet;
            contact.timestamp = msg.timestamp || Math.floor(Date.now() / 1000);
            if (!msg.is_outgoing && !contact.is_group && msg.sender_name) {
                contact.name = msg.sender_name;
            }
        }
        
        contacts.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
        applyFiltersAndRender();
    }

    // --- Search & New Chats ---
    function handleSearch(e) {
        applyFiltersAndRender();
    }

    function handleNewChatSearchEnter(e) {
        if (e.key === "Enter") {
            const val = e.target.value.trim();
            if (!val) return;

            const phonePattern = /^\+?[0-9]{8,15}$/;
            if (phonePattern.test(val)) {
                let cleanPhone = val.replace("+", "").replace(/\s/g, "");
                const jid = `${cleanPhone}@s.whatsapp.net`;
                
                let contact = contacts.find(c => c.jid === jid);
                if (!contact) {
                    contact = {
                        jid: jid,
                        name: `+${cleanPhone}`,
                        is_group: false,
                        timestamp: Math.floor(Date.now() / 1000),
                        last_message: ""
                    };
                    contacts.unshift(contact);
                }
                
                chatSearch.value = "";
                applyFiltersAndRender();
                handleSelectContact(contact);
            }
        }
    }

    // --- Sending Messages ---
    async function handleSendMessage(e) {
        e.preventDefault();
        if (!activeAccountId || !activeContactJid) return;

        const text = messageInput.value.trim();
        if (!text) return;

        messageInput.value = "";
        
        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    target: activeContactJid,
                    message: text
                })
            });
            const data = await res.json();
            if (!data.success) {
                alert("Failed to send message. Account may be disconnected.");
            }
        } catch (err) {
            console.error("Error sending message:", err);
            alert("Network error sending message.");
        }
    }

    // --- Utilities ---
    function scrollToBottom() {
        messagePanel.scrollTop = messagePanel.scrollHeight;
    }

    function formatTime(timestamp) {
        if (!timestamp) return "";
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function formatChatTimestamp(timestamp) {
        if (!timestamp) return "";
        const date = new Date(timestamp * 1000);
        const now = new Date();

        // Check if today
        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        // Check if yesterday
        const yesterday = new Date(now);
        yesterday.setDate(now.getDate() - 1);
        if (date.toDateString() === yesterday.toDateString()) {
            return "Yesterday";
        }

        // Older: show date
        return date.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
    }

    function formatDisplayJid(jid) {
        if (!jid) return "";
        if (jid.endsWith("@g.us")) return jid;
        return jid.split("@")[0] || jid;
    }

    function escapeHTML(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
