/* ============================================================
   Bookshop — общий JS: auth, api-клиент, пагинация, ui-хелперы
   ============================================================ */
"use strict";

const API = document.documentElement.dataset.apiPrefix || "/api";

/* ---------- auth / tokens ---------- */

/* Витрина и панель менеджера — разные области авторизации: у каждой свой
   ключ в localStorage и своя роль. Токен менеджера на витрину не попадает. */
const IS_MANAGER_SCOPE = document.documentElement.dataset.tokenScope === "manager";
const TOKEN_KEY = IS_MANAGER_SCOPE ? "manager_access_token" : "access_token";
const SCOPE_ROLE = IS_MANAGER_SCOPE ? "authorized_manager" : "authorized_user";

/** Роль из payload access-токена. Только для UI — подпись проверяет бэкенд. */
function tokenRole(token) {
    try {
        const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
        return JSON.parse(atob(padded)).role ?? null;
    } catch {
        return null;
    }
}

const isScopeToken = (t) => !!t && tokenRole(t) === SCOPE_ROLE;

/* Токен чужой роли (или выданный до разделения областей) считаем отсутствующим. */
const getToken = () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && !isScopeToken(token)) {
        localStorage.removeItem(TOKEN_KEY);
        return null;
    }
    return token;
};
const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/* CSRF double-submit: бэкенд ставит нечитаемый httponly refresh-cookie и
   parallel-cookie csrf_token (обычный, читаемый). Значение csrf_token эхом
   отправляем в заголовке X-CSRF-Token на cookie-эндпоинты (refresh/logout). */
const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";
const UNSAFE_METHODS = ["POST", "PUT", "PATCH", "DELETE"];

function getCookie(name) {
    const escaped = name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1");
    const match = document.cookie.match(new RegExp("(?:^|; )" + escaped + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : null;
}

function csrfHeaders(headers = {}) {
    const token = getCookie(CSRF_COOKIE);
    if (token) headers[CSRF_HEADER] = token;
    return headers;
}

let accessTokenRefreshPromise = null;

async function refreshAccessToken() {
    // Refresh-токен ротируется после каждого обмена. Все одновременные
    // потребители страницы должны ждать один запрос, иначе второй запрос
    // может быть воспринят сервером как replay старого refresh-токена.
    if (accessTokenRefreshPromise) return accessTokenRefreshPromise;

    accessTokenRefreshPromise = refreshAccessTokenOnce();

    try {
        return await accessTokenRefreshPromise;
    } finally {
        accessTokenRefreshPromise = null;
    }
}

async function refreshAccessTokenOnce() {
    try {
        const res = await fetch(`${API}/users/token/refresh`, {
            method: "POST",
            credentials: "include",
            headers: csrfHeaders(),
        });
        if (!res.ok) throw new Error("refresh failed");
        const data = await res.json();

        // refresh-cookie у витрины и панели общий: сессия менеджера
        // не должна авторизовать покупателя, и наоборот
        if (!isScopeToken(data.access_token)) {
            clearToken();
            return null;
        }

        setToken(data.access_token);
        return data.access_token;
    } catch {
        clearToken();
        return null;
    }
}

class ApiError extends Error {
    constructor(status, detail) {
        super(typeof detail === "string" ? detail : JSON.stringify(detail));
        this.status = status;
        this.detail = detail;
    }
}

/**
 * fetch к API: JSON, Bearer-токен, авто-refresh при 401 (один retry).
 */
async function apiFetch(path, options = {}, _retry = true) {
    const opts = { credentials: "include", ...options };
    opts.headers = { ...(options.headers || {}) };

    if (opts.json !== undefined) {
        opts.body = JSON.stringify(opts.json);
        opts.headers["Content-Type"] = "application/json";
        delete opts.json;
    }

    const token = getToken();
    if (token) opts.headers["Authorization"] = `Bearer ${token}`;

    // CSRF-заголовок на все изменяющие запросы (для cookie-эндпоинтов —
    // обязателен, для Bearer-эндпоинтов — безвредный defense-in-depth)
    if (UNSAFE_METHODS.includes((opts.method || "GET").toUpperCase())) {
        csrfHeaders(opts.headers);
    }

    const res = await fetch(`${API}${path}`, opts);

    if (res.status === 401 && _retry) {
        const newToken = await refreshAccessToken();
        if (newToken) return apiFetch(path, options, false);
    }

    if (!res.ok) {
        let detail = res.statusText;
        try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
        throw new ApiError(res.status, detail);
    }

    if (res.status === 204) return null;
    return res.json();
}

/** Требует авторизацию: возвращает токен или уводит на /auth. */
async function requireAuth() {
    let token = getToken() || await refreshAccessToken();
    if (!token) {
        const next = encodeURIComponent(location.pathname + location.search);
        location.href = `/auth?next=${next}`;
        return null;
    }
    return token;
}

async function logout(everywhere = false) {
    try {
        await apiFetch(`/users/logout${everywhere ? "/all" : ""}`, { method: "POST" });
    } catch { /* уже разлогинен */ }
    clearToken();
    location.href = "/";
}

/* ---------- ui helpers ---------- */

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const fmtPrice = (v) => new Intl.NumberFormat("ru-RU", {
    style: "currency", currency: "RUB", maximumFractionDigits: 0,
}).format(v);

const fmtDate = (iso) => new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "long", year: "numeric",
});

