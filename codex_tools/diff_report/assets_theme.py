from __future__ import annotations

def theme_script() -> str:
    return """<script>
(function () {
  const themeKey = "codex-diff-report-theme";
  const root = document.documentElement;
  const toggle = document.querySelector("[data-settings-toggle]");
  const modal = document.querySelector("[data-settings-modal]");
  const closeButtons = Array.from(document.querySelectorAll("[data-settings-close]"));
  const themeOptions = Array.from(document.querySelectorAll("[data-theme-value]"));

  function currentTheme() {
    return root.dataset.theme === "dark" ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = nextTheme;
    for (const option of themeOptions) {
      const active = option.dataset.themeValue === nextTheme;
      option.classList.toggle("is-active", active);
      option.setAttribute("aria-pressed", active ? "true" : "false");
    }
    if (persist) {
      try {
        localStorage.setItem(themeKey, nextTheme);
      } catch (error) {
        // Ignore storage failures, for example in restricted file viewers.
      }
    }
  }

  function setSettingsOpen(open) {
    if (!modal || !toggle) {
      return;
    }
    modal.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      const close = modal.querySelector("[data-settings-close].settings-close");
      if (close) {
        close.focus();
      }
    } else {
      toggle.focus();
    }
  }

  applyTheme(currentTheme(), false);

  if (toggle) {
    toggle.addEventListener("click", function (event) {
      event.preventDefault();
      setSettingsOpen(!modal || modal.hidden);
    });
  }
  for (const closeButton of closeButtons) {
    closeButton.addEventListener("click", function () {
      setSettingsOpen(false);
    });
  }
  for (const option of themeOptions) {
    option.addEventListener("click", function () {
      applyTheme(option.dataset.themeValue, true);
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal && !modal.hidden) {
      setSettingsOpen(false);
    }
  });
  window.addEventListener("storage", function (event) {
    if (event.key === themeKey) {
      applyTheme(event.newValue === "dark" ? "dark" : "light", false);
    }
  });
}());
</script>
"""
