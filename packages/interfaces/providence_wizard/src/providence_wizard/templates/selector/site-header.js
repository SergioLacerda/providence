/* Providence — shared dynamic site header
 * Synced copy. Canonical source: apps/landing/public/shared/site-header.js
 * (providence_wizard is packaged independently via importlib.resources, so it
 * cannot reach across to apps/landing at build time — keep both in sync
 * manually when editing).
 *
 * Mounted on Selector and Docs only. The landing page keeps its own React
 * header (apps/landing/src/components/Landing.tsx) unchanged.
 *
 * Usage:
 *   window.SDDSiteHeader.mount({ nav: "landing" | "docs", root: "../" });
 * `root` is the relative path from the current page to the shared site root
 * (build/site/). If omitted, it is auto-detected from MkDocs Material's own
 * logo link (same trick used by the removed docs/app/sdd-banner.js).
 */
(function () {
  var NAV = {
    landing: [
      { key: "home", label: { en: "Home", pt: "Home" }, href: "" },
      { key: "selector", label: { en: "Selector", pt: "Selector" }, href: "selector/" },
      { key: "docs", label: { en: "Docs", pt: "Docs" }, href: "docs/" },
    ],
    docs: [
      { key: "home", label: { en: "Home", pt: "Home" }, href: "" },
      { key: "selector", label: { en: "Selector", pt: "Selector" }, href: "selector/" },
      { key: "getting-started", label: { en: "Getting Started", pt: "Primeiros Passos" }, href: "docs/guides/CLIENT_ONBOARDING/" },
      { key: "guides", label: { en: "Guides", pt: "Guias" }, href: "docs/guides/TECHNICAL_GUIDE/" },
      { key: "reference", label: { en: "Reference", pt: "Referência" }, href: "docs/spec/reference/commands/cli/" },
      { key: "architecture", label: { en: "Architecture", pt: "Arquitetura" }, href: "docs/architecture/" },
      { key: "runtime", label: { en: "Runtime", pt: "Runtime" }, href: "docs/runtime/protocols/AGENT_ENTRYPOINT/" },
      { key: "governance", label: { en: "Governance", pt: "Governança" }, href: "docs/spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW/" },
    ],
  };

  function detectLang() {
    var docLang = document.documentElement.lang;
    if (docLang) return docLang.slice(0, 2);
    var stored = null;
    try { stored = localStorage.getItem("sdd-lang"); } catch (e) { /* noop */ }
    return stored || "en";
  }

  function rootHref() {
    var logo = document.querySelector(".md-header__button.md-logo")
            || document.querySelector("a.md-logo")
            || document.querySelector('[data-md-component="logo"]');
    var href = logo && logo.getAttribute("href");
    if (!href) {
      var base = document.querySelector("base");
      href = (base && base.getAttribute("href")) || "./";
    }
    if (href.charAt(href.length - 1) !== "/") href += "/";
    return href;
  }

  function isActive(item, nav, root) {
    if (nav !== "docs") return item.key === "selector";
    var path = window.location.pathname;
    if (item.key === "home") return false;
    var target = (root + item.href).replace(/\/{2,}/g, "/");
    return path.indexOf(target.replace(/^\.\.?\//, "/")) !== -1
      || path.indexOf("/" + item.href) !== -1;
  }

  function build(opts) {
    opts = opts || {};
    var nav = opts.nav === "docs" ? "docs" : "landing";
    var root = opts.root || (nav === "docs" ? rootHref() + "../" : "../");
    var lang = opts.lang || detectLang();
    var items = NAV[nav];

    if (document.querySelector(".providence-site-header")) return; // avoid duplicates

    var header = document.createElement("div");
    header.className = "providence-site-header";
    header.setAttribute("data-nav", nav);

    var brand = document.createElement("a");
    brand.className = "providence-site-header-brand";
    brand.href = root;
    brand.innerHTML =
      '<span class="providence-site-header-mark" aria-hidden="true">' +
        '<span class="providence-site-header-halo"></span>' +
        '<span class="providence-site-header-ring"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-a"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-b"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-c"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-d"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-e"></span>' +
        '<span class="providence-site-header-mote providence-site-header-mote-f"></span>' +
        '<img src="' + root + 'assets/sdd-mark.svg" width="24" height="24" alt="" />' +
      '</span>' +
      '<span class="providence-site-header-brand-text">SDD<span class="dim">Harness</span></span>';

    var navEl = document.createElement("nav");
    navEl.className = "providence-site-header-nav";
    items.forEach(function (item) {
      var a = document.createElement("a");
      a.href = root + item.href;
      a.textContent = item.label[lang] || item.label.en;
      if (isActive(item, nav, root)) a.setAttribute("aria-current", "page");
      navEl.appendChild(a);
    });

    // Docs: language switching and search/theme stay on MkDocs Material's own
    // native controls (kept visible in a slim utility row below this header —
    // see the .md-header__title/.md-tabs suppression in site-header.css).
    // They are real, working widgets (the i18n plugin already computes
    // correct localized URLs); duplicating them here would only add a second,
    // non-functional copy, since Material's own JS drives them and does not
    // react when its host elements are hidden via display:none.
    var actions = null;
    if (nav !== "docs") {
      actions = document.createElement("div");
      actions.className = "providence-site-header-actions";

      var langGroup = document.createElement("span");
      langGroup.className = "providence-site-header-lang-group";
      ["pt", "en"].forEach(function (code) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "providence-site-header-lang";
        btn.textContent = code === "pt" ? "PT-BR" : "EN";
        if (lang === code) btn.setAttribute("aria-current", "true");
        btn.addEventListener("click", function () {
          try { localStorage.setItem("sdd-lang", code); } catch (e) { /* noop */ }
          if (typeof opts.onLangChange === "function") opts.onLangChange(code);
        });
        langGroup.appendChild(btn);
      });
      actions.appendChild(langGroup);
    }

    if (actions && opts.theme === true) {
      var themeBtn = document.createElement("button");
      themeBtn.type = "button";
      themeBtn.className = "providence-site-header-icon";
      themeBtn.setAttribute("aria-label", "Toggle theme");
      themeBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
      themeBtn.addEventListener("click", function () {
        opts.onThemeToggle();
      });
      actions.appendChild(themeBtn);
    }

    header.appendChild(brand);
    header.appendChild(navEl);
    if (actions) header.appendChild(actions);
    document.body.insertBefore(header, document.body.firstChild);

    if (nav === "docs") {
      document.documentElement.style.setProperty("--sdd-header-offset", header.offsetHeight + "px");
    }
  }

  window.SDDSiteHeader = { mount: build };

  // Auto-mount on MkDocs Docs pages (detected via Material's native header,
  // present in the server-rendered HTML before this script runs), or via an
  // explicit data attribute on this <script> tag, e.g.
  // <script src="shared/site-header.js" data-sdd-nav="docs"></script>.
  // Selector calls SDDSiteHeader.mount(...) explicitly instead (see index.html).
  var thisScript = document.currentScript;
  var autoNav = (thisScript && thisScript.getAttribute("data-sdd-nav"))
    || (document.querySelector(".md-header") ? "docs" : null);
  if (autoNav) {
    var mountAuto = function () { build({ nav: autoNav }); };
    var documentObservable = window["document$"];
    if (documentObservable && typeof documentObservable.subscribe === "function") {
      documentObservable.subscribe(mountAuto);
    } else if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mountAuto);
    } else {
      mountAuto();
    }
  }
})();
