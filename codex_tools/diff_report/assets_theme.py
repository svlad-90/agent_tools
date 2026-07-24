from __future__ import annotations

def theme_script() -> str:
    return """<script>
(function () {
  const themeKey = "codex-diff-report-theme";
  const textScaleKey = "codex-diff-report-text-scale";
  const root = document.documentElement;
  const toggle = document.querySelector("[data-settings-toggle]");
  const modal = document.querySelector("[data-settings-modal]");
  const closeButtons = Array.from(document.querySelectorAll("[data-settings-close]"));
  const themeOptions = Array.from(document.querySelectorAll("[data-theme-value]"));
  const textScaleButtons = Array.from(document.querySelectorAll("[data-text-scale-step]"));
  const textScaleReset = document.querySelector("[data-text-scale-reset]");
  const minTextScale = 0.9;
  const maxTextScale = 1.3;

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

  function normalizeTextScale(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return 1;
    }
    return Math.max(minTextScale, Math.min(maxTextScale, Math.round(parsed * 10) / 10));
  }

  function currentTextScale() {
    try {
      return normalizeTextScale(localStorage.getItem(textScaleKey));
    } catch (error) {
      return 1;
    }
  }

  function applyTextScale(scale, persist) {
    const nextScale = normalizeTextScale(scale);
    root.style.setProperty("--text-scale", String(nextScale));
    if (textScaleReset) {
      textScaleReset.textContent = Math.round(nextScale * 100) + "%";
    }
    for (const button of textScaleButtons) {
      const step = Number(button.dataset.textScaleStep || 0);
      const disabled = step < 0 ? nextScale <= minTextScale : nextScale >= maxTextScale;
      button.disabled = disabled;
      button.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
    if (persist) {
      try {
        localStorage.setItem(textScaleKey, String(nextScale));
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
  applyTextScale(currentTextScale(), false);

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
  for (const button of textScaleButtons) {
    button.addEventListener("click", function () {
      const currentScale = Number(root.style.getPropertyValue("--text-scale")) || 1;
      applyTextScale(currentScale + Number(button.dataset.textScaleStep || 0), true);
    });
  }
  if (textScaleReset) {
    textScaleReset.addEventListener("click", function () {
      applyTextScale(1, true);
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
    if (event.key === textScaleKey) {
      applyTextScale(event.newValue, false);
    }
  });
}());
</script>
"""
