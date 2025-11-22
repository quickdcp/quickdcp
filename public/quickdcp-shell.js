// WARNING: This file is legacy and not active.
// DO NOT IMPORT until full refactor is complete.
// All selectors refer to a deprecated DOM structure.

// QuickDCP Shell - Shared logic for all pages

(function() {
  'use strict';

  // ---- Page and Section Maps ----
  const pageMap = {
    index: "/",
    verify: "/verify.html",
    "proof-chain": "/docs/dcp-proof-chain.html",
    about: "/about.html"
  };

  const sectionMap = {
    upload: "#panel-upload",
    jobs: "#panel-jobs",
    qc: "#panel-qc",
    proof: "#panel-proof",
    worker: "#panel-worker",
    kdm: "#panel-kdm",
    vault: "#panel-vault"
  };

  // ---- Utility Functions ----
  function $(id) {
    return document.getElementById(id);
  }

  const apiBase = window.location.origin;

  // ---- Scroll to Section ----
  function scrollToSection(key) {
    const selector = sectionMap[key];
    const el = selector ? document.querySelector(selector) : null;
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---- Execute Command ----
  function executeCommand(command) {
    const trimmed = (command || "").toLowerCase().trim();
    
    // Check if it's a section key (only works on index.html)
    if (sectionMap[trimmed]) {
      scrollToSection(trimmed);
      return true;
    }
    
    // Check if it's a page name
    if (pageMap[trimmed]) {
      window.location.href = pageMap[trimmed];
      return true;
    }
    
    // Try fuzzy matching for sections
    const sectionKeys = Object.keys(sectionMap);
    for (const key of sectionKeys) {
      if (key.startsWith(trimmed) || trimmed.startsWith(key) || 
          key.includes(trimmed) || trimmed.includes(key)) {
        scrollToSection(key);
        return true;
      }
    }
    
    // Try fuzzy matching for pages
    const pageKeys = Object.keys(pageMap);
    for (const key of pageKeys) {
      if (key.startsWith(trimmed) || trimmed.startsWith(key) || 
          key.includes(trimmed) || trimmed.includes(key)) {
        window.location.href = pageMap[key];
        return true;
      }
    }
    
    return false;
  }

  // ---- Wire Page Navigation ----
  function wirePageNav() {
    const navPills = document.querySelectorAll(".qd-shell-nav button");
    navPills.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const key = btn.dataset.section;
        if (key) {
          scrollToSection(key);
        } else if (btn.onclick) {
          // If button has onclick, let it handle navigation
          return;
        }
      });
    });

    // Highlight active pill by section in view (only on index.html)
    const panels = [
      "panel-upload",
      "panel-jobs",
      "panel-qc",
      "panel-proof",
      "panel-worker",
      "panel-kdm",
      "panel-vault",
    ].map((id) => document.getElementById(id)).filter(Boolean);

    if (panels.length > 0) {
      const observer = new IntersectionObserver(
        (entries) => {
          let topMost = null;
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              if (!topMost || entry.boundingClientRect.top < topMost.boundingClientRect.top) {
                topMost = entry;
              }
            }
          });
          if (topMost) {
            const id = topMost.target.id;
            navPills.forEach((btn) => {
              btn.classList.toggle("active", btn.dataset.target === id);
            });
          }
        },
        { rootMargin: "-40% 0px -50% 0px", threshold: 0.2 }
      );

      panels.forEach((panel) => panel && observer.observe(panel));
    }
  }

  // ---- Wire Command Palette ----
  function wireCommandPalette() {
    const searchModal = document.getElementById("qdSearchModal");
    if (!searchModal) return;

    const searchInner = searchModal.querySelector(".qd-search-inner");
    const searchInput = searchModal.querySelector("input");
    const searchOptions = searchModal.querySelectorAll(".qd-search-options li");

    function closeSearchModal() {
      searchModal.classList.remove("open");
      if (searchInput) searchInput.value = "";
    }

    function resolveSectionKey(query) {
      const lowerQuery = query.toLowerCase().trim();
      const keys = Object.keys(sectionMap);
      
      // Exact match
      if (keys.includes(lowerQuery)) {
        return lowerQuery;
      }
      
      // startsWith match
      for (const key of keys) {
        if (key.startsWith(lowerQuery) || lowerQuery.startsWith(key)) {
          return key;
        }
      }
      
      // includes match
      for (const key of keys) {
        if (key.includes(lowerQuery) || lowerQuery.includes(key)) {
          return key;
        }
      }
      
      return null;
    }

    // Click on options
    searchOptions.forEach((li) => {
      li.addEventListener("click", () => {
        const key = li.dataset.section;
        if (key) {
          scrollToSection(key);
        }
        closeSearchModal();
      });
    });

    // Enter key in input
    if (searchInput) {
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const query = searchInput.value.trim();
          if (query) {
            const key = resolveSectionKey(query);
            if (key) {
              scrollToSection(key);
              closeSearchModal();
            } else {
              // Try executeCommand for page navigation
              if (executeCommand(query)) {
                closeSearchModal();
              }
            }
          }
        }
      });
    }

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        searchModal.classList.add("open");
        setTimeout(() => {
          if (searchInput) searchInput.focus();
        }, 100);
      } else if (e.key === "Escape" && searchModal.classList.contains("open")) {
        e.preventDefault();
        closeSearchModal();
      }
    });

    // Click outside to close
    searchModal.addEventListener("click", (e) => {
      if (e.target === searchModal) {
        closeSearchModal();
      }
    });
  }

  // ---- API Health Check ----
  async function refreshApiHealth() {
    const led = $("apiLed");
    const txt = $("apiStatusText");
    if (!led || !txt) return;

    try {
      const res = await fetch(apiBase + "/healthz");
      if (!res.ok) throw new Error("bad");
      const data = await res.json().catch(() => ({}));
      led.classList.remove("bad");
      txt.textContent = "API: online" + (data.db ? " · DB: " + data.db : "");
    } catch (e) {
      led.classList.add("bad");
      txt.textContent = "API: offline (check container)";
    }
  }

  // ---- Initialize ----
  function init() {
    wirePageNav();
    wireCommandPalette();
    refreshApiHealth();
    setInterval(refreshApiHealth, 15000);
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Export for global access if needed
  window.QuickDCPShell = {
    pageMap,
    sectionMap,
    scrollToSection,
    executeCommand,
    wirePageNav,
    wireCommandPalette
  };
})();


