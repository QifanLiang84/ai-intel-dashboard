/* 投资·AI产业链每日情报看板 - 前端逻辑 */

const SECTOR_NAMES = {
    computing: "算力与国产替代",
    ai_app: "AI应用",
    physical_ai: "物理AI",
    funding: "投融资",
};

const SECTOR_ICONS = {
    computing: "⚡",
    ai_app: "🧠",
    physical_ai: "🤖",
    funding: "💰",
};

let currentData = null;
let currentNewsSector = "all";
let autoRefreshTimer = null;
const AUTO_REFRESH_INTERVAL = 30 * 60 * 1000;
const LOCAL_SERVER = "http://localhost:8199";

function isLocalServer() {
    return location.hostname === "localhost" || location.hostname === "127.0.0.1";
}

// ====== 数据加载 ======

async function loadData(date) {
    // 优先使用嵌入数据（自包含HTML）
    if (!date && typeof EMBEDDED_DATA !== "undefined") {
        currentData = EMBEDDED_DATA;
        renderAll(EMBEDDED_DATA);
        return EMBEDDED_DATA;
    }
    try {
        let url = "data/latest.json";
        if (date) {
            url = `data/history/${date}.json`;
        }
        const resp = await fetch(url + "?t=" + Date.now());
        if (!resp.ok) throw new Error("Not found");
        const data = await resp.json();
        currentData = data;
        renderAll(data);
        return data;
    } catch (e) {
        console.error("Load data failed:", e);
        // 如果在线模式加载失败，尝试回退嵌入数据
        if (!date && typeof EMBEDDED_DATA !== "undefined") {
            currentData = EMBEDDED_DATA;
            renderAll(EMBEDDED_DATA);
            showToast("网络加载失败，已显示缓存数据");
            return EMBEDDED_DATA;
        }
        renderEmpty();
        return null;
    }
}

// ====== 渲染 ======

function renderAll(data) {
    renderHeader(data);
    renderSummary(data);
    renderSectorGrid(data);
    renderKeywords(data);
    renderNews(data);
    renderPolicy(data);
    renderResearch(data);
    renderCompany(data);
    renderFunding(data);
}

function renderHeader(data) {
    const dateEl = document.getElementById("headerDate");
    dateEl.textContent = `${data.date} ${data.updated_at ? "· 更新于 " + data.updated_at : ""}`;
}

function renderSummary(data) {
    document.getElementById("dailySummary").innerHTML =
        `<p class="summary-text">${escapeHtml(data.daily_summary || "暂无摘要")}</p>`;

    const insightEl = document.getElementById("investmentInsight");
    if (data.investment_insight) {
        insightEl.style.display = "block";
        document.getElementById("insightText").textContent = data.investment_insight;
    }

    const eventsEl = document.getElementById("keyEvents");
    if (data.key_events && data.key_events.length > 0) {
        eventsEl.style.display = "block";
        document.getElementById("eventsList").innerHTML = data.key_events
            .map((e) => `<li>${escapeHtml(e)}</li>`)
            .join("");
    }
}

function renderSectorGrid(data) {
    const news = data.news || {};
    const maxCount = Math.max(
        1,
        ...Object.keys(SECTOR_NAMES)
            .filter((k) => k !== "funding")
            .map((k) => (news[k] || []).length)
    );

    Object.keys(SECTOR_NAMES)
        .filter((k) => k !== "funding")
        .forEach((sector) => {
            const count = (news[sector] || []).length;
            const countEl = document.getElementById("count-" + sector);
            const barEl = document.getElementById("bar-" + sector);
            if (countEl) countEl.textContent = count + " 条";
            if (barEl) barEl.style.width = (count / maxCount) * 100 + "%";
        });

    // 赛道摘要
    document.querySelectorAll(".sector-card").forEach((card) => {
        const sector = card.dataset.sector;
        card.addEventListener("click", () => {
            switchToNewsTab(sector);
        });
        const summary = (data.sector_summaries || {})[sector];
        if (summary) {
            card.title = summary;
        }
    });
}

