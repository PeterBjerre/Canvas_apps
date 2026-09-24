(function () {
  const { toText, escapeHtml } = window.TextUtils;

  const ALL_CATEGORY = "Alle";

  const state = {
    query: "",
    category: ALL_CATEGORY,
  };

  const dom = {};

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    bindDom();

    if (!window.BOOK2_FAQ_DATA || !Array.isArray(window.BOOK2_FAQ_DATA.items)) {
      if (dom.list) {
        dom.list.innerHTML = '<div class="faq-empty">FAQ-data kunne ikke indlæses.</div>';
      }
      return;
    }

    bindEvents();
    renderCategories();
    renderList();
  }

  function bindDom() {
    dom.search = document.getElementById("faqSearch");
    dom.categoryRow = document.getElementById("faqCategoryRow");
    dom.list = document.getElementById("faqList");
    dom.resultCount = document.getElementById("faqResultCount");
  }

  function bindEvents() {
    if (dom.search) {
      dom.search.addEventListener("input", () => {
        state.query = normalizeText(dom.search.value || "");
        renderList();
      });
    }

    if (dom.categoryRow) {
      dom.categoryRow.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const button = target.closest("[data-category]");
        if (!(button instanceof HTMLElement)) return;

        state.category = button.getAttribute("data-category") || ALL_CATEGORY;
        renderCategories();
        renderList();
      });
    }
  }

  function renderCategories() {
    if (!dom.categoryRow) return;

    const categories = Array.from(new Set(window.BOOK2_FAQ_DATA.items.map((item) => item.category))).sort((a, b) =>
      String(a).localeCompare(String(b), "da-DK")
    );
    const all = [ALL_CATEGORY, ...categories];

    dom.categoryRow.innerHTML = all
      .map(
        (category) => `
      <button type="button" class="faq-category-btn" data-category="${escapeHtml(category)}" aria-pressed="${state.category === category}">
        ${escapeHtml(category)}
      </button>
    `
      )
      .join("");
  }

  function renderList() {
    if (!dom.list) return;

    const allItems = window.BOOK2_FAQ_DATA.items;
    const filtered = allItems.filter((item) => {
      if (state.category !== ALL_CATEGORY && item.category !== state.category) return false;
      if (!state.query) return true;

      const transactionText = Array.isArray(item.transactions) ? item.transactions.join(" ") : "";
      const haystack = normalizeText([item.question, item.answer, item.category, transactionText].join(" "));
      return haystack.includes(state.query);
    });

    if (dom.resultCount) {
      dom.resultCount.textContent = `Viser ${filtered.length} af ${allItems.length} spørgsmål`;
    }

    if (!filtered.length) {
      dom.list.innerHTML = '<div class="faq-empty">Ingen FAQ-punkter matcher dit filter.</div>';
      return;
    }

    dom.list.innerHTML = filtered.map(renderFaqItem).join("");
  }

  function renderFaqItem(item) {
    return `
      <details class="faq-item">
        <summary>
          <span class="faq-question-text">${escapeHtml(item.question)}</span>
          <span class="faq-item-category">${escapeHtml(item.category)}</span>
        </summary>
        <div class="faq-item-answer">
          ${renderAnswer(item)}
        </div>
      </details>
    `;
  }

  function renderAnswer(item) {
    const lines = toText(item.answer)
      .split("\n")
      .map((line) => toText(line))
      .filter(Boolean);

    const answerHtml = lines.length
      ? lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("")
      : "<p>-</p>";

    const transactions = Array.isArray(item.transactions)
      ? item.transactions.map((transaction) => toText(transaction)).filter(Boolean)
      : [];

    const roles = Array.isArray(item.roles)
      ? item.roles.map((role) => toText(role)).filter(Boolean)
      : [];

    const transactionHtml = transactions.length
      ? `<div class="faq-transactions">${transactions
          .map((transaction) => `<span class="faq-tcode">${escapeHtml(transaction)}</span>`)
          .join("")}</div>`
      : "";

    const roleHtml = roles.length
      ? `
        <div class="faq-role-block">
          <p class="faq-role-title">Relevante roller</p>
          <div class="faq-roles">${roles.map((role) => `<span class="faq-role">${escapeHtml(role)}</span>`).join("")}</div>
        </div>
      `
      : "";

    return `${answerHtml}${roleHtml}${transactionHtml}`;
  }

  function normalizeText(value) {
    return String(value == null ? "" : value).trim().toLocaleLowerCase("da-DK");
  }
})();
