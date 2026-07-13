/* ============================================================
   Bookshop — плавающий чат-виджет: ИИ консультант (SSE) + поддержка (WS)
   ============================================================ */
"use strict";

(() => {
    /* на странице входа и в панели менеджера виджет не нужен */
    if (location.pathname.startsWith("/auth") ||
        location.pathname.startsWith("/support/manager")) return;

    /* ---------- разметка ---------- */

    const root = document.createElement("div");
    root.className = "chat-widget";
    root.innerHTML = `
        <div class="cw-panel" hidden>
            <div class="cw-head">
                <div class="cw-tabs">
                    <button class="cw-tab active" data-tab="agent">🤖 Консультант</button>
                    <button class="cw-tab" data-tab="support">💬 Поддержка</button>
                </div>
                <span class="chat-status" data-role="status"></span>
            </div>

            <div class="cw-pane" data-pane="agent">
                <div class="cw-body" data-role="agent-body">
                    <div class="msg msg-system">Спросите совета — например: «посоветуй фантастику на вечер»</div>
                </div>
                <div class="cw-input-row">
                    <input class="form-input" data-role="agent-input" placeholder="Ваш вопрос…" maxlength="2000">
                    <button class="btn" data-role="agent-send" title="Отправить">➤</button>
                </div>
            </div>

            <div class="cw-pane" data-pane="support" hidden>
                <div class="cw-body" data-role="support-body"></div>
                <div class="cw-input-row">
                    <input class="form-input" data-role="support-input" placeholder="Напишите сообщение…" maxlength="1000">
                    <button class="btn" data-role="support-send" title="Отправить">➤</button>
                    <button class="btn btn-ghost" data-role="support-close" title="Завершить чат">✕</button>
                </div>
            </div>
        </div>

        <button class="cw-fab" title="Чат: консультант и поддержка">
            <span data-role="fab-icon">💬</span>
            <span class="cw-fab-dot" data-role="fab-dot" hidden></span>
        </button>
    `;
    document.body.appendChild(root);

    const $ = (sel) => root.querySelector(sel);
    const panel = $(".cw-panel");
    const fab = $(".cw-fab");
    const fabIcon = $('[data-role="fab-icon"]');
    const fabDot = $('[data-role="fab-dot"]');
    const statusEl = $('[data-role="status"]');

    const panes = {
        agent: {
            el: $('[data-pane="agent"]'),
            body: $('[data-role="agent-body"]'),
            input: $('[data-role="agent-input"]'),
            send: $('[data-role="agent-send"]'),
            status: { text: "", cls: "" },
            loginShown: false,
        },
        support: {
            el: $('[data-pane="support"]'),
            body: $('[data-role="support-body"]'),
            input: $('[data-role="support-input"]'),
            send: $('[data-role="support-send"]'),
            status: { text: "офлайн", cls: "off" },
            loginShown: false,
            ws: null,
        },
    };

    let isOpen = false;
    let activeTab = "agent";
    let authed = null; // null — ещё не проверяли

    /* ---------- общие хелперы ---------- */

    const scrollPane = (pane) => { pane.body.scrollTop = pane.body.scrollHeight; };

    function addMsg(pane, cls, text = "") {
        const el = document.createElement("div");
        el.className = `msg ${cls}`;
        el.textContent = text;
        pane.body.appendChild(el);
        scrollPane(pane);
        return el;
    }

    function setStatus(tab, text, cls = "") {
        panes[tab].status = { text, cls };
        if (tab === activeTab) {
            statusEl.textContent = text;
            statusEl.className = `chat-status ${cls}`;
        }
    }

    /* мягкая проверка авторизации: без редиректа на /auth */
    async function ensureAuth() {
        if (authed === null) {
            authed = Boolean(getToken() || await refreshAccessToken());
        }
        return authed;
    }

    function showLoginPrompt(pane) {
        if (pane.loginShown) return;
        pane.loginShown = true;
        const next = encodeURIComponent(location.pathname + location.search);
        const el = document.createElement("div");
        el.className = "msg msg-system";
        el.innerHTML = `Чтобы написать в чат, <a href="/auth?next=${next}">войдите в аккаунт</a>`;
        pane.body.appendChild(el);
        pane.input.disabled = true;
        pane.send.disabled = true;
    }

    /* ---------- консультант (SSE-стрим) ---------- */

    /* разбор text/event-stream из fetch-стрима */
    async function streamChat(message, onEvent, _retry = true) {
        const res = await fetch(`${API}/agent/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${getToken()}`,
            },
            credentials: "include",
            body: JSON.stringify({ message }),
        });

        if (res.status === 401 && _retry && await refreshAccessToken()) {
            return streamChat(message, onEvent, false);
        }

        if (!res.ok) {
            let detail = res.statusText;
            try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
            throw new Error(detail);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        /* SSE-спека: после "event:"/"data:" убирается ровно один пробел */
        const clean = (s) => s.startsWith(" ") ? s.slice(1) : s;

        for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            // sse_starlette разделяет строки через \r\n — нормализуем
            buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

            let idx;
            while ((idx = buffer.indexOf("\n\n")) !== -1) {
                const raw = buffer.slice(0, idx);
                buffer = buffer.slice(idx + 2);

                let event = "message";
                const dataLines = [];
                for (const line of raw.split("\n")) {
                    if (line.startsWith("event:")) event = clean(line.slice(6));
                    else if (line.startsWith("data:")) dataLines.push(clean(line.slice(5)));
                }
                onEvent(event, dataLines.join("\n"));
            }
        }
    }

    async function agentSend() {
        const pane = panes.agent;
        const text = pane.input.value.trim();
        if (!text || pane.send.disabled) return;

        addMsg(pane, "msg-user", text);
        pane.input.value = "";
        pane.send.disabled = true;
        setStatus("agent", "думает…", "on");

        const answer = addMsg(pane, "msg-other", "…");
        let acc = "";
        const asJson = (s) => { try { return JSON.parse(s); } catch { return null; } };

        try {
            await streamChat(text, (event, data) => {
                if (event === "token") {
                    acc += data;
                    answer.textContent = acc;
                    scrollPane(pane);
                } else if (event === "tool") {
                    const name = asJson(data)?.name;
                    setStatus("agent", name ? `🔧 ${name}` : "🔧 использует инструмент…", "on");
                } else if (event === "done") {
                    const full = asJson(data)?.answer;
                    if (full) answer.textContent = full;
                } else if (event === "error") {
                    answer.textContent = asJson(data)?.message ?? `Ошибка: ${data}`;
                }
            });
        } catch (e) {
            answer.textContent = `Ошибка: ${e.message}`;
        } finally {
            pane.send.disabled = false;
            setStatus("agent", "");
            scrollPane(pane);
        }
    }

    /* ---------- поддержка (WebSocket) ---------- */

    function addSupportMsg({ sender, content }, { system = false } = {}) {
        const pane = panes.support;
        if (system) {
            addMsg(pane, "msg-system", content);
            return;
        }
        const mine = sender === "user";
        const el = document.createElement("div");
        el.className = `msg ${mine ? "msg-user" : "msg-other"}`;
        if (!mine) {
            const label = { bot: "🤖 Бот", manager: "👤 Оператор" }[sender] ?? sender;
            el.innerHTML = `<div class="msg-sender">${esc(label)}</div>`;
        }
        el.appendChild(document.createTextNode(content));
        pane.body.appendChild(el);
        scrollPane(pane);
    }

    function supportConnect() {
        const pane = panes.support;
        // CONNECTING / OPEN — соединение уже есть
        if (pane.ws && pane.ws.readyState <= WebSocket.OPEN) return;

        const proto = location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(`${proto}://${location.host}${API}/support/ws?token=${encodeURIComponent(getToken())}`);
        pane.ws = ws;

        ws.onopen = () => setStatus("support", "онлайн", "on");

        ws.onmessage = (e) => {
            let payload;
            try { payload = JSON.parse(e.data); } catch { return; }

            switch (payload.type) {
                case "history":
                    pane.body.innerHTML = "";
                    (payload.data?.messages ?? []).forEach((m) => addSupportMsg(m));
                    if (!pane.body.children.length) {
                        addSupportMsg({ content: "Напишите нам — бот ответит мгновенно, а при необходимости подключится оператор." }, { system: true });
                    }
                    break;
                case "message":
                    addSupportMsg(payload.data ?? {});
                    if (!isOpen || activeTab !== "support") fabDot.hidden = false;
                    break;
                case "system":
                    addSupportMsg({ content: String(payload.data ?? "") }, { system: true });
                    break;
                case "error":
                    toast(String(payload.data ?? "Ошибка чата"), "error");
                    break;
            }
        };

        ws.onclose = (e) => {
            setStatus("support", e.reason ? `офлайн — ${e.reason}` : "офлайн", "off");
        };
    }

    function supportSend() {
        const pane = panes.support;
        const text = pane.input.value.trim();
        if (!text || pane.ws?.readyState !== WebSocket.OPEN) return;
        pane.ws.send(text);
        pane.input.value = "";
    }

    /* ---------- вкладки и открытие/закрытие ---------- */

    function selectTab(tab) {
        activeTab = tab;
        root.querySelectorAll(".cw-tab").forEach((b) => {
            b.classList.toggle("active", b.dataset.tab === tab);
        });
        Object.entries(panes).forEach(([name, p]) => { p.el.hidden = name !== tab; });

        const st = panes[tab].status;
        statusEl.textContent = st.text;
        statusEl.className = `chat-status ${st.cls}`;

        if (tab === "support") {
            fabDot.hidden = true;
            if (authed) supportConnect();
        }
        if (authed && !panes[tab].input.disabled) panes[tab].input.focus();
    }

    async function toggle(open = !isOpen) {
        isOpen = open;
        panel.hidden = !open;
        fabIcon.textContent = open ? "✕" : "💬";
        if (!open) return;

        if (await ensureAuth()) {
            if (activeTab === "support") supportConnect();
            panes[activeTab].input.focus();
        } else {
            showLoginPrompt(panes.agent);
            showLoginPrompt(panes.support);
        }
        if (activeTab === "support") fabDot.hidden = true;
    }

    /* ---------- события ---------- */

    fab.addEventListener("click", () => toggle());

    root.querySelectorAll(".cw-tab").forEach((b) => {
        b.addEventListener("click", () => selectTab(b.dataset.tab));
    });

    panes.agent.send.addEventListener("click", agentSend);
    panes.agent.input.addEventListener("keydown", (e) => { if (e.key === "Enter") agentSend(); });

    panes.support.send.addEventListener("click", supportSend);
    panes.support.input.addEventListener("keydown", (e) => { if (e.key === "Enter") supportSend(); });

    $('[data-role="support-close"]').addEventListener("click", () => {
        const pane = panes.support;
        if (pane.ws?.readyState === WebSocket.OPEN) {
            pane.ws.send(JSON.stringify({ action: "close" }));
            addSupportMsg({ content: "Чат закрыт" }, { system: true });
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && isOpen) toggle(false);
    });
})();