function renderKeywords(data) {
    const container = document.getElementById("keywordsContainer");
    const keywords = data.keywords || [];
    if (!keywords.length) {
        container.innerHTML = '<div class="empty-state">暂无关键词数据</div>';
        return;
    }
    container.innerHTML = keywords
        .map((kw) => {
            const weightClass = kw.weight >= 5 ? "keyword-weight-5" : kw.weight >= 4 ? "keyword-weight-4" : "";
            const trendClass =
                kw.trend === "up"
                    ? "trend-up"
                    : kw.trend === "down"
                      ? "trend-down"
                      : "trend-stable";
            const trendIcon = kw.trend === "up" ? "▲" : kw.trend === "down" ? "▼" : "━";
            return `<span class="keyword-tag ${weightClass}" data-keyword="${escapeAttr(kw.word)}" data-sector="${kw.sector}" title="点击查看「${escapeHtml(kw.word)}」相关新闻">
                ${escapeHtml(kw.word)}
                <span class="${trendClass}">${trendIcon}</span>
            </span>`;
        })
        .join("");

    // 关键词点击 -> 跳转到对应赛道的新闻并筛选含该关键词的新闻
    container.querySelectorAll(".keyword-tag").forEach((tag) => {
        tag.style.cursor = "pointer";
        tag.addEventListener("click", () => {
            const sector = tag.dataset.sector;
            const keyword = tag.dataset.keyword;
            if (sector) {
                switchToNewsTab(sector);
                // 滚动到新闻区域
                const newsSection = document.querySelector(".main-content");
                if (newsSection) {
                    newsSection.scrollIntoView({ behavior: "smooth", block: "start" });
                }
                // 高亮含关键词的新闻
                setTimeout(() => {
                    document.querySelectorAll(".news-item").forEach((item) => {
                        const titleEl = item.querySelector(".news-item-title");
                        if (titleEl && titleEl.textContent.toLowerCase().includes(keyword.toLowerCase())) {
                            item.style.background = "rgba(49, 130, 206, 0.12)";
                            item.style.borderColor = "var(--accent-blue)";
                        } else {
                            item.style.background = "";
                            item.style.borderColor = "";
                        }
                    });
                }, 100);
            }
        });
    });
}

function renderNews(data) {
    const news = data.news || {};

    // 渲染赛道子Tab
    const tabsContainer = document.getElementById("newsSectorTabs");
    const sectors = ["all", ...Object.keys(SECTOR_NAMES).filter((k) => k !== "funding")];
    tabsContainer.innerHTML = sectors
        .map(
            (s) =>
                `<button class="news-sector-tab ${s === currentNewsSector ? "active" : ""}" data-sector="${s}">
            ${s === "all" ? "全部" : SECTOR_ICONS[s] + " " + SECTOR_NAMES[s]}
        </button>`
        )
        .join("");

    tabsContainer.querySelectorAll(".news-sector-tab").forEach((btn) => {
        btn.addEventListener("click", () => {
            currentNewsSector = btn.dataset.sector;
            tabsContainer.querySelectorAll(".news-sector-tab").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            renderNewsList(news);
        });
    });

    renderNewsList(news);
}

function renderNewsList(news) {
    const listEl = document.getElementById("newsList");
    let items = [];

    if (currentNewsSector === "all") {
        Object.keys(SECTOR_NAMES)
            .filter((k) => k !== "funding")
            .forEach((sector) => {
                (news[sector] || []).forEach((n) => items.push({ ...n, sector }));
            });
    } else {
        items = (news[currentNewsSector] || []).map((n) => ({
            ...n,
            sector: currentNewsSector,
        }));
    }

    if (!items.length) {
        listEl.innerHTML = '<div class="empty-state">暂无新闻数据</div>';
        return;
    }

    listEl.innerHTML = items
        .slice(0, 50)
        .map(
            (item) => `
        <div class="news-item">
            <div class="news-item-source">${escapeHtml(item.source)}</div>
            <div class="news-item-body">
                <a class="news-item-title" href="${escapeAttr(item.url)}" target="_blank" rel="noopener">
                    ${escapeHtml(item.title)}
                </a>
                <div class="news-item-meta">
                    <span class="news-item-sector">${SECTOR_NAMES[item.sector] || item.sector}</span>
                    <span>${escapeHtml(item.date || "")}</span>
                </div>
            </div>
        </div>
    `
        )
        .join("");
}

function renderPolicy(data) {
    const listEl = document.getElementById("policyList");
    const items = data.policy || [];
    if (!items.length) {
        listEl.innerHTML = '<div class="empty-state">暂无政策数据</div>';
        return;
    }
    listEl.innerHTML = items
        .map(
            (item) => `
        <div class="news-item">
            <div class="news-item-source">${escapeHtml(item.source)}</div>
            <div class="news-item-body">
                <a class="news-item-title" href="${escapeAttr(item.url)}" target="_blank" rel="noopener">
                    ${escapeHtml(item.title)}
                </a>
                <div class="news-item-meta">
                    <span class="news-item-sector">${SECTOR_NAMES[item.sector] || "政策"}</span>
                    <span>${escapeHtml(item.date || "")}</span>
                </div>
            </div>
        </div>
    `
        )
        .join("");
}

