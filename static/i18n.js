(() => {
  const STORAGE_KEY = "vbf_lang";
  const DEFAULT_LANG = "zh-CN";

  function normalizeLang(lang) {
    return lang === "en" ? "en" : DEFAULT_LANG;
  }

  function getLang() {
    try {
      return normalizeLang(localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return DEFAULT_LANG;
    }
  }

  function setLang(lang) {
    const next = normalizeLang(lang);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (_) {}
    document.documentElement.lang = next;
    window.dispatchEvent(new CustomEvent("vbf:langchange", { detail: { lang: next } }));
    return next;
  }

  function toggleLang() {
    return setLang(getLang() === DEFAULT_LANG ? "en" : DEFAULT_LANG);
  }

  function translate(dict, lang) {
    const strings = (dict && dict.strings && dict.strings[lang]) || {};
    const titles = (dict && dict.titles) || {};

    if (titles[lang]) {
      document.title = titles[lang];
    }

    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.dataset.i18n;
      if (strings[key] !== undefined) node.textContent = strings[key];
    });

    document.querySelectorAll("[data-i18n-html]").forEach((node) => {
      const key = node.dataset.i18nHtml;
      if (strings[key] !== undefined) node.innerHTML = strings[key];
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      const key = node.dataset.i18nPlaceholder;
      if (strings[key] !== undefined) node.setAttribute("placeholder", strings[key]);
    });

    document.querySelectorAll("[data-i18n-title]").forEach((node) => {
      const key = node.dataset.i18nTitle;
      if (strings[key] !== undefined) node.setAttribute("title", strings[key]);
    });

    document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
      const key = node.dataset.i18nAriaLabel;
      if (strings[key] !== undefined) node.setAttribute("aria-label", strings[key]);
    });

    document.querySelectorAll("[data-lang-toggle]").forEach((node) => {
      node.textContent = lang === DEFAULT_LANG ? "English" : "简体中文";
      node.setAttribute(
        "aria-label",
        lang === DEFAULT_LANG ? "Switch to English" : "切换到简体中文",
      );
    });
  }

  function mount({ dict, onRender } = {}) {
    const render = (lang = getLang()) => {
      document.documentElement.lang = lang;
      translate(dict, lang);
      if (typeof onRender === "function") onRender(lang);
    };

    document.querySelectorAll("[data-lang-toggle]").forEach((node) => {
      node.addEventListener("click", toggleLang);
    });

    window.addEventListener("vbf:langchange", (event) => {
      render(event.detail.lang);
    });

    render();
  }

  window.VBF_I18N = {
    getLang,
    setLang,
    toggleLang,
    translate,
    mount,
    normalizeLang,
  };

  document.documentElement.lang = getLang();
})();