function toast(message, type = "") {
    let wrap = document.querySelector(".toast-wrap");
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "toast-wrap";
        document.body.appendChild(wrap);
    }
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    wrap.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

function showSkeletons(container, count = 8) {
    container.innerHTML = Array.from(
        { length: count },
        () => '<div class="skeleton skeleton-card"></div>',
    ).join("");
}

function emptyState(icon, text) {
    return `<div class="empty-state"><div class="icon">${icon}</div><p>${esc(text)}</p></div>`;
}

/** Стабильный seed сессии для random cursor-пагинации. */
function getSeed(key = "pagination_seed") {
    let seed = sessionStorage.getItem(key);
    if (!seed) {
        seed = Array.from(crypto.getRandomValues(new Uint8Array(8)))
            .map((b) => b.toString(16).padStart(2, "0")).join("");
        sessionStorage.setItem(key, seed);
    }
    return seed;
}

/* ---------- карточка книги ---------- */

function bookCard(book) {
    const author = book.author?.name ?? "";
    const cover = book.img
        ? `<img src="${esc(book.img)}" alt="${esc(book.title)}" loading="lazy">`
        : "📖";
    const discount = book.discount_percent
        ? `<span class="badge badge-discount">−${book.discount_percent}%</span>`
        : "";
    const rating = book.rating
        ? `<span class="rating">★ ${Number(book.rating).toFixed(1)}</span>`
        : "";
    const availability = book.is_available === false
        ? '<span class="badge badge-warn">Нет в наличии</span>'
        : "";
    const category = book.category
        ? `<span class="book-category">${esc(book.category)}</span>`
        : "";

    return `
    <article class="book-card" data-book-id="${book.id}">
        ${discount}
        <a href="/books/${esc(book.slug)}" class="book-cover">${cover}</a>
        <div class="book-body">
            ${category}
            <a href="/books/${esc(book.slug)}" class="book-title">${esc(book.title)}</a>
            <span class="book-author">${esc(author)}</span>
            <div class="book-meta">
                <span class="book-price">${fmtPrice(book.price)}</span>
                ${rating} ${availability}
            </div>
        </div>
        <div class="book-actions">
            <button class="btn btn-sm" data-cart-btn onclick="addToCart(${book.id})">🧺 В корзину</button>
            <button class="btn-ghost btn btn-sm" data-wish-btn onclick="addToWishlist(${book.id})" title="В избранное">❤️</button>
        </div>
    </article>`;
}

/* ---------- состояние «в корзине / в избранном» ---------- */

/* Множества id книг, которые уже в корзине и в избранном у пользователя. */
const userLists = { cart: new Set(), wishlist: new Set(), loaded: false };

/** Загружает корзину и избранное пользователя (один раз за сессию страницы). */
async function loadUserLists(force = false) {
    if (!getToken()) {
        userLists.cart.clear();
        userLists.wishlist.clear();
        userLists.loaded = true;
        return userLists;
    }
    if (userLists.loaded && !force) return userLists;

    const [cart, wish] = await Promise.all([
        apiFetch("/books/cart/by/user").catch(() => ({ items: [] })),
        apiFetch("/books/wishlist/by/user").catch(() => []),
    ]);

    userLists.cart = new Set((cart.items || []).map((i) => i.book.id));
    userLists.wishlist = new Set((wish || []).map((b) => b.id));
    userLists.loaded = true;
    return userLists;
}