function renderResearch(data) {
    const listEl = document.getElementById("researchList");
    const highlights = data.research_highlights || [];
    const researchNews = [];
    (data.news || {});
    Object.values(data.news || {}).forEach((items) => {
        items.forEach((n) => {
            if (n.category === "research") researchNews.push(n);
        });
    });

    if (!highlights.length && !researchNews.length) {
        listEl.innerHTML = '<div class="empty-state">暂无研报数据</div>';
        return;
    }

    let html = "";

    // AI解读的研报
    if (highlights.length) {
        html += highlights
            .map(
                (r) => `
            <div class="research-card">
                <div class="research-card-header">
                    <div class="research-card-title">${escapeHtml(r.title)}</div>
                    <div class="research-card-source">${escapeHtml(r.source)}</div>
                </div>
                ${r.summary ? `<div class="research-card-summary">${escapeHtml(r.summary)}</div>` : ""}
                ${r.key_point ? `<div class="research-card-point">💡 ${escapeHtml(r.key_point)}</div>` : ""}
            </div>
        `
            )
            .join("");
    }

    // 普通研报列表
    if (researchNews.length) {
        html += researchNews
            .filter((n) => !highlights.some((h) => h.title === n.title))
            .slice(0, 10)
            .map(
                (item) => `
            <div class="news-item">
                <div class="news-item-source">${escapeHtml(item.source)}</div>
                <div class="news-item-body">
                    <a class="news-item-title" href="${escapeAttr(item.url)}" target="_blank" rel="noopener">
                        ${escapeHtml(item.title)}
                    </a>
                    <div class="news-item-meta">
                        <span class="news-item-sector">${SECTOR_NAMES[item.sector] || "研报"}</span>
                        <span>${escapeHtml(item.date || "")}</span>
                    </div>
                </div>
            </div>
        `
            )
            .join("");
    }

    listEl.innerHTML = html;
}

function renderCompany(data) {
    const gridEl = document.getElementById("companyGrid");
    const updates = data.company_updates || {};
    const sectorNames = SECTOR_NAMES;

    const hasData = Object.values(updates).some((v) => v && v.length > 0);
    if (!hasData) {
        gridEl.innerHTML = '<div class="empty-state">暂无公司动态数据</div>';
        return;
    }

    gridEl.innerHTML = Object.entries(updates)
        .filter(([, events]) => events && events.length > 0)
        .map(
            ([sector, events]) => `
        <div class="company-sector-group">
            <div class="company-sector-title">
                ${SECTOR_ICONS[sector] || ""} ${sectorNames[sector] || sector}
            </div>
            <div class="company-events">
                ${events
                    .slice(0, 5)
                    .map(
                        (e) => `
                    <div class="company-event">
                        <div class="company-event-name">${escapeHtml(e.name)}</div>
                        <div class="company-event-text">
                            ${e.url ? `<a href="${escapeAttr(e.url)}" target="_blank" rel="noopener" style="color:var(--text-secondary);text-decoration:none;">${escapeHtml(e.event)}</a>` : escapeHtml(e.event)}
                        </div>
                        <div class="company-event-date">${escapeHtml(e.date || "")}</div>
                    </div>
                `
                    )
                    .join("")}
            </div>
        </div>
    `
        )
        .join("");
}

function renderFunding(data) {
    const listEl = document.getElementById("fundingList");
    const items = (data.news || {}).funding || [];
    if (!items.length) {
        listEl.innerHTML = '<div class="empty-state">暂无投融资数据</div>';
        return;
    }
    listEl.innerHTML = items
        .map(
            (item) => `
        <div class="news-item">
            <div class="news-item-source">${escapeHtml(item.source)}</div>
            <div class="news-item-body">
                <a class="news-item-title" href="${escapeAttr(item.url)}" target="_blank" rel="noopener">
                    ${escapeHtml(item.title)}
                </a>
                <div class="news-item-meta">
                    <span>${escapeHtml(item.date || "")}</span>
                </div>
            </div>
        </div>
    `
        )
        .join("");
}

function renderEmpty() {
    document.getElementById("dailySummary").innerHTML =
        '<div class="empty-state">暂无数据，请先运行爬虫: python scraper/main.py</div>';
    document.getElementById("headerDate").textContent = "暂无数据";
}

// ====== Tab 切换 ======

function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            const target = document.getElementById("tab-" + tab.dataset.tab);
            if (target) target.classList.add("active");
        });
    });
}

function switchToNewsTab(sector) {
    // 切换到新闻流tab
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelector('.tab[data-tab="news"]').classList.add("active");
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    document.getElementById("tab-news").classList.add("active");

    // 切换到对应赛道
    currentNewsSector = sector;
    document.querySelectorAll(".news-sector-tab").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.sector === sector);
    });
    if (currentData) {
        renderNewsList(currentData.news || {});
    }
}

