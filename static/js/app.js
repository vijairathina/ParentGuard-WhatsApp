// ParentGuard WhatsApp - Client Application & Safety Guardian
document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let accounts = [];
    let activeAccountId = "";
    let activeContactJid = "";
    let contacts = [];
    let activeFilter = "all"; // "all", "chats", "groups"
    let activePlatform = "all"; // "all", "whatsapp", "telegram", "instagram"
    let tgCurrentAccountId = "";
    let igCurrentAccountId = "";
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
    const accountStatusIndicator = document.getElementById("account-status-indicator");

    // In-Window QR Pane & Banner Elements (Right side of window)
    const qrPane = document.getElementById("qr-pane");
    const qrPaneLoading = document.getElementById("qr-pane-loading");
    const qrPaneImage = document.getElementById("qr-pane-image");
    const qrPaneStatusDot = document.getElementById("qr-pane-status-dot");
    const qrPaneStatusText = document.getElementById("qr-pane-status-text");
    const btnRefreshQrPane = document.getElementById("btn-refresh-qr-pane");
    const sessionNoticeBanner = document.getElementById("session-notice-banner");
    const btnBannerReconnect = document.getElementById("btn-banner-reconnect");

    // Photo Lightbox Modal Elements
    const photoLightboxModal = document.getElementById("photo-lightbox-modal");
    const lightboxBackdrop = document.getElementById("lightbox-backdrop");
    const btnLightboxClose = document.getElementById("btn-lightbox-close");
    const lightboxImage = document.getElementById("lightbox-image");
    const lightboxCaption = document.getElementById("lightbox-caption");

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
    const btnSettingsDeleteAccount = document.getElementById("btn-settings-delete-account");

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

    // Scheduled Messages Elements
    const btnOpenSchedules = document.getElementById("btn-open-schedules");
    const schedulesCounterBadge = document.getElementById("schedules-counter-badge");
    const btnChatSchedule = document.getElementById("btn-chat-schedule");
    const schedulesModal = document.getElementById("schedules-modal");
    const btnCloseSchedules = document.getElementById("btn-close-schedules");
    const btnCancelCreateSched = document.getElementById("btn-cancel-create-sched");
    const btnTopCreateSched = document.getElementById("btn-top-create-sched");
    const btnTabCreateSchedule = document.getElementById("btn-tab-create-schedule");
    const schedulesCardsContainer = document.getElementById("schedules-cards-container");
    const formSchedule = document.getElementById("form-schedule");
    const btnSaveSchedule = document.getElementById("btn-save-schedule");
    const schedEditId = document.getElementById("sched-edit-id");
    const schedTitle = document.getElementById("sched-title");
    const schedCategory = document.getElementById("sched-category");
    const schedRecipientSelect = document.getElementById("sched-recipient-select");
    const schedCustomTarget = document.getElementById("sched-custom-target");
    const schedAnnualMonth = document.getElementById("sched-annual-month");
    const schedAnnualDay = document.getElementById("sched-annual-day");
    const schedDatetimePicker = document.getElementById("sched-datetime-picker");
    const schedTimePicker = document.getElementById("sched-time-picker");
    const groupAnnualDate = document.getElementById("group-annual-date");
    const groupOnceDatetime = document.getElementById("group-once-datetime");
    const groupTimeOfDay = document.getElementById("group-time-of-day");
    const groupWeeklyDays = document.getElementById("group-weekly-days");
    const schedMessageText = document.getElementById("sched-message-text");
    const schedLivePreview = document.getElementById("sched-live-preview");
    const schedEnabled = document.getElementById("sched-enabled");
    const templatesLibraryGrid = document.getElementById("templates-library-grid");
    const btnInsertName = document.getElementById("btn-insert-name");
    const btnInsertDate = document.getElementById("btn-insert-date");
    const btnInsertTime = document.getElementById("btn-insert-time");
    const btnInsertDay = document.getElementById("btn-insert-day");

    // Curated default template fallbacks (ensures instantaneous rendering even before API returns)
    const DEFAULT_TEMPLATES = {
        birthday: {
            title: "🎂 Birthday Wishes",
            category: "birthday",
            default_type: "annual",
            default_time: "09:00",
            templates: [
                {
                    id: "bday_1",
                    name: "Warm & Joyful Celebration",
                    text: "🎂 Happy Birthday, {name}! 🎉 Wishing you a magnificent year filled with boundless happiness, radiant health, and outstanding achievements! Have a wonderful celebration! 🎈✨"
                },
                {
                    id: "bday_2",
                    name: "Blessing & Endless Success",
                    text: "Happy Birthday {name}! 🌟 May your special day bring countless reasons to smile and may the year ahead be your most successful and fulfilling one yet! 🎁🎂"
                }
            ]
        },
        anniversary: {
            title: "💍 Wedding Anniversary",
            category: "anniversary",
            default_type: "annual",
            default_time: "10:00",
            templates: [
                {
                    id: "anni_1",
                    name: "Golden Milestone of Love",
                    text: "💍 Happy Wedding Anniversary, {name}! Wishing you both a lifetime of enduring love, deepest joy, and wonderful adventures together! Cheers to your beautiful journey! 🥂❤️"
                }
            ]
        },
        morning: {
            title: "🌅 Good Morning Greetings",
            category: "morning",
            default_type: "daily",
            default_time: "08:00",
            templates: [
                {
                    id: "morn_1",
                    name: "Sunny & Productive Morning",
                    text: "🌅 Good morning, {name}! Rise and shine! May your day be filled with positive energy, sharp focus, and pleasant surprises! ☀️💪"
                }
            ]
        },
        afternoon: {
            title: "☀️ Afternoon Check-in",
            category: "afternoon",
            default_type: "daily",
            default_time: "13:30",
            templates: [
                {
                    id: "aft_1",
                    name: "Lunch & Refresh Check-in",
                    text: "☀️ Good afternoon, {name}! Hope your day is going smoothly. Remember to take a nourishing lunch break, stay hydrated, and keep up the great momentum! 🥗🥪"
                }
            ]
        },
        night: {
            title: "🌙 Good Night Greetings",
            category: "night",
            default_type: "daily",
            default_time: "21:30",
            templates: [
                {
                    id: "night_1",
                    name: "Peaceful Rest & Sweet Dreams",
                    text: "🌙 Good night, {name}! Let go of today's worries and rest well. Wishing you deep, restorative sleep and sweet dreams! See you tomorrow! 😴⭐"
                }
            ]
        },
        festival: {
            title: "🪔 Festivals & Holidays",
            category: "festival",
            default_type: "annual",
            default_time: "08:30",
            templates: [
                {
                    id: "fest_diwali",
                    name: "Diwali / Deepavali Wishes",
                    text: "🪔 Happy Diwali, {name}! May the divine festival of lights illuminate your life with joy, good health, peace, and prosperous abundance! Wishing you and your family a safe and glittering Deepavali! 🎆✨"
                },
                {
                    id: "fest_newyear",
                    name: "New Year Celebration",
                    text: "🎆 Happy New Year, {name}! May the year bring endless opportunities, good fortune, peace, and prosperity to you and your loved ones! 🥂🎉"
                }
            ]
        },
        reminder: {
            title: "💧 Routine & Wellness",
            category: "reminder",
            default_type: "daily",
            default_time: "11:00",
            templates: [
                {
                    id: "rem_water",
                    name: "Hydration & Posture Reminder",
                    text: "💧 Quick wellness check-in, {name}! Remember to drink a tall glass of water, stretch your back, and rest your eyes for a moment. Take care! 🌿"
                }
            ]
        }
    };

    let schedules = [];
    let sampleTemplates = Object.assign({}, DEFAULT_TEMPLATES);
    let activeSchedFilter = "all";

    // Initialize App
    init();

    async function init() {
        // Event Listeners (Registered immediately & synchronously)
        dropdown.addEventListener("change", handleAccountSwitch);
        btnAddAccount.addEventListener("click", openAddAccountModal);
        btnEmptyAddAccount.addEventListener("click", openAddAccountModal);
        btnDeleteAccount.addEventListener("click", handleDeleteAccount);
        btnCloseModal.addEventListener("click", closeAddAccountModal);
        chatSearch.addEventListener("input", handleSearch);
        chatSearch.addEventListener("keydown", handleNewChatSearchEnter);
        messageForm.addEventListener("submit", handleSendMessage);

        // Multi-Platform Navigation Dock Listeners
        document.querySelectorAll(".platform-tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".platform-tab-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activePlatform = btn.getAttribute("data-platform") || "all";
                hideQrPane(); // Never show WhatsApp QR pane when navigating to another platform!
                renderAccountsDropdown();
                const available = getFilteredAccounts();
                if (available.length > 0 && !available.some(a => a.id === activeAccountId)) {
                    activeAccountId = available[0].id;
                    dropdown.value = activeAccountId;
                    handleAccountSelectionChange();
                } else if (available.length === 0) {
                    activeAccountId = "";
                    dropdown.value = "";
                    contactsList.innerHTML = `<div class="list-empty"><p>No ${activePlatform.toUpperCase()} accounts configured.</p><button type="button" class="btn btn-primary btn-sm mt-3" id="btn-empty-plat-add">+ Add ${activePlatform.toUpperCase()} Account</button></div>`;
                    const emptyBtn = document.getElementById("btn-empty-plat-add");
                    if (emptyBtn) emptyBtn.addEventListener("click", () => openAddAccountModalForPlatform(activePlatform));
                    hideChatWindow();
                } else {
                    handleAccountSelectionChange();
                }
            });
        });

        // Add Account Platform Tab Switching
        document.querySelectorAll("#add-account-platform-tabs .tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#add-account-platform-tabs .tab-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const targetTabId = btn.getAttribute("data-platform-tab");
                document.querySelectorAll("#add-account-modal .tab-pane").forEach(pane => {
                    pane.style.display = "none";
                    pane.classList.remove("active");
                });
                const targetPane = document.getElementById(targetTabId);
                if (targetPane) {
                    targetPane.style.display = "block";
                    targetPane.classList.add("active");
                }
                if (targetTabId === "tab-add-whatsapp" && !qrSessionId) {
                    requestWhatsAppQrSession();
                }
            });
        });

        // Telegram OTP Login Handlers
        const btnTgSendOtp = document.getElementById("btn-tg-send-otp");
        const btnTgChangePhone = document.getElementById("btn-tg-change-phone");
        const btnTgVerifyOtp = document.getElementById("btn-tg-verify-otp");
        const btnTgResendSms = document.getElementById("btn-tg-resend-sms");

        if (btnTgSendOtp) btnTgSendOtp.addEventListener("click", handleTelegramSendOtp);
        if (btnTgChangePhone) btnTgChangePhone.addEventListener("click", () => {
            document.getElementById("tg-step-phone").style.display = "block";
            document.getElementById("tg-step-otp").style.display = "none";
            document.getElementById("tg-status-feedback").style.display = "none";
        });
        if (btnTgVerifyOtp) btnTgVerifyOtp.addEventListener("click", handleTelegramVerifyOtp);
        if (btnTgResendSms) btnTgResendSms.addEventListener("click", handleTelegramResendSms);

        // Instagram Login Handlers
        const btnIgLogin = document.getElementById("btn-ig-login");
        const btnIgVerify2Fa = document.getElementById("btn-ig-verify-2fa");

        if (btnIgLogin) btnIgLogin.addEventListener("click", handleInstagramLogin);
        if (btnIgVerify2Fa) btnIgVerify2Fa.addEventListener("click", handleInstagramVerify2Fa);

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
        if (btnSettingsDeleteAccount) {
            btnSettingsDeleteAccount.addEventListener("click", handleDeleteAccount);
        }

        btnRefreshLogs.addEventListener("click", loadAuditLogs);
        btnClearLogs.addEventListener("click", handleClearLogs);
        btnExportLogs.addEventListener("click", handleExportLogs);

        // Webhook Button
        if (btnRegisterWebhook) {
            btnRegisterWebhook.addEventListener("click", handleRegisterWebhook);
        }

        // Settings Modal Tab Navigation (scoped strictly to settings modal)
        document.querySelectorAll("#settings-modal .modal-tabs .tab-btn").forEach(btn => {
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

        // QR Pane & Reconnect Listeners
        if (btnRefreshQrPane) {
            btnRefreshQrPane.addEventListener("click", () => {
                showQrPane(true);
            });
        }
        if (btnBannerReconnect) {
            btnBannerReconnect.addEventListener("click", () => {
                const acc = accounts.find(a => a.id === activeAccountId);
                const platform = getAccountPlatform(acc);
                if (platform === "whatsapp") {
                    showQrPane(true);
                } else if (platform === "telegram") {
                    openAddAccountModalForPlatform("telegram");
                } else if (platform === "instagram") {
                    openAddAccountModalForPlatform("instagram");
                }
            });
        }
        if (accountStatusIndicator) {
            accountStatusIndicator.addEventListener("click", () => {
                const acc = accounts.find(a => a.id === activeAccountId);
                if (acc && acc.status !== "Connected") {
                    const platform = getAccountPlatform(acc);
                    if (platform === "whatsapp") {
                        showQrPane(true);
                    } else if (platform === "telegram") {
                        openAddAccountModalForPlatform("telegram");
                    } else if (platform === "instagram") {
                        openAddAccountModalForPlatform("instagram");
                    }
                }
            });
        }

        // Photo Lightbox Modal Listeners
        if (btnLightboxClose) {
            btnLightboxClose.addEventListener("click", closePhotoLightbox);
        }
        if (lightboxBackdrop) {
            lightboxBackdrop.addEventListener("click", closePhotoLightbox);
        }
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && photoLightboxModal && photoLightboxModal.style.display !== "none") {
                closePhotoLightbox();
            }
        });

        // Scheduled Messages Listeners
        if (btnOpenSchedules) {
            btnOpenSchedules.addEventListener("click", () => openSchedulesModal("tab-schedules-list"));
        }
        if (btnCloseSchedules) {
            btnCloseSchedules.addEventListener("click", closeSchedulesModal);
        }
        if (btnCancelCreateSched) {
            btnCancelCreateSched.addEventListener("click", () => switchSchedulesTab("tab-schedules-list"));
        }
        if (btnTopCreateSched) {
            btnTopCreateSched.addEventListener("click", () => openCreateScheduleTab());
        }
        if (btnTabCreateSchedule) {
            btnTabCreateSchedule.addEventListener("click", () => openCreateScheduleTab());
        }
        if (btnChatSchedule) {
            btnChatSchedule.addEventListener("click", handleChatScheduleClick);
        }
        if (formSchedule) {
            formSchedule.addEventListener("submit", handleSaveSchedule);
        }
        if (btnSaveSchedule) {
            btnSaveSchedule.addEventListener("click", handleSaveSchedule);
        }

        // Schedule Modal Tab Navigation
        document.querySelectorAll("#schedules-modal .sched-tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                if (targetTab === "tab-schedules-create" && !schedEditId.value) {
                    openCreateScheduleTab();
                } else {
                    switchSchedulesTab(targetTab);
                }
            });
        });

        // Recurrence radio buttons change
        document.querySelectorAll("input[name='sched-type']").forEach(radio => {
            radio.addEventListener("change", handleScheduleTypeChange);
        });

        // Variable insertion helpers
        if (btnInsertName) btnInsertName.addEventListener("click", () => insertScheduleVariable("{name}"));
        if (btnInsertDate) btnInsertDate.addEventListener("click", () => insertScheduleVariable("{date}"));
        if (btnInsertTime) btnInsertTime.addEventListener("click", () => insertScheduleVariable("{time}"));
        if (btnInsertDay) btnInsertDay.addEventListener("click", () => insertScheduleVariable("{day}"));

        if (schedMessageText) {
            schedMessageText.addEventListener("input", updateScheduleLivePreview);
        }
        if (schedRecipientSelect) {
            schedRecipientSelect.addEventListener("change", updateScheduleLivePreview);
        }
        if (schedCustomTarget) {
            schedCustomTarget.addEventListener("input", updateScheduleLivePreview);
        }

        // Category filter pills in schedules modal
        document.querySelectorAll(".sched-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                document.querySelectorAll(".sched-pill").forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activeSchedFilter = pill.getAttribute("data-cat") || "all";
                renderSchedulesList();
            });
        });

        // Quick template chips
        document.querySelectorAll(".template-quick-chips .chip-btn").forEach(chip => {
            chip.addEventListener("click", () => {
                const tplCat = chip.getAttribute("data-tpl");
                loadCategoryTemplateIntoForm(tplCat);
            });
        });

        // Category select change
        if (schedCategory) {
            schedCategory.addEventListener("change", (e) => {
                loadCategoryTemplateIntoForm(e.target.value);
            });
        }

        // Initial Background Data Synchronization
        setupSSE();
        loadAccounts();
        loadSchedules();
        loadSampleTemplates();
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

                // Handle Scheduled Message Sent Event
                if (type === "scheduled_message_sent") {
                    showSecurityToast(`⏰ Automated Schedule Sent: ${escapeHTML(data.title)}`, "info");
                    loadSchedules();
                }

                // Handle QR Event
                if (type === "qr") {
                    if (account_id === activeAccountId) {
                        const acc = accounts.find(a => a.id === account_id);
                        if (acc) acc.qr = data.qr;
                        qrPaneLoading.style.display = "none";
                        qrPaneImage.src = `data:image/png;base64,${data.qr}`;
                        qrPaneImage.style.display = "block";
                        qrPaneStatusDot.className = "status-dot warning";
                        qrPaneStatusText.innerText = "Scan QR with WhatsApp on Phone";
                    }
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
                            hideQrPane();
                            if (sessionNoticeBanner) sessionNoticeBanner.style.display = "none";
                            loadContacts();
                        } else if (data.status === "Logged Out" || data.status === "Disconnected") {
                            if (activeContactJid) {
                                if (sessionNoticeBanner) sessionNoticeBanner.style.display = "flex";
                            } else {
                                showQrPane(false);
                            }
                        }
                    }
                }

                // Handle Message Event
                else if (type === "message") {
                    const { chat_jid, alt_jid, message } = data;
                    if (account_id === activeAccountId) {
                        updateContactLastMessage(chat_jid, message, alt_jid);
                    }

                    const sameChat = isMatchingChat(chat_jid, activeContactJid, alt_jid);
                    if (sameChat && account_id === activeAccountId) {
                        // Check if bubble with this message ID was already appended optimistically
                        const existing = document.querySelector(`.message[data-msg-id="${message.id}"]`);
                        if (!existing) {
                            // If empty state placeholder is showing, clear it first
                            const placeholder = messagePanel.querySelector(".empty-chat-placeholder");
                            if (placeholder) messagePanel.innerHTML = "";
                            appendMessageBubble(message);
                            scrollToBottom();
                        }
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

    function getAccountPlatform(acc) {
        if (!acc) return "whatsapp";
        if (acc.platform) return acc.platform.toLowerCase();
        if (acc.id && acc.id.startsWith("acc_tg_")) return "telegram";
        if (acc.id && acc.id.startsWith("acc_ig_")) return "instagram";
        return "whatsapp";
    }

    function getFilteredAccounts() {
        if (activePlatform === "all") return accounts;
        return accounts.filter(a => getAccountPlatform(a) === activePlatform);
    }

    async function loadPlatformCounts() {
        try {
            const res = await fetch("/api/platform_counts");
            const counts = await res.json();
            
            const elAll = document.getElementById("plat-count-all");
            const elWa = document.getElementById("plat-count-wa");
            const elTg = document.getElementById("plat-count-tg");
            const elIg = document.getElementById("plat-count-ig");

            if (elAll) elAll.innerText = counts.total ? counts.total.accounts : 0;
            if (elWa) elWa.innerText = counts.whatsapp ? counts.whatsapp.accounts : 0;
            if (elTg) elTg.innerText = counts.telegram ? counts.telegram.accounts : 0;
            if (elIg) elIg.innerText = counts.instagram ? counts.instagram.accounts : 0;
        } catch (e) {
            console.error("Error loading platform counts:", e);
        }
    }

    // --- Accounts Management ---
    async function loadAccounts() {
        try {
            const res = await fetch("/api/accounts");
            accounts = await res.json();
            renderAccountsDropdown();
            await loadPlatformCounts();

            if (!activeAccountId && accounts && accounts.length) {
                const available = getFilteredAccounts();
                const firstConnected = available.find(a => a.status === 'Connected') || available[0];
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
        const available = getFilteredAccounts();
        available.forEach(acc => {
            const opt = document.createElement("option");
            opt.value = acc.id;
            const icon = acc.platform === "telegram" ? "✈️" : (acc.platform === "instagram" ? "📸" : "🟢");
            opt.textContent = `${icon} ${acc.name} (${acc.status})`;
            dropdown.appendChild(opt);
        });

        if (activeAccountId && available.some(a => a.id === activeAccountId)) {
            dropdown.value = activeAccountId;
            updateActiveAccountUI();
        } else if (available.length > 0) {
            activeAccountId = available[0].id;
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
                    <p>No ${activePlatform.toUpperCase()} accounts configured.</p>
                    <button type="button" class="btn btn-primary btn-sm mt-3" id="btn-empty-plat-add">+ Add Account</button>
                </div>`;
            const emptyBtn = document.getElementById("btn-empty-plat-add");
            if (emptyBtn) emptyBtn.addEventListener("click", () => openAddAccountModalForPlatform(activePlatform));
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
            
            const platform = getAccountPlatform(activeAcc);
            const isConnected = activeAcc.status === "Connected";
            if (accountStatusIndicator) {
                accountStatusIndicator.className = `account-status-badge ${isConnected ? 'status-connected' : 'status-reconnect'}`;
                accountStatusIndicator.title = isConnected ? "Session Connected" : (platform === "whatsapp" ? "Click to view QR code and reconnect" : "Click to reconnect account");
                accountStatusIndicator.innerHTML = isConnected 
                    ? `<span class="status-dot online"></span> Connected`
                    : `<span class="status-dot warning"></span> ⚡ ${escapeHTML(activeAcc.status)} ${platform === "whatsapp" ? "(Scan QR)" : "(Reconnect)"}`;
            }

            // Keep chat list on left side intact! Never wipe contactsList!
            // Update right pane depending on session status:
            if (!isConnected) {
                if (platform === "whatsapp" && activePlatform !== "telegram" && activePlatform !== "instagram") {
                    if (!activeContactJid) {
                        showQrPane(false);
                    } else if (sessionNoticeBanner) {
                        sessionNoticeBanner.style.display = "flex";
                    }
                } else {
                    hideQrPane();
                    if (!activeContactJid) {
                        emptyState.style.display = "flex";
                    } else if (sessionNoticeBanner) {
                        sessionNoticeBanner.style.display = "flex";
                    }
                }
            } else {
                hideQrPane();
                if (sessionNoticeBanner) sessionNoticeBanner.style.display = "none";
            }
        } else {
            btnOpenSettings.disabled = true;
            btnOpenLogs.disabled = true;
            activeAvatar.innerText = "PG";
            if (accountStatusIndicator) {
                accountStatusIndicator.className = "account-status-badge";
                accountStatusIndicator.innerHTML = "";
            }
            hideQrPane();
        }
    }

    function showQrPane(triggerReconnect = true) {
        if (!activeAccountId) {
            hideQrPane();
            return;
        }
        const acc = accounts.find(a => a.id === activeAccountId);
        if (!acc) {
            hideQrPane();
            return;
        }
        const platform = getAccountPlatform(acc);
        // QR Code is strictly for WhatsApp! Never show for Telegram or Instagram!
        if (platform !== "whatsapp" || activePlatform === "telegram" || activePlatform === "instagram") {
            hideQrPane();
            return;
        }
        // If WhatsApp is already connected, hide QR
        if (acc.status === "Connected") {
            hideQrPane();
            return;
        }

        emptyState.style.display = "none";
        chatWindow.style.display = "none";
        if (qrPane) qrPane.style.display = "flex";

        if (qrPaneLoading) qrPaneLoading.style.display = "flex";
        if (qrPaneImage) qrPaneImage.style.display = "none";

        if (acc.qr) {
            if (qrPaneImage) {
                qrPaneImage.src = `data:image/png;base64,${acc.qr}`;
                qrPaneImage.style.display = "block";
            }
            if (qrPaneLoading) qrPaneLoading.style.display = "none";
            if (qrPaneStatusDot) qrPaneStatusDot.className = "status-dot warning";
            if (qrPaneStatusText) qrPaneStatusText.innerText = "Scan QR Code with Phone";
        } else {
            if (qrPaneStatusDot) qrPaneStatusDot.className = "status-dot warning";
            if (qrPaneStatusText) qrPaneStatusText.innerText = "Requesting secure QR session...";
            if (triggerReconnect) {
                fetch(`/api/accounts/${activeAccountId}/login`, { method: "POST" })
                    .catch(err => console.error("Error requesting login QR:", err));
            }
        }
    }

    function hideQrPane() {
        if (qrPane) qrPane.style.display = "none";
        if (activeContactJid) {
            chatWindow.style.display = "flex";
        } else {
            emptyState.style.display = "flex";
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
        if (!activeAccountId) {
            showSecurityToast("Please select a WhatsApp account first to delete.", "warning");
            return;
        }

        const acc = accounts.find(a => a.id === activeAccountId);
        const accName = acc?.name || activeAccountId;
        const accPhone = acc?.phone ? `(${acc.phone})` : "";

        const confirmDelete = await showConfirmDialog(
            "Delete WhatsApp Account",
            `Are you sure you want to permanently delete account "${accName}" ${accPhone}?\n\nThis will remove all session credentials and saved chat data for this account.`,
            "Delete Permanently",
            true
        );
        if (!confirmDelete) return;

        try {
            showSecurityToast("Deleting account...", "info");
            const res = await fetch("/api/accounts/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ account_id: activeAccountId })
            });
            const data = await res.json();
            if (data.success) {
                showSecurityToast(`Account "${accName}" was permanently removed.`, "danger");
                closeSettingsModal();
                activeAccountId = "";
                activeContactJid = "";
                hideChatWindow();
                hideQrPane();
                await loadAccounts();
            } else {
                showSecurityToast("Failed to delete account: " + (data.error || "Unknown error"), "danger");
            }
        } catch (err) {
            console.error("Error deleting account:", err);
            showSecurityToast("Error deleting account: " + err.message, "danger");
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

    function showNotificationToast(title, body = "", color = "var(--wa-green)") {
        const toast = document.createElement("div");
        toast.className = "security-toast";
        toast.style.borderColor = color || "var(--wa-green)";
        toast.innerHTML = `
            <div class="security-toast-header">
                <span class="security-toast-title" style="color: ${color || 'var(--wa-green)'}">${escapeHTML(title)}</span>
            </div>
            ${body ? `<div class="security-toast-body">${escapeHTML(body)}</div>` : ''}
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 3500);
    }

    function showSecurityToast(title, typeOrColor = "info") {
        let color = "var(--wa-green)";
        if (typeOrColor === "danger" || typeOrColor === "error") color = "var(--danger)";
        else if (typeOrColor === "warning") color = "var(--warning)";
        else if (typeOrColor === "info") color = "var(--info)";
        else if (typeOrColor && (typeOrColor.startsWith("#") || typeOrColor.startsWith("var("))) color = typeOrColor;
        showNotificationToast(title, "", color);
    }
    window.showSecurityToast = showSecurityToast;
    window.showNotificationToast = showNotificationToast;

    function showConfirmDialog(title, message, confirmBtnText = "Confirm", isDanger = false) {
        return new Promise((resolve) => {
            const modal = document.getElementById("confirm-dialog-modal");
            const titleEl = document.getElementById("confirm-dialog-title");
            const msgEl = document.getElementById("confirm-dialog-message");
            const btnOk = document.getElementById("btn-confirm-dialog-ok");
            const btnCancel = document.getElementById("btn-confirm-dialog-cancel");
            const btnClose = document.getElementById("btn-confirm-dialog-close");

            if (!modal) {
                resolve(confirm(message));
                return;
            }

            titleEl.textContent = title;
            msgEl.textContent = message;
            btnOk.textContent = confirmBtnText;
            btnOk.className = isDanger ? "btn btn-danger" : "btn btn-primary";
            modal.style.display = "flex";

            function cleanup(result) {
                modal.style.display = "none";
                btnOk.removeEventListener("click", onOk);
                btnCancel.removeEventListener("click", onCancel);
                if (btnClose) btnClose.removeEventListener("click", onCancel);
                modal.removeEventListener("click", onBackdrop);
                document.removeEventListener("keydown", onKeyDown);
                resolve(result);
            }

            function onOk() { cleanup(true); }
            function onCancel() { cleanup(false); }
            function onBackdrop(e) { if (e.target === modal) cleanup(false); }
            function onKeyDown(e) { if (e.key === "Escape") cleanup(false); }

            btnOk.addEventListener("click", onOk);
            btnCancel.addEventListener("click", onCancel);
            if (btnClose) btnClose.addEventListener("click", onCancel);
            modal.addEventListener("click", onBackdrop);
            document.addEventListener("keydown", onKeyDown);
        });
    }
    window.showConfirmDialog = showConfirmDialog;

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

    function openAddAccountModalForPlatform(platform) {
        addAccountModal.style.display = "flex";
        
        let tabId = "tab-add-whatsapp";
        if (platform === "telegram") tabId = "tab-add-telegram";
        else if (platform === "instagram") tabId = "tab-add-instagram";

        // Activate corresponding tab button
        document.querySelectorAll("#add-account-platform-tabs .tab-btn").forEach(btn => {
            btn.classList.toggle("active", btn.getAttribute("data-platform-tab") === tabId);
        });
        document.querySelectorAll("#add-account-modal .tab-pane").forEach(pane => {
            pane.style.display = pane.id === tabId ? "block" : "none";
            pane.classList.toggle("active", pane.id === tabId);
        });

        if (tabId === "tab-add-whatsapp") {
            requestWhatsAppQrSession();
        }
    }

    async function openAddAccountModal() {
        openAddAccountModalForPlatform(activePlatform !== "all" ? activePlatform : "whatsapp");
    }

    async function requestWhatsAppQrSession() {
        qrLoading.style.display = "flex";
        qrImage.style.display = "none";
        qrStatusDot.className = "status-dot warning";
        qrStatusText.innerText = "Status: Initializing session...";
        qrSessionId = "";

        try {
            const res = await fetch("/api/accounts/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ platform: "whatsapp" })
            });
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
        openAddAccountModalForPlatform("whatsapp");
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
        const tgFeedback = document.getElementById("tg-status-feedback");
        if (tgFeedback) tgFeedback.style.display = "none";
        const igFeedback = document.getElementById("ig-status-feedback");
        if (igFeedback) igFeedback.style.display = "none";
    }

    // --- Telegram Authentication (Phone -> OTP Code -> Optional 2FA) ---
    let tgCountdownTimer = null;
    let tgCountdownSeconds = 0;

    function startTgResendCountdown(seconds) {
        if (tgCountdownTimer) clearInterval(tgCountdownTimer);
        tgCountdownSeconds = Math.max(seconds || 60, 15);
        
        const timerText = document.getElementById("tg-resend-timer-text");
        const countdownEl = document.getElementById("tg-resend-countdown");
        const resendBtn = document.getElementById("btn-tg-resend-sms");

        if (timerText) timerText.style.display = "inline";
        if (resendBtn) resendBtn.style.display = "none";
        if (countdownEl) countdownEl.innerText = tgCountdownSeconds;

        tgCountdownTimer = setInterval(() => {
            tgCountdownSeconds--;
            if (countdownEl) countdownEl.innerText = tgCountdownSeconds;
            if (tgCountdownSeconds <= 0) {
                clearInterval(tgCountdownTimer);
                tgCountdownTimer = null;
                if (timerText) timerText.style.display = "none";
                if (resendBtn) resendBtn.style.display = "inline-block";
            }
        }, 1000);
    }

    async function handleTelegramResendSms() {
        const feedback = document.getElementById("tg-status-feedback");
        const resendBtn = document.getElementById("btn-tg-resend-sms");
        if (!tgCurrentAccountId) return;

        if (resendBtn) {
            resendBtn.disabled = true;
            resendBtn.innerText = "Requesting SMS from Telegram...";
        }

        try {
            const res = await fetch("/api/telegram/resend_code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ account_id: tgCurrentAccountId })
            });
            const data = await res.json();
            if (data.success) {
                feedback.className = "status-feedback success";
                feedback.innerText = data.delivery_text || "SMS requested from Telegram. Check your phone's SMS inbox.";
                feedback.style.display = "block";
                startTgResendCountdown(data.timeout || 60);
            } else {
                feedback.className = "status-feedback error";
                feedback.innerText = data.error || "Could not resend SMS. Please check your Telegram app.";
                feedback.style.display = "block";
            }
        } catch (err) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Failed to request SMS code.";
            feedback.style.display = "block";
        } finally {
            if (resendBtn) {
                resendBtn.disabled = false;
                resendBtn.innerText = "📩 Didn't receive code in app? Send via SMS";
            }
        }
    }

    async function handleTelegramSendOtp() {
        const phoneInput = document.getElementById("tg-phone-input");
        const feedback = document.getElementById("tg-status-feedback");
        const btn = document.getElementById("btn-tg-send-otp");
        const phone = (phoneInput.value || "").trim();

        if (!phone) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Please enter a valid phone number with country code.";
            feedback.style.display = "block";
            return;
        }

        feedback.style.display = "none";
        btn.disabled = true;
        btn.innerHTML = `<span>Requesting Telegram Code...</span>`;

        try {
            const res = await fetch("/api/telegram/send_code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone })
            });
            const data = await res.json();

            if (data.success) {
                tgCurrentAccountId = data.account_id;
                document.getElementById("tg-sent-phone-display").innerText = phone;

                const titleEl = document.getElementById("tg-delivery-title");
                const textEl = document.getElementById("tg-delivery-text");
                const iconEl = document.getElementById("tg-delivery-icon");

                if (data.delivery_type === "sms") {
                    if (iconEl) iconEl.innerText = "💬";
                    if (titleEl) titleEl.innerText = "Check Your SMS Messages";
                    if (textEl) textEl.innerHTML = `Telegram sent a verification code via SMS text message to <strong>${phone}</strong>.`;
                } else {
                    if (iconEl) iconEl.innerText = "📲";
                    if (titleEl) titleEl.innerText = "Check Your Telegram App!";
                    if (textEl) textEl.innerHTML = `Telegram sent the code to your <strong>Telegram app</strong>. Please open Telegram on your phone or PC and look for the official service chat from <strong>Telegram</strong> (verified checkmark). <em>(Telegram does NOT send SMS if your account is active in an app)</em>.`;
                }

                document.getElementById("tg-step-phone").style.display = "none";
                document.getElementById("tg-step-otp").style.display = "block";
                document.getElementById("tg-otp-input").value = "";
                document.getElementById("tg-otp-input").focus();

                startTgResendCountdown(data.timeout || 60);
            } else {
                feedback.className = "status-feedback error";
                feedback.innerText = data.error || "Failed to send Telegram OTP.";
                feedback.style.display = "block";
            }
        } catch (err) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Network error while contacting Telegram.";
            feedback.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>Send Telegram OTP Code</span>`;
        }
    }

    async function handleTelegramVerifyOtp() {
        const otpInput = document.getElementById("tg-otp-input");
        const pwdInput = document.getElementById("tg-password-input");
        const feedback = document.getElementById("tg-status-feedback");
        const btn = document.getElementById("btn-tg-verify-otp");
        const code = (otpInput.value || "").trim();
        const password = (pwdInput.value || "").trim();

        if (!code) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Please enter the 5-digit verification code.";
            feedback.style.display = "block";
            return;
        }

        feedback.style.display = "none";
        btn.disabled = true;
        btn.innerHTML = `<span>Verifying Code...</span>`;

        try {
            const res = await fetch("/api/telegram/verify_code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    account_id: tgCurrentAccountId,
                    code,
                    password
                })
            });
            const data = await res.json();

            if (data.success) {
                feedback.className = "status-feedback success";
                feedback.innerText = `Connected! Logged in as ${data.name || "Telegram User"}.`;
                feedback.style.display = "block";

                setTimeout(() => {
                    closeAddAccountModal();
                    loadAccounts().then(() => {
                        activeAccountId = tgCurrentAccountId;
                        dropdown.value = activeAccountId;
                        handleAccountSelectionChange();
                    });
                    loadPlatformCounts();
                }, 1000);
            } else {
                feedback.className = "status-feedback error";
                feedback.innerText = data.error || "Verification failed. Check the code or 2FA password.";
                feedback.style.display = "block";
            }
        } catch (err) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Network error verifying code.";
            feedback.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>Verify & Connect Telegram</span>`;
        }
    }

    // --- Instagram Authentication (Username/Password -> 2FA) ---
    async function handleInstagramLogin() {
        const userInput = document.getElementById("ig-username-input");
        const passInput = document.getElementById("ig-password-input");
        const feedback = document.getElementById("ig-status-feedback");
        const btn = document.getElementById("btn-ig-login");
        const username = (userInput.value || "").trim();
        const password = (passInput.value || "").trim();

        if (!username || !password) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Please enter both Instagram username and password.";
            feedback.style.display = "block";
            return;
        }

        feedback.style.display = "none";
        btn.disabled = true;
        btn.innerHTML = `<span>Connecting to Instagram...</span>`;

        try {
            const res = await fetch("/api/instagram/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();

            if (data.success) {
                feedback.className = "status-feedback success";
                feedback.innerText = `Connected! Logged in as @${username}.`;
                feedback.style.display = "block";

                setTimeout(() => {
                    closeAddAccountModal();
                    loadAccounts().then(() => {
                        activeAccountId = data.account_id;
                        dropdown.value = activeAccountId;
                        handleAccountSelectionChange();
                    });
                    loadPlatformCounts();
                }, 1000);
            } else if (data.requires_2fa) {
                igCurrentAccountId = data.account_id;
                document.getElementById("ig-username-display").innerText = "@" + username;
                document.getElementById("ig-step-credentials").style.display = "none";
                document.getElementById("ig-step-2fa").style.display = "block";
                document.getElementById("ig-2fa-input").focus();
            } else {
                feedback.className = "status-feedback error";
                feedback.innerText = data.error || "Instagram login failed.";
                feedback.style.display = "block";
            }
        } catch (err) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Network error logging into Instagram.";
            feedback.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>Connect Instagram Account</span>`;
        }
    }

    async function handleInstagramVerify2Fa() {
        const codeInput = document.getElementById("ig-2fa-input");
        const feedback = document.getElementById("ig-status-feedback");
        const btn = document.getElementById("btn-ig-verify-2fa");
        const code = (codeInput.value || "").trim();

        if (!code) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Please enter the two-factor security code.";
            feedback.style.display = "block";
            return;
        }

        feedback.style.display = "none";
        btn.disabled = true;
        btn.innerHTML = `<span>Verifying 2FA...</span>`;

        try {
            const res = await fetch("/api/instagram/verify_2fa", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    account_id: igCurrentAccountId,
                    code
                })
            });
            const data = await res.json();

            if (data.success) {
                feedback.className = "status-feedback success";
                feedback.innerText = `Connected to Instagram!`;
                feedback.style.display = "block";

                setTimeout(() => {
                    closeAddAccountModal();
                    loadAccounts().then(() => {
                        activeAccountId = igCurrentAccountId;
                        dropdown.value = activeAccountId;
                        handleAccountSelectionChange();
                    });
                    loadPlatformCounts();
                }, 1000);
            } else {
                feedback.className = "status-feedback error";
                feedback.innerText = data.error || "2FA verification failed.";
                feedback.style.display = "block";
            }
        } catch (err) {
            feedback.className = "status-feedback error";
            feedback.innerText = "Network error verifying 2FA code.";
            feedback.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>Verify & Connect</span>`;
        }
    }

    // --- Contacts & Chats Logic ---
    async function loadContacts() {
        if (!activeAccountId) return;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/contacts`);
            contacts = await res.json();
            applyFiltersAndRender();
        } catch (err) {
            console.error("Error fetching contacts:", err);
        }
    }

    // --- Name & Phone Number Resolution Helpers ---
    function isProperName(name) {
        if (!name || typeof name !== 'string') return false;
        const trimmed = name.trim();
        if (!trimmed || trimmed === '.' || trimmed === '..' || trimmed === '-' || trimmed === 'WA' || trimmed === 'null' || trimmed === 'None' || trimmed === 'Unknown' || trimmed === 'Member') {
            return false;
        }
        const cleanDigits = trimmed.replace(/[@\s\-\+\(\)\.]/g, '');
        if (/^\d+$/.test(cleanDigits) || trimmed.includes('@lid') || trimmed.includes('@s.whatsapp.net')) {
            return false;
        }
        return true;
    }

    function formatPhoneNumber(numOrJid) {
        if (!numOrJid) return "";
        let clean = String(numOrJid).split('@')[0].replace(/[^\d+]/g, '');
        if (!clean) return String(numOrJid).split('@')[0];
        if (clean.startsWith('+')) clean = clean.substring(1);
        
        // India (12 digits starting with 91)
        if (clean.length === 12 && clean.startsWith('91')) {
            return `+91 ${clean.substring(2, 7)} ${clean.substring(7)}`;
        }
        // India local 10 digits
        if (clean.length === 10 && ['6','7','8','9'].includes(clean[0])) {
            return `+91 ${clean.substring(0, 5)} ${clean.substring(5)}`;
        }
        // US / Canada (11 digits starting with 1)
        if (clean.length === 11 && clean.startsWith('1')) {
            return `+1 (${clean.substring(1, 4)}) ${clean.substring(4, 7)}-${clean.substring(7)}`;
        }
        // UK (12 digits starting with 44)
        if (clean.length === 12 && clean.startsWith('44')) {
            return `+44 ${clean.substring(2, 6)} ${clean.substring(6)}`;
        }
        // General International
        if (clean.length >= 7 && clean.length <= 15) {
            if (clean.length > 10) {
                return `+${clean.substring(0, clean.length - 10)} ${clean.substring(clean.length - 10, clean.length - 5)} ${clean.substring(clean.length - 5)}`;
            }
            return `+${clean}`;
        }
        return `+${clean}`;
    }

    function getChatDisplayName(contact) {
        if (!contact) return "Chat";
        if (contact.is_group) {
            if (isProperName(contact.name)) return contact.name;
            return "WhatsApp Group";
        }
        // If contact has a saved name, ALWAYS return that name!
        if (isProperName(contact.name)) {
            return contact.name;
        }
        // If new number: use phone number
        const phone = contact.phone_number || (contact.jid && !contact.jid.includes('@lid') ? contact.jid.split('@')[0] : '');
        if (phone && phone.replace(/[^\d]/g, '').length >= 7) {
            return formatPhoneNumber(phone);
        }
        // Fallback: check if JID has phone number digits
        if (contact.jid) {
            const rawUser = contact.jid.split('@')[0];
            if (!contact.jid.includes('@lid') && rawUser.length >= 7 && rawUser.length <= 13) {
                return formatPhoneNumber(rawUser);
            }
        }
        return "New Contact";
    }

    function getChatInitials(contact, displayName) {
        if (contact && contact.is_group) {
            return "👥";
        }
        const name = displayName || (contact ? contact.name : "");
        if (name && isProperName(name)) {
            const parts = name.trim().split(/\s+/).filter(Boolean);
            if (parts.length >= 2) {
                return (parts[0][0] + parts[1][0]).toUpperCase();
            }
            return name.substring(0, 2).toUpperCase();
        }
        // Unsaved phone number: show last 2 digits
        if (name && name.startsWith('+')) {
            const digits = name.replace(/[^\d]/g, '');
            return digits.length >= 2 ? digits.slice(-2) : "#";
        }
        return "👤";
    }

    function applyFiltersAndRender() {
        let filtered = contacts;

        // Update live counts on the filter pills
        const countAll = contacts.length;
        const countChats = contacts.filter(c => !c.is_group).length;
        const countGroups = contacts.filter(c => c.is_group).length;

        const elCountAll = document.getElementById("filter-count-all");
        const elCountChats = document.getElementById("filter-count-chats");
        const elCountGroups = document.getElementById("filter-count-groups");
        if (elCountAll) elCountAll.innerText = countAll > 0 ? `(${countAll})` : "";
        if (elCountChats) elCountChats.innerText = countChats > 0 ? `(${countChats})` : "";
        if (elCountGroups) elCountGroups.innerText = countGroups > 0 ? `(${countGroups})` : "";
        
        // Tab Filter: all, chats, groups
        if (activeFilter === "chats") {
            filtered = contacts.filter(c => !c.is_group);
        } else if (activeFilter === "groups") {
            filtered = contacts.filter(c => c.is_group);
        }

        // Search Filter: matches name, phone number, formatted phone number, or JID
        const query = chatSearch.value.toLowerCase().trim();
        if (query) {
            filtered = filtered.filter(c => {
                const name = (c.name || "").toLowerCase();
                const jid = (c.jid || "").toLowerCase();
                const phone = (c.phone_number || "").toLowerCase();
                const formatted = formatPhoneNumber(c.phone_number || c.jid).toLowerCase();
                return name.includes(query) || jid.includes(query) || phone.includes(query) || formatted.includes(query);
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
                    <p class="secondary-text">Type a phone number or username in search box and press Enter to start chatting.</p>
                </div>`;
            return;
        }

        contactsListToRender.forEach(c => {
            const item = document.createElement("div");
            item.className = `contact-item ${isMatchingChat(c.jid, activeContactJid) ? 'active' : ''}`;
            
            const displayName = getChatDisplayName(c);
            const initials = getChatInitials(c, displayName);
            const avatarClass = c.is_group ? "contact-avatar group-avatar" : "contact-avatar";

            const activeAcc = accounts.find(a => a.id === activeAccountId);
            const platform = c.platform || (activeAcc && activeAcc.platform) || "whatsapp";
            let platTag = '<span class="contact-platform-tag wa">WA</span>';
            if (platform === "telegram") platTag = '<span class="contact-platform-tag tg">TG</span>';
            else if (platform === "instagram") platTag = '<span class="contact-platform-tag ig">IG</span>';

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
                        <span class="contact-name">${platTag}${escapeHTML(displayName)}</span>
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

        const activeAcc = accounts.find(a => a.id === activeAccountId);
        const platform = (contact && contact.platform) || (activeAcc && activeAcc.platform) || "whatsapp";

        // Update platform badge pill in chat header
        const chatPlatPill = document.getElementById("chat-platform-pill");
        if (chatPlatPill) {
            chatPlatPill.className = "platform-header-pill " + (platform === "telegram" ? "tg" : (platform === "instagram" ? "ig" : "wa"));
            chatPlatPill.innerHTML = platform === "telegram" ? "✈️ Telegram" : (platform === "instagram" ? "📸 Instagram" : "🟢 WhatsApp");
        }

        const displayName = getChatDisplayName(contact);
        chatContactName.innerText = displayName;

        if (contact.is_group) {
            chatContactJid.innerText = platform === "telegram" ? "Telegram Group" : (platform === "instagram" ? "Instagram Group" : "WhatsApp Group");
        } else if (isProperName(contact.name)) {
            // Contact has a saved name: show phone number as subtitle!
            const phone = contact.phone_number || (contact.jid && !contact.jid.includes('@lid') ? contact.jid.split('@')[0] : '');
            chatContactJid.innerText = phone ? formatPhoneNumber(phone) : (contact.jid || "");
        } else {
            // Unsaved / new number: title is already the phone number, show subtitle as Contact
            chatContactJid.innerText = platform === "telegram" ? "Telegram Contact" : (platform === "instagram" ? "Instagram Direct" : "WhatsApp Contact");
        }
        
        const initials = getChatInitials(contact, displayName);
        chatAvatar.innerText = initials;
        chatAvatar.className = contact.is_group ? "avatar group-avatar" : "avatar";

        emptyState.style.display = "none";
        hideQrPane();
        chatWindow.style.display = "flex";

        // Check if active account is logged out/disconnected and show banner
        if (activeAcc && activeAcc.status !== "Connected" && sessionNoticeBanner) {
            sessionNoticeBanner.style.display = "flex";
        } else if (sessionNoticeBanner) {
            sessionNoticeBanner.style.display = "none";
        }

        loadMessages();
    }

    function hideChatWindow() {
        chatWindow.style.display = "none";
        const acc = accounts.find(a => a.id === activeAccountId);
        const platform = getAccountPlatform(acc);
        if (acc && acc.status !== "Connected" && platform === "whatsapp" && activePlatform !== "telegram" && activePlatform !== "instagram") {
            showQrPane(false);
        } else {
            hideQrPane();
            emptyState.style.display = "flex";
        }
    }

    async function loadMessages() {
        if (!activeAccountId || !activeContactJid) return;

        messagePanel.innerHTML = `
            <div class="empty-chat-placeholder" style="opacity: 0.6; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary);">
                <div class="spinner" style="width: 24px; height: 24px; border: 2px solid rgba(255,255,255,0.2); border-top-color: var(--wa-green); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 10px;"></div>
                <p style="font-size: 13px;">Loading conversation...</p>
            </div>
        `;

        try {
            const res = await fetch(`/api/accounts/${activeAccountId}/messages?contact=${encodeURIComponent(activeContactJid)}`);
            let messages = await res.json();
            
            if (!Array.isArray(messages)) {
                messages = messages.messages || [];
            }
            
            messagePanel.innerHTML = "";
            if (messages.length === 0) {
                messagePanel.innerHTML = `
                    <div class="empty-chat-placeholder" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80%; text-align: center; color: var(--text-secondary); margin: auto;">
                        <div style="font-size: 38px; margin-bottom: 8px;">💬</div>
                        <p style="font-weight: 500; font-size: 15px; color: var(--text-primary); margin-bottom: 4px;">No messages yet</p>
                        <small style="font-size: 12.5px;">Send a message below to start the conversation.</small>
                    </div>
                `;
                return;
            }

            messages.forEach(msg => {
                appendMessageBubble(msg);
            });
            scrollToBottom();
        } catch (err) {
            console.error("Error loading messages:", err);
            messagePanel.innerHTML = `
                <div class="empty-chat-placeholder" style="text-align: center; padding: 40px; color: var(--danger);">
                    <p>Failed to load messages: ${escapeHTML(err.message)}</p>
                </div>
            `;
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
            let displayName = "";
            const senderJid = msg.sender || "";
            const cleanSender = senderJid.split('@')[0];
            // Try matching in loaded contacts
            const matchedContact = contacts.find(c => 
                isMatchingChat(c.jid, senderJid) || 
                (c.phone_number && (c.phone_number === cleanSender || senderJid.includes(c.phone_number)))
            );
            if (matchedContact && isProperName(matchedContact.name)) {
                displayName = matchedContact.name;
            } else if (isProperName(msg.sender_name)) {
                displayName = msg.sender_name;
            } else {
                // New number: show formatted phone number!
                const rawNum = matchedContact?.phone_number || (senderJid && !senderJid.includes('@lid') ? cleanSender : '');
                displayName = rawNum ? formatPhoneNumber(rawNum) : (senderJid ? formatDisplayJid(senderJid) : 'Participant');
            }
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

    // Lightbox modal controls
    function openPhotoLightbox(src, captionText = "") {
        if (!photoLightboxModal || !lightboxImage) return;
        lightboxImage.src = src;
        if (lightboxCaption) {
            lightboxCaption.textContent = captionText;
            lightboxCaption.style.display = captionText ? "block" : "none";
        }
        photoLightboxModal.style.display = "flex";
        document.body.style.overflow = "hidden";
    }
    window.openPhotoLightbox = openPhotoLightbox;

    function closePhotoLightbox() {
        if (!photoLightboxModal) return;
        photoLightboxModal.style.display = "none";
        if (lightboxImage) lightboxImage.src = "";
        document.body.style.overflow = "";
    }
    window.closePhotoLightbox = closePhotoLightbox;

    function renderAttachmentHtml(attachment) {
        if (!attachment) return '';

        const type = attachment.type || 'attachment';
        const localUrl = attachment.local_url || '';
        // WhatsApp attachment.url points to mmg.whatsapp.net which requires WhatsApp authorization and returns 403.
        // We prioritize local_url (disk storage) or inline base64 preview (data:image/jpeg;base64,...).
        const preview = (attachment.preview && attachment.preview.startsWith('data:image')) ? attachment.preview : '';
        const caption = attachment.caption ? `<div class="attachment-caption">${escapeHTML(attachment.caption)}</div>` : '';

        // 1. Audio / Voice Note Player
        if (type === 'audio') {
            const audioSrc = localUrl || (attachment.url && !attachment.url.includes('whatsapp.net') ? attachment.url : '');
            return `
                <div class="media-container audio-media">
                    <audio controls preload="metadata" src="${escapeHTML(audioSrc)}">
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
            const displaySrc = localUrl || preview;
            if (displaySrc) {
                return `
                    <div class="media-container image-media">
                        <div class="photo-card-wrapper" onclick="window.openPhotoLightbox('${escapeHTML(displaySrc)}', '${escapeHTML(attachment.caption || '')}')" title="Click to view full image">
                            <img src="${escapeHTML(displaySrc)}" class="chat-photo" loading="lazy" alt="WhatsApp Photo">
                            <div class="photo-hover-overlay">
                                <span class="photo-zoom-badge">🔍 Click to Zoom</span>
                            </div>
                        </div>
                        ${caption}
                    </div>
                `;
            } else {
                return `
                    <div class="media-container image-media">
                        <div class="image-placeholder-card">
                            <span class="img-icon">📷</span>
                            <div class="img-details">
                                <span class="img-title">WhatsApp Photo</span>
                                <span class="img-subtitle">Media preview pending download</span>
                            </div>
                        </div>
                        ${caption}
                    </div>
                `;
            }
        }

        // 3. Video Player
        if (type === 'video') {
            const videoSrc = localUrl || (attachment.url && !attachment.url.includes('whatsapp.net') ? attachment.url : '');
            return `
                <div class="media-container video-media">
                    ${videoSrc ? `<video controls preload="metadata" src="${escapeHTML(videoSrc)}"></video>` : `
                    <div class="image-placeholder-card">
                        <span class="img-icon">🎥</span>
                        <div class="img-details">
                            <span class="img-title">WhatsApp Video</span>
                            <span class="img-subtitle">${attachment.duration ? formatDuration(attachment.duration) : 'Video file'}</span>
                        </div>
                    </div>`}
                    ${caption}
                </div>
            `;
        }

        // 4. Document / File
        if (type === 'document') {
            const fileName = attachment.file_name || 'Document';
            const docUrl = localUrl || (attachment.url && !attachment.url.includes('whatsapp.net') ? attachment.url : '');
            return `
                <div class="media-container document-media">
                    <span class="doc-icon">📄</span>
                    <div class="doc-info">
                        <span class="doc-name">${escapeHTML(fileName)}</span>
                        ${docUrl ? `<a href="${escapeHTML(docUrl)}" download="${escapeHTML(fileName)}" class="btn-download-doc">Download File</a>` : ''}
                    </div>
                </div>
                ${caption}
            `;
        }

        // 5. Sticker
        if (type === 'sticker') {
            const stickerSrc = localUrl || preview;
            if (stickerSrc) {
                return `
                    <div class="media-container sticker-media" style="max-width: 140px;">
                        <img src="${escapeHTML(stickerSrc)}" style="width: 100%; border-radius: 6px;" alt="Sticker">
                    </div>
                `;
            }
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

    function updateContactLastMessage(chatJid, msg, altJid) {
        let contact = contacts.find(c => isMatchingChat(chatJid, c.jid, altJid));
        
        let snippet = msg.body || '';
        if (msg.is_deleted) {
            snippet = "🚫 This message was deleted";
        } else if (msg.attachment) {
            const icons = { image: "📷 Photo", audio: "🎵 Voice note", video: "🎥 Video", document: "📄 Document", sticker: "✨ Sticker" };
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
        
        // Optimistic UI Rendering: immediately bind bubble in UI
        const tempId = `out_temp_${Date.now()}`;
        const tempMsg = {
            id: tempId,
            sender: "Me",
            sender_name: "Me",
            chat_jid: activeContactJid,
            body: text,
            timestamp: Math.floor(Date.now() / 1000),
            is_outgoing: true
        };

        // If placeholder empty notice is showing, clear it first
        const placeholder = messagePanel.querySelector(".empty-chat-placeholder");
        if (placeholder) {
            messagePanel.innerHTML = "";
        }

        appendMessageBubble(tempMsg);
        scrollToBottom();
        updateContactLastMessage(activeContactJid, tempMsg);

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
                const bubble = document.querySelector(`.message[data-msg-id="${tempId}"]`);
                if (bubble) {
                    bubble.style.borderColor = "var(--danger)";
                    const timeEl = bubble.querySelector(".message-time");
                    if (timeEl) timeEl.innerHTML += ` <span style="color: var(--danger);" title="Failed to deliver">⚠️</span>`;
                }
                alert(data.error || "Failed to send message. Account may be disconnected.");
            }
        } catch (err) {
            console.error("Error sending message:", err);
            const bubble = document.querySelector(`.message[data-msg-id="${tempId}"]`);
            if (bubble) {
                bubble.style.borderColor = "var(--danger)";
            }
            alert("Network error sending message.");
        }
    }

    function isMatchingChat(incomingJid, currentJid, altJid) {
        if (!incomingJid || !currentJid) return false;
        if (incomingJid === currentJid) return true;
        if (altJid && (altJid === currentJid || altJid === incomingJid)) return true;

        const user1 = incomingJid.split('@')[0];
        const user2 = currentJid.split('@')[0];
        if (user1 === user2) return true;

        const digits1 = user1.replace(/\D/g, '');
        const digits2 = user2.replace(/\D/g, '');
        if (digits1 && digits2 && (digits1 === digits2 || digits1.endsWith(digits2) || digits2.endsWith(digits1))) {
            if (digits1.length >= 8 && digits2.length >= 8) return true;
        }
        return false;
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
        if (jid.endsWith("@g.us")) return "WhatsApp Group";
        if (jid.includes("@lid")) {
            const matched = contacts.find(c => c.jid === jid || c.alt_jid === jid);
            if (matched?.phone_number) {
                return formatPhoneNumber(matched.phone_number);
            }
            return "WhatsApp Contact";
        }
        return formatPhoneNumber(jid);
    }

    // ========================================================
    // ADVANCED SCHEDULED & AUTOMATED MESSAGES LOGIC
    // ========================================================
    function openSchedulesModal(defaultTab = "tab-schedules-list") {
        if (!schedulesModal) return;
        schedulesModal.style.display = "flex";
        populateContactsDropdown();
        switchSchedulesTab(defaultTab);
        loadSchedules();
        loadSampleTemplates();
    }

    function closeSchedulesModal() {
        if (!schedulesModal) return;
        schedulesModal.style.display = "none";
    }

    function switchSchedulesTab(tabId) {
        document.querySelectorAll("#schedules-modal .sched-tab-btn").forEach(btn => {
            btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
        });
        document.querySelectorAll("#schedules-modal .sched-tab-pane").forEach(pane => {
            pane.classList.toggle("active", pane.id === tabId);
        });
        if (tabId === "tab-schedules-list") {
            renderSchedulesList();
        } else if (tabId === "tab-schedules-templates") {
            renderTemplatesLibrary();
        }
    }

    function populateContactsDropdown() {
        if (!schedRecipientSelect) return;
        const currentVal = schedRecipientSelect.value;
        schedRecipientSelect.innerHTML = '<option value="">-- Choose from WhatsApp Contacts / Groups --</option>';

        // Sort contacts alphabetically
        const sorted = [...contacts].sort((a, b) => {
            const na = getChatDisplayName(a).toLowerCase();
            const nb = getChatDisplayName(b).toLowerCase();
            return na.localeCompare(nb);
        });

        sorted.forEach(c => {
            const name = getChatDisplayName(c);
            const opt = document.createElement("option");
            opt.value = c.jid;
            opt.textContent = `${name} (${c.is_group ? 'Group' : (c.phone_number || c.jid.split('@')[0])})`;
            schedRecipientSelect.appendChild(opt);
        });

        if (currentVal) schedRecipientSelect.value = currentVal;
    }

    async function loadSchedules() {
        try {
            const res = await fetch("/api/schedules");
            schedules = await res.json();
            
            // Update sidebar badge
            const activeCount = schedules.filter(s => s.enabled).length;
            if (schedulesCounterBadge) {
                schedulesCounterBadge.textContent = activeCount;
                schedulesCounterBadge.style.display = activeCount > 0 ? "flex" : "none";
            }

            renderSchedulesList();
        } catch (err) {
            console.error("Error loading schedules:", err);
        }
    }

    function renderSchedulesList() {
        if (!schedulesCardsContainer) return;
        schedulesCardsContainer.innerHTML = "";

        let filtered = schedules;
        if (activeSchedFilter !== "all") {
            filtered = schedules.filter(s => s.category === activeSchedFilter);
        }

        if (filtered.length === 0) {
            schedulesCardsContainer.innerHTML = `
                <div class="list-empty" style="padding: 30px;">
                    <div style="font-size: 36px; margin-bottom: 8px;">⏰</div>
                    <p style="font-weight: 600; color: var(--text-primary);">No scheduled messages in this category</p>
                    <p class="secondary-text">Click <strong>"+ Add New Schedule"</strong> or browse the <strong>Sample Templates Library</strong>.</p>
                </div>
            `;
            return;
        }

        filtered.forEach(s => {
            const card = document.createElement("div");
            card.className = `schedule-card ${s.enabled ? '' : 'disabled'}`;
            card.id = `sched-card-${s.id}`;

            const catMap = {
                birthday: { badge: "🎂 Birthday Wish", cls: "bday" },
                anniversary: { badge: "💍 Anniversary", cls: "anni" },
                morning: { badge: "🌅 Morning", cls: "morn" },
                afternoon: { badge: "☀️ Afternoon", cls: "morn" },
                night: { badge: "🌙 Night", cls: "anni" },
                festival: { badge: "🪔 Festival", cls: "fest" },
                reminder: { badge: "💧 Reminder", cls: "morn" },
                custom: { badge: "✨ Custom", cls: "" }
            };
            const catInfo = catMap[s.category] || { badge: s.category || "Custom", cls: "" };

            // Format timing description
            let timingDesc = "";
            if (s.schedule_type === "annual") {
                const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
                const mName = months[(s.annual_month || 1) - 1];
                timingDesc = `📅 Yearly on ${s.annual_day} ${mName} at ${s.time_of_day || '09:00'}`;
            } else if (s.schedule_type === "daily") {
                timingDesc = `🔁 Daily at ${s.time_of_day || '08:00'}`;
            } else if (s.schedule_type === "weekly") {
                const dayNames = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
                const daysStr = (s.days_of_week || []).map(d => dayNames[d]).join(", ");
                timingDesc = `🗓️ Weekly (${daysStr || 'Mon'}) at ${s.time_of_day || '09:00'}`;
            } else if (s.schedule_type === "once") {
                timingDesc = `⏰ Once at ${s.scheduled_datetime || 'Specified date/time'}`;
            }

            // Next run time
            let nextRunStr = "Pending";
            if (s.next_run) {
                const d = new Date(s.next_run * 1000);
                nextRunStr = d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }

            // Recipients label
            let recipientsLabel = "No recipient set";
            if (s.recipients && s.recipients.length > 0) {
                recipientsLabel = s.recipients.map(r => r.name || r.jid || r.phone).join(", ");
            }

            card.innerHTML = `
                <div class="schedule-card-header">
                    <div class="schedule-title-area">
                        <span class="schedule-cat-badge ${catInfo.cls}">${catInfo.badge}</span>
                        <h4>${escapeHTML(s.title || 'Untitled Schedule')}</h4>
                    </div>
                    <label class="switch-control" title="Toggle Enable / Disable">
                        <input type="checkbox" ${s.enabled ? 'checked' : ''} onchange="window.handleToggleSchedule('${s.id}', ${s.enabled})">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="schedule-card-body">
                    ${escapeHTML(s.message_template || '')}
                </div>

                <div class="schedule-card-meta">
                    <div>
                        <span>To: <strong class="sched-target-tag">${escapeHTML(recipientsLabel)}</strong></span>
                        <span class="sched-timing-tag ms-2">${timingDesc}</span>
                    </div>
                    <div>
                        <span style="color: ${s.enabled ? 'var(--wa-green)' : 'var(--text-secondary)'}; font-size: 11.5px;">
                            ${s.enabled ? '⏳ Next: ' + nextRunStr : '⏸️ Paused'}
                        </span>
                    </div>
                </div>

                <div class="d-flex justify-content-between align-items-center pt-2 border-top">
                    <small class="secondary-text" style="font-size: 11px;">
                        Status: <strong>${escapeHTML(s.last_status || 'Scheduled')}</strong>
                        ${s.sent_count ? ` • Sent ${s.sent_count} time(s)` : ''}
                    </small>
                    <div class="sched-card-actions">
                        <button type="button" class="btn-sched-action" onclick="window.handleTestSendSchedule('${s.id}')" title="Send a test message right now">
                            ⚡ Send Test Now
                        </button>
                        <button type="button" class="btn-sched-action" onclick="window.handleEditSchedule('${s.id}')">
                            ✏️ Edit
                        </button>
                        <button type="button" class="btn-sched-action danger" onclick="window.handleDeleteSchedule('${s.id}')">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
            `;
            schedulesCardsContainer.appendChild(card);
        });
    }

    async function loadSampleTemplates() {
        try {
            const res = await fetch("/api/schedules/templates");
            sampleTemplates = await res.json();
            renderTemplatesLibrary();
        } catch (err) {
            console.error("Error loading sample templates:", err);
        }
    }

    function renderTemplatesLibrary() {
        if (!templatesLibraryGrid) return;
        templatesLibraryGrid.innerHTML = "";

        Object.keys(sampleTemplates).forEach(catKey => {
            const cat = sampleTemplates[catKey];
            (cat.templates || []).forEach(tpl => {
                const card = document.createElement("div");
                card.className = "template-library-card";
                card.innerHTML = `
                    <div>
                        <div class="tpl-header">
                            <span class="tpl-name">${escapeHTML(tpl.name)}</span>
                            <span class="schedule-cat-badge" style="font-size: 10px;">${escapeHTML(cat.title)}</span>
                        </div>
                        <div class="tpl-text mt-2">${escapeHTML(tpl.text)}</div>
                    </div>
                    <button type="button" class="btn-use-tpl" onclick="window.useTemplateFromLibrary('${catKey}', '${tpl.id}')">
                        Use Template ➔
                    </button>
                `;
                templatesLibraryGrid.appendChild(card);
            });
        });
    }

    window.useTemplateFromLibrary = function(catKey, tplId) {
        const cat = sampleTemplates[catKey];
        if (!cat) return;
        const tpl = (cat.templates || []).find(t => t.id === tplId);
        if (!tpl) return;

        openCreateScheduleTab();
        schedCategory.value = catKey;
        schedTitle.value = tpl.name;
        schedMessageText.value = tpl.text;
        
        // Recommended frequency
        const recType = cat.default_type || "daily";
        const radio = document.querySelector(`input[name='sched-type'][value='${recType}']`);
        if (radio) radio.checked = true;
        
        if (schedTimePicker && cat.default_time) {
            schedTimePicker.value = cat.default_time;
        }

        handleScheduleTypeChange();
        updateScheduleLivePreview();
        switchSchedulesTab("tab-schedules-create");
    };

    function loadCategoryTemplateIntoForm(catKey) {
        const cat = sampleTemplates[catKey];
        if (!cat || !cat.templates || cat.templates.length === 0) return;
        const tpl = cat.templates[0];

        schedCategory.value = catKey;
        if (!schedTitle.value || schedTitle.value === "Untitled Schedule") {
            schedTitle.value = tpl.name;
        }
        schedMessageText.value = tpl.text;

        const recType = cat.default_type || "daily";
        const radio = document.querySelector(`input[name='sched-type'][value='${recType}']`);
        if (radio) radio.checked = true;
        if (schedTimePicker && cat.default_time) {
            schedTimePicker.value = cat.default_time;
        }

        handleScheduleTypeChange();
        updateScheduleLivePreview();
    }

    function handleScheduleTypeChange() {
        const selected = document.querySelector("input[name='sched-type']:checked")?.value || "annual";
        if (groupAnnualDate) groupAnnualDate.style.display = selected === "annual" ? "block" : "none";
        if (groupOnceDatetime) groupOnceDatetime.style.display = selected === "once" ? "block" : "none";
        if (groupTimeOfDay) groupTimeOfDay.style.display = selected !== "once" ? "block" : "none";
        if (groupWeeklyDays) groupWeeklyDays.style.display = selected === "weekly" ? "block" : "none";
    }

    function insertScheduleVariable(varTag) {
        if (!schedMessageText) return;
        const start = schedMessageText.selectionStart || 0;
        const end = schedMessageText.selectionEnd || 0;
        const text = schedMessageText.value;
        schedMessageText.value = text.substring(0, start) + varTag + text.substring(end);
        schedMessageText.focus();
        schedMessageText.selectionStart = schedMessageText.selectionEnd = start + varTag.length;
        updateScheduleLivePreview();
    }

    function updateScheduleLivePreview() {
        if (!schedLivePreview || !schedMessageText) return;
        const raw = schedMessageText.value || "Type message above...";
        
        let recipientName = "Friend";
        if (schedRecipientSelect && schedRecipientSelect.value) {
            const contact = contacts.find(c => c.jid === schedRecipientSelect.value);
            if (contact) recipientName = getChatDisplayName(contact);
        } else if (schedCustomTarget && schedCustomTarget.value) {
            recipientName = schedCustomTarget.value.trim();
        }

        const now = new Date();
        const dateStr = now.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dayStr = now.toLocaleDateString([], { weekday: 'long' });

        let rendered = raw.replace(/{name}/g, recipientName)
                          .replace(/{date}/g, dateStr)
                          .replace(/{time}/g, timeStr)
                          .replace(/{day}/g, dayStr);

        schedLivePreview.textContent = rendered;
    }

    function openCreateScheduleTab(prefillTarget = "", prefillName = "") {
        if (schedEditId) schedEditId.value = "";
        if (formSchedule) formSchedule.reset();
        populateContactsDropdown();

        if (prefillTarget) {
            let matched = false;
            if (schedRecipientSelect) {
                for (let i = 0; i < schedRecipientSelect.options.length; i++) {
                    if (schedRecipientSelect.options[i].value === prefillTarget) {
                        schedRecipientSelect.selectedIndex = i;
                        matched = true;
                        break;
                    }
                }
                if (!matched) {
                    const opt = document.createElement("option");
                    opt.value = prefillTarget;
                    opt.textContent = `${prefillName || prefillTarget} (Selected Chat)`;
                    schedRecipientSelect.appendChild(opt);
                    schedRecipientSelect.value = prefillTarget;
                }
            }
            if (schedCustomTarget) {
                schedCustomTarget.value = prefillName || prefillTarget.split('@')[0];
            }
        }

        // Default to Birthday template or morning
        loadCategoryTemplateIntoForm("birthday");
        if (prefillTarget && schedTitle) {
            schedTitle.value = `Greeting to ${prefillName || 'Contact'}`;
        }
        handleScheduleTypeChange();
        updateScheduleLivePreview();
        switchSchedulesTab("tab-schedules-create");
    }

    function handleChatScheduleClick() {
        const contact = contacts.find(c => c.jid === activeContactJid);
        const name = contact ? getChatDisplayName(contact) : (activeContactJid ? activeContactJid.split('@')[0] : "");
        openSchedulesModal("tab-schedules-create");
        openCreateScheduleTab(activeContactJid, name);
    }

    async function handleSaveSchedule(e) {
        if (e && e.preventDefault) e.preventDefault();

        const editId = schedEditId ? schedEditId.value.trim() : "";
        const title = schedTitle ? schedTitle.value.trim() : "";
        if (!title) {
            showSecurityToast("Please enter a schedule title.", "warning");
            if (schedTitle) schedTitle.focus();
            return;
        }

        const messageTemplate = schedMessageText ? schedMessageText.value.trim() : "";
        if (!messageTemplate) {
            showSecurityToast("Please enter message content.", "warning");
            if (schedMessageText) schedMessageText.focus();
            return;
        }

        const category = schedCategory?.value || "custom";
        const schedType = document.querySelector("input[name='sched-type']:checked")?.value || "annual";
        const timeOfDay = schedTimePicker ? schedTimePicker.value : "09:00";
        const annualMonth = schedAnnualMonth ? parseInt(schedAnnualMonth.value) : 1;
        const annualDay = schedAnnualDay ? parseInt(schedAnnualDay.value) : 1;
        const schedDatetime = schedDatetimePicker ? schedDatetimePicker.value : "";
        const enabled = schedEnabled ? schedEnabled.checked : true;

        const daysOfWeek = [];
        document.querySelectorAll("input[name='sched-day']:checked").forEach(cb => {
            daysOfWeek.push(parseInt(cb.value));
        });

        // Determine recipient(s)
        const recipients = [];
        if (schedRecipientSelect && schedRecipientSelect.value) {
            const contact = contacts.find(c => c.jid === schedRecipientSelect.value);
            recipients.push({
                jid: schedRecipientSelect.value,
                name: contact ? getChatDisplayName(contact) : schedRecipientSelect.value.split('@')[0]
            });
        } else if (schedCustomTarget && schedCustomTarget.value.trim()) {
            recipients.push({
                phone: schedCustomTarget.value.trim(),
                name: schedCustomTarget.value.trim()
            });
        }

        const payload = {
            title,
            category,
            schedule_type: schedType,
            time_of_day: timeOfDay,
            annual_month: annualMonth,
            annual_day: annualDay,
            scheduled_datetime: schedDatetime,
            days_of_week: daysOfWeek,
            account_id: activeAccountId || "any",
            recipients,
            message_template: messageTemplate,
            enabled
        };

        if (btnSaveSchedule) {
            btnSaveSchedule.disabled = true;
            btnSaveSchedule.textContent = "💾 Saving...";
        }

        try {
            const url = editId ? `/api/schedules/${editId}` : "/api/schedules";
            const method = editId ? "PUT" : "POST";
            const res = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showSecurityToast(editId ? "Schedule updated successfully!" : "Schedule created successfully!", "info");
                if (schedEditId) schedEditId.value = "";
                if (formSchedule) formSchedule.reset();
                switchSchedulesTab("tab-schedules-list");
                await loadSchedules();
            } else {
                showSecurityToast("Error saving schedule: " + (data.error || "Unknown error"), "danger");
            }
        } catch (err) {
            console.error("Error saving schedule:", err);
            showSecurityToast("Failed to save schedule: " + err.message, "danger");
        } finally {
            if (btnSaveSchedule) {
                btnSaveSchedule.disabled = false;
                btnSaveSchedule.textContent = "💾 Save Schedule";
            }
        }
    }

    window.handleToggleSchedule = async function(schedId, currentVal) {
        try {
            const res = await fetch(`/api/schedules/${schedId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled: !currentVal })
            });
            const data = await res.json();
            if (data.success) {
                await loadSchedules();
            }
        } catch (err) {
            console.error("Error toggling schedule:", err);
        }
    };

    window.handleDeleteSchedule = async function(schedId) {
        const ok = await showConfirmDialog(
            "Delete Scheduled Message",
            "Are you sure you want to permanently delete this scheduled message?",
            "Delete Schedule",
            true
        );
        if (!ok) return;

        try {
            showSecurityToast("Deleting schedule...", "info");
            const res = await fetch(`/api/schedules/${schedId}`, { method: "DELETE" });
            const data = await res.json();
            if (data.success) {
                showSecurityToast("Schedule deleted successfully.", "info");
                await loadSchedules();
            } else {
                showSecurityToast("Failed to delete schedule: " + (data.error || "Unknown error"), "danger");
            }
        } catch (err) {
            console.error("Error deleting schedule:", err);
            showSecurityToast("Error deleting schedule: " + err.message, "danger");
        }
    };

    window.handleTestSendSchedule = async function(schedId) {
        try {
            showSecurityToast("Sending test message...", "info");
            const res = await fetch(`/api/schedules/${schedId}/test`, { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showSecurityToast(`Test message sent successfully (${data.sent_count} delivered)!`, "info");
                await loadSchedules();
            } else {
                alert("Error sending test: " + (data.error || "Failed"));
            }
        } catch (err) {
            console.error("Error sending test:", err);
            alert("Error sending test: " + err.message);
        }
    };

    window.handleEditSchedule = function(schedId) {
        const sched = schedules.find(s => s.id === schedId);
        if (!sched) return;

        openCreateScheduleTab();
        schedEditId.value = sched.id;
        schedTitle.value = sched.title || "";
        schedCategory.value = sched.category || "custom";
        schedMessageText.value = sched.message_template || "";
        if (schedEnabled) schedEnabled.checked = Boolean(sched.enabled);

        // Recurrence
        const radio = document.querySelector(`input[name='sched-type'][value='${sched.schedule_type || 'annual'}']`);
        if (radio) radio.checked = true;

        if (schedTimePicker && sched.time_of_day) schedTimePicker.value = sched.time_of_day;
        if (schedAnnualMonth && sched.annual_month) schedAnnualMonth.value = sched.annual_month;
        if (schedAnnualDay && sched.annual_day) schedAnnualDay.value = sched.annual_day;
        if (schedDatetimePicker && sched.scheduled_datetime) schedDatetimePicker.value = sched.scheduled_datetime;

        // Recipient
        if (sched.recipients && sched.recipients.length > 0) {
            const r = sched.recipients[0];
            if (r.jid && schedRecipientSelect) {
                schedRecipientSelect.value = r.jid;
            } else if (r.phone && schedCustomTarget) {
                schedCustomTarget.value = r.phone;
            }
        }

        handleScheduleTypeChange();
        updateScheduleLivePreview();
        switchSchedulesTab("tab-schedules-create");
    };

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