/* textContent пишем только при изменении — иначе MutationObserver зациклится. */
const setText = (el, text) => { if (el.textContent !== text) el.textContent = text; };

/** Приводит одну кнопку «в корзину» к нужному состоянию. */
function setCartBtnState(btn, inCart) {
    if (!btn.dataset.label) btn.dataset.label = btn.textContent.trim();
    btn.classList.toggle("in-cart", inCart);
    setText(btn, inCart ? "✓ В корзине" : btn.dataset.label);
    btn.title = inCart ? "Книга уже в корзине" : "";
}

/** Приводит одну кнопку «в избранное» к нужному состоянию. */
function setWishBtnState(btn, inWish) {
    if (!btn.dataset.label) btn.dataset.label = btn.textContent.trim();
    const full = btn.hasAttribute("data-full");
    btn.classList.toggle("in-wishlist", inWish);
    btn.disabled = inWish;
    if (inWish) {
        setText(btn, full ? "❤️ В избранном" : "❤️");
        btn.title = "Уже в избранном";
    } else {
        setText(btn, btn.dataset.label);
        btn.title = full ? "" : "В избранное";
    }
}

/** Обновляет все кнопки в области scope по текущему userLists. */
function applyBookStates(scope = document) {
    scope.querySelectorAll("[data-book-id]").forEach((el) => {
        const id = Number(el.dataset.bookId);
        if (!id) return;
        const cartBtn = el.querySelector("[data-cart-btn]");
        const wishBtn = el.querySelector("[data-wish-btn]");
        if (cartBtn) setCartBtnState(cartBtn, userLists.cart.has(id));
        if (wishBtn) setWishBtnState(wishBtn, userLists.wishlist.has(id));
    });
}

async function addToCart(bookId) {
    if (!await requireAuth()) return;
    try {
        await apiFetch(`/books/cart?book_id=${bookId}`, { method: "POST" });
        userLists.cart.add(Number(bookId));
        applyBookStates();
        toast("Книга добавлена в корзину", "success");
    } catch (e) {
        toast(e.message, "error");
    }
}

async function addToWishlist(bookId) {
    if (!await requireAuth()) return;
    try {
        await apiFetch(`/books/wishlist?book_id=${bookId}`, { method: "POST" });
        userLists.wishlist.add(Number(bookId));
        applyBookStates();
        toast("Книга добавлена в избранное", "success");
    } catch (e) {
        // 409 — книга уже в избранном: это не ошибка, просто синхронизируем UI
        if (e.status === 409) {
            userLists.wishlist.add(Number(bookId));
            applyBookStates();
            toast("Книга уже в избранном", "");
        } else {
            toast(e.message, "error");
        }
    }
}

/* ---------- cursor-пагинация (бесконечный скролл) ---------- */

const SCROLL_MARGIN = 600; // за сколько px до сентинела подгружать

/**
 * Универсальный cursor-пейджер с автоподгрузкой при скролле.
 * cfg.fetchPage(cursor) -> {items, next, hasNext}
 * cfg.render(items, isFirstPage)
 * cfg.sentinel — пустой элемент в конце списка, по видимости которого грузим ещё
 */