// ====== 历史回顾 ======

function initHistory() {
    const modal = document.getElementById("historyModal");
    const btnHistory = document.getElementById("btnHistory");
    const btnClose = document.getElementById("modalClose");

    btnHistory.addEventListener("click", () => {
        modal.style.display = "flex";
        loadHistoryList();
    });
    btnClose.addEventListener("click", () => {
        modal.style.display = "none";
    });
    modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });
}

async function loadHistoryList() {
    const listEl = document.getElementById("historyList");
    listEl.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';

    // 尝试加载最近7天的历史
    const dates = [];
    const today = new Date();
    for (let i = 0; i < 14; i++) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        dates.push(d.toISOString().slice(0, 10));
    }

    const items = [];
    for (const date of dates) {
        try {
            const resp = await fetch(`data/history/${date}.json`);
            if (resp.ok) {
                const data = await resp.json();
                const totalNews = Object.values(data.news || {}).reduce(
                    (sum, arr) => sum + arr.length,
                    0
                );
                items.push({ date, count: totalNews });
            }
        } catch {
            // skip
        }
    }

    if (!items.length) {
        listEl.innerHTML = '<div class="empty-state">暂无历史数据</div>';
        return;
    }

    listEl.innerHTML = items
        .map(
            (item) => `
        <div class="history-item" data-date="${item.date}">
            <div class="history-date">${item.date}</div>
            <div class="history-count">${item.count} 条新闻</div>
        </div>
    `
        )
        .join("");

    listEl.querySelectorAll(".history-item").forEach((el) => {
        el.addEventListener("click", () => {
            loadData(el.dataset.date);
            document.getElementById("historyModal").style.display = "none";
        });
    });
}

// ====== 刷新 ======

function initRefresh() {
    const btnRefresh = document.getElementById("btnRefresh");
    if (!btnRefresh) return;

    btnRefresh.addEventListener("click", () => {
        triggerRefresh();
    });
}

async function triggerRefresh() {
    const btnRefresh = document.getElementById("btnRefresh");
    if (!btnRefresh) return;

    btnRefresh.classList.add("loading");
    btnRefresh.textContent = "🔄 刷新中...";

    try {
        if (isLocalServer()) {
            // 本地模式：尝试触发爬虫
            let serverAvailable = false;
            try {
                const resp = await fetch(LOCAL_SERVER + "/api/refresh", {
                    signal: AbortSignal.timeout(5000),
                });
                if (resp.ok) {
                    serverAvailable = true;
                    const result = await resp.json();
                    if (result.status === "already_running") {
                        showToast("爬虫正在运行中，请稍候...");
                    } else {
                        showToast("数据刷新已启动，等待爬虫完成...");
                        await pollScraperStatus();
                    }
                }
            } catch {
                serverAvailable = false;
            }

            if (serverAvailable) {
                await loadData();
                showToast("数据已更新至最新！");
            } else {
                await loadData();
                showToast("已加载最新数据（本地服务器未启动，无法触发爬虫）");
            }
        } else {
            // 线上模式：直接重新加载JSON
            await loadData();
            showToast("数据已刷新");
        }
    } catch (e) {
        console.error("Refresh failed:", e);
        showToast("刷新失败，请稍后重试");
    } finally {
        btnRefresh.classList.remove("loading");
        btnRefresh.textContent = "🔄 刷新数据";
    }
}

async function pollScraperStatus() {
    const maxWait = 180;
    const interval = 5000;
    let elapsed = 0;

    while (elapsed < maxWait * 1000) {
        try {
            const resp = await fetch(LOCAL_SERVER + "/api/status", {
                signal: AbortSignal.timeout(5000),
            });
            if (resp.ok) {
                const status = await resp.json();
                if (!status.running) {
                    showToast(status.last_result === "success" ? "爬虫已完成，正在加载新数据..." : "爬虫运行结束，但可能出错");
                    return;
                }
            }
        } catch {
            return;
        }
        await new Promise((r) => setTimeout(r, interval));
        elapsed += interval;
    }
    showToast("等待超时，请稍后手动刷新");
}

function showToast(text) {
    const toast = document.getElementById("refreshToast");
    const toastText = document.getElementById("refreshToastText");
    if (!toast || !toastText) return;
    toastText.textContent = text;
    toast.style.display = "block";
    toast.style.opacity = "1";
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => {
            toast.style.display = "none";
        }, 300);
    }, 3000);
}

function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(() => {
        loadData();
    }, AUTO_REFRESH_INTERVAL);
}

// ====== 工具函数 ======

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function escapeAttr(str) {
    if (!str) return "";
    return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ====== 初始化 ======

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initHistory();
    initRefresh();
    loadData();
    startAutoRefresh();
});