function createCursorPager(cfg) {
    const sentinel = cfg.sentinel;
    let cursor = null;
    let loading = false;
    let first = true;
    let done = false;
    let observer = null;

    const sentinelVisible = () => {
        if (!sentinel || sentinel.hidden) return false;
        const r = sentinel.getBoundingClientRect();
        // display:none / ещё не отрисованный элемент даёт нулевой бокс —
        // такой сентинел «видимым» не считаем (иначе — ложная догрузка)
        if (r.width === 0 && r.height === 0) return false;
        return r.top < window.innerHeight + SCROLL_MARGIN && r.bottom > -SCROLL_MARGIN;
    };

    async function loadNext() {
        if (loading || done) return;
        loading = true;
        if (sentinel) sentinel.classList.add("loading");

        let ok = false;
        try {
            const page = await cfg.fetchPage(cursor);
            cfg.render(page.items, first);
            first = false;
            cursor = page.next;
            ok = true;
            if (!page.hasNext || !page.items.length) finish();
        } catch (e) {
            // Ошибку показываем как есть, но пейджер НЕ выключаем и курсор
            // НЕ теряем. 429 «slow down» лимитирует только создание НОВЫХ
            // сессий ленты — продолжение по курсору сервер не ограничивает.
            // observer остаётся активным, поэтому следующий скролл корректно
            // продолжит cursor-пагинацию с того же места.
            toast(e.message, "error");
        } finally {
            loading = false;
            if (sentinel) sentinel.classList.remove("loading");
        }

        // после УСПЕШНОЙ страницы догружаем, пока сентинел в зоне видимости.
        // На ошибке (ok=false) авто-цепочки нет — ждём реального скролла,
        // иначе получили бы шторм повторных запросов.
        if (ok && !done && sentinelVisible()) await loadNext();
    }

    function start() {
        if (!sentinel || observer) return;
        observer = new IntersectionObserver((entries) => {
            if (entries.some((e) => e.isIntersecting)) loadNext();
        }, { rootMargin: `${SCROLL_MARGIN}px 0px` });
        observer.observe(sentinel);
    }

    function stop() {
        if (observer) { observer.disconnect(); observer = null; }
    }

    function finish() {
        done = true;
        stop();
        if (sentinel) sentinel.hidden = true;
    }

    start();

    return {
        loadNext,
        reset() {
            cursor = null;
            first = true;
            done = false;
            if (sentinel) sentinel.hidden = false;
            stop();
            start();
        },
    };
}

/* ---------- offset-пагинация (номера страниц) ---------- */

/**
 * Рисует номерные кнопки страниц в container.
 * meta: {page, pages, total} — из PagePaginationRESP.
 */
function renderPagination(container, meta, onPage) {
    container.innerHTML = "";
    if (meta.pages <= 1) return;

    const btn = (label, page, { active = false, disabled = false } = {}) => {
        const b = document.createElement("button");
        b.className = `page-btn${active ? " active" : ""}`;
        b.textContent = label;
        b.disabled = disabled || active;
        if (!disabled && !active) b.addEventListener("click", () => onPage(page));
        return b;
    };

    container.appendChild(btn("‹", meta.page - 1, { disabled: meta.page <= 1 }));

    // окно страниц: 1 … p-1 p p+1 … N
    const windowPages = new Set([
        1, meta.pages,
        meta.page - 1, meta.page, meta.page + 1,
    ]);
    let prev = 0;
    for (let p = 1; p <= meta.pages; p++) {
        if (!windowPages.has(p)) continue;
        if (p - prev > 1) {
            const dots = document.createElement("span");
            dots.className = "page-info";
            dots.textContent = "…";
            container.appendChild(dots);
        }
        container.appendChild(btn(String(p), p, { active: p === meta.page }));
        prev = p;
    }

    container.appendChild(btn("›", meta.page + 1, { disabled: meta.page >= meta.pages }));

    const info = document.createElement("span");
    info.className = "page-info";
    info.textContent = `всего: ${meta.total}`;
    container.appendChild(info);
}

/* ---------- навигация: состояние авторизации ---------- */

document.addEventListener("DOMContentLoaded", async () => {
    // OAuth callback сохраняет refresh-cookie и перенаправляет на главную.
    // До отрисовки шапки восстанавливаем access-токен из этой cookie.
    const token = getToken() || await refreshAccessToken();

    const authSlot = document.getElementById("nav-auth");
    if (authSlot) {
        if (token) {
            authSlot.innerHTML = '<button class="btn btn-ghost btn-sm" id="nav-logout">Выйти</button>';
            document.getElementById("nav-logout").addEventListener("click", () => logout());
        } else {
            authSlot.innerHTML = '<a class="btn btn-sm" href="/auth">Войти</a>';
        }
    }

    // подсветка активного пункта меню
    document.querySelectorAll(".nav-links a").forEach((a) => {
        if (a.getAttribute("href") === location.pathname) a.classList.add("active");
    });

    // отметки «в корзине / в избранном»: грузим списки и применяем к карточкам,
    // в т.ч. к тем, что подгружаются пагинацией (MutationObserver)
    const main = document.querySelector("main") || document.body;
    let applyScheduled = false;
    const scheduleApply = () => {
        if (applyScheduled) return;
        applyScheduled = true;
        requestAnimationFrame(() => {
            applyScheduled = false;
            applyBookStates(main);
        });
    };

    new MutationObserver(scheduleApply).observe(main, {
        childList: true,
        subtree: true,
    });

    loadUserLists()
        .then(() => applyBookStates(main))
        .catch(() => { /* не критично */ });
});
