from __future__ import annotations

def story_script() -> str:
    return """<script>
(function () {
  const steps = Array.from(document.querySelectorAll("[data-story-index]"));
  const counter = document.getElementById("story-counter");
  const detailsTitle = document.getElementById("story-details-title");
  const detailsBody = document.getElementById("story-details-body");
  const jumpDurationMs = 0;
  let activeIndex = 0;
  let activeTarget = null;
  let activeScrollTimer = 0;
  let activeScrollEndTimer = 0;
  let activeFlashClearTimer = 0;
  let navigationToken = 0;
  let topStateRaf = 0;
  let storyOffsetRaf = 0;
  if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
  }

  function initReviewNavResize() {
    const nav = document.getElementById("review-comments");
    const resizer = nav ? nav.querySelector(".review-nav-resizer") : null;
    if (!nav || !resizer) {
      return;
    }
    let resizing = false;
    const defaultWidth = 430;

    function applyWidth(width) {
      const maxWidth = Math.max(320, Math.min(window.innerWidth * 0.58, 820));
      const nextWidth = Math.max(280, Math.min(maxWidth, width));
      document.documentElement.style.setProperty("--nav-width", nextWidth + "px");
    }

    resizer.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 || window.matchMedia("(max-width: 1100px)").matches) {
        return;
      }
      resizing = true;
      document.body.classList.add("is-resizing-review-nav");
      event.preventDefault();
    });

    resizer.addEventListener("dblclick", function (event) {
      applyWidth(defaultWidth);
      event.preventDefault();
    });

    document.addEventListener("pointermove", function (event) {
      if (!resizing) {
        return;
      }
      if (event.buttons !== 1) {
        stopResize();
        return;
      }
      applyWidth(event.clientX - 8);
      event.preventDefault();
    });

    function stopResize(event) {
      if (!resizing) {
        return;
      }
      resizing = false;
      document.body.classList.remove("is-resizing-review-nav");
    }

    document.addEventListener("pointerup", stopResize);
    document.addEventListener("pointercancel", stopResize);
    window.addEventListener("blur", stopResize);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        stopResize();
      }
    });
  }

  function initReviewNavTree() {
    const nav = document.getElementById("review-comments");
    if (!nav) {
      return;
    }
    nav.addEventListener("click", function (event) {
      const toggle = event.target.closest(".review-nav-toggle");
      if (!toggle || !nav.contains(toggle)) {
        return;
      }
      const node = toggle.closest(".review-nav-node");
      if (!node) {
        return;
      }
      const nextOpen = !node.classList.contains("is-open");
      event.preventDefault();
      event.stopPropagation();
      node.classList.toggle("is-open", nextOpen);
      toggle.setAttribute("aria-expanded", nextOpen ? "true" : "false");
    });
  }

  function resetReviewNavTree() {
    const nav = document.getElementById("review-comments");
    if (!nav) {
      return;
    }
    for (const node of nav.querySelectorAll(".review-nav-node")) {
      const isFile = node.classList.contains("review-nav-file");
      const shouldOpen = !isFile || node.classList.contains("review-nav-passthrough");
      node.classList.toggle("is-open", shouldOpen);
      const toggle = node.querySelector(":scope > .review-nav-row .review-nav-toggle");
      if (toggle) {
        toggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
      }
    }
    nav.scrollTop = 0;
    nav.scrollLeft = 0;
  }

  function initReviewNavActiveFile() {
    const nav = document.getElementById("review-comments");
    const files = Array.from(document.querySelectorAll("article.file[data-file]"));
    if (!nav || !files.length) {
      return;
    }
    const navItemsByAnchor = new Map();
    for (const link of nav.querySelectorAll('.review-nav-file > .review-nav-row a[href^="#"]')) {
      const anchor = decodeURIComponent(String(link.getAttribute("href") || "").replace(/^#/, ""));
      const item = link.closest(".review-nav-file");
      if (anchor && item) {
        navItemsByAnchor.set(anchor, item);
      }
    }
    let activeItem = null;
    let activeRaf = 0;

    function revealActiveItem(item) {
      let parent = item.parentElement ? item.parentElement.closest(".review-nav-dir") : null;
      while (parent) {
        parent.classList.add("is-open");
        const toggle = parent.querySelector(":scope > .review-nav-row .review-nav-toggle");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "true");
        }
        parent = parent.parentElement ? parent.parentElement.closest(".review-nav-dir") : null;
      }
      const navStyle = window.getComputedStyle(nav);
      const hasOwnScroll = nav.scrollHeight > nav.clientHeight + 2 || nav.scrollWidth > nav.clientWidth + 2;
      if (hasOwnScroll && navStyle.position === "fixed") {
        item.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    }

    function setActiveFile(article) {
      const nextItem = article ? navItemsByAnchor.get(article.id) || null : null;
      if (nextItem === activeItem) {
        return;
      }
      if (activeItem) {
        activeItem.classList.remove("is-current");
      }
      activeItem = nextItem;
      if (activeItem) {
        activeItem.classList.add("is-current");
        revealActiveItem(activeItem);
      }
    }

    function updateActiveFile() {
      activeRaf = 0;
      const story = document.getElementById("story");
      const probeY = Math.min(
        Math.max((story ? story.offsetHeight : 0) + 80, 120),
        window.innerHeight * 0.45
      );
      let candidate = null;
      let fallback = null;
      for (const file of files) {
        const rect = file.getBoundingClientRect();
        if (rect.bottom <= probeY || rect.top >= window.innerHeight) {
          continue;
        }
        if (rect.top <= probeY) {
          candidate = file;
        } else if (!fallback) {
          fallback = file;
        }
      }
      setActiveFile(candidate || fallback);
    }

    function scheduleActiveFileUpdate() {
      if (activeRaf) {
        return;
      }
      activeRaf = window.requestAnimationFrame(updateActiveFile);
    }

    window.addEventListener("scroll", scheduleActiveFileUpdate, { passive: true });
    window.addEventListener("resize", scheduleActiveFileUpdate);
    scheduleActiveFileUpdate();
  }

  function updateStoryOffset() {
    const story = document.getElementById("story");
    if (!story) {
      document.documentElement.style.setProperty("--story-offset", "0px");
      return;
    }
    story.style.minHeight = "";
    const storyTop = Math.max(0, Math.ceil(story.getBoundingClientRect().top));
    const currentHeight = Math.ceil(story.getBoundingClientRect().height);
    document.documentElement.style.setProperty("--story-offset", (storyTop + currentHeight) + "px");
  }

  function scheduleStoryOffsetUpdate() {
    if (storyOffsetRaf) {
      return;
    }
    storyOffsetRaf = window.requestAnimationFrame(function () {
      storyOffsetRaf = 0;
      updateStoryOffset();
    });
  }

  function updateTopButtonState() {
    if (topStateRaf) {
      return;
    }
    topStateRaf = window.requestAnimationFrame(function () {
      topStateRaf = 0;
      const hasLeftTop = window.scrollY > 24;
      const story = document.getElementById("story");
      const storyPinned = Boolean(
        hasLeftTop && story && story.getBoundingClientRect().top <= 0
      );
      document.body.classList.toggle("has-left-top", hasLeftTop);
      document.body.classList.toggle("has-pinned-story", storyPinned);
    });
  }

  function setActive(index) {
    if (!steps.length) {
      return;
    }
    activeIndex = Math.max(0, Math.min(steps.length - 1, index));
    steps.forEach(function (step, stepIndex) {
      step.classList.toggle("is-active", stepIndex === activeIndex);
    });
    if (counter) {
      counter.textContent = (activeIndex + 1) + " / " + steps.length;
    }
    const step = steps[activeIndex];
    document.body.dataset.activeStoryTitle = step.dataset.storyTitle || "";
    document.body.dataset.activeStoryBody = step.dataset.storyBody || "";
    if (detailsTitle) {
      detailsTitle.textContent = step.dataset.storyTitle || "Details";
    }
    if (detailsBody) {
      detailsBody.textContent = step.dataset.storyBody || "";
    }
    updateStoryOffset();
  }

  function clearTargetHighlight() {
    if (activeTarget) {
      activeTarget.classList.remove("story-target-active");
      activeTarget = null;
    }
    clearFlashTargets();
  }

  function openStep(index) {
    if (!steps.length) {
      return;
    }
    setActive(index);
    const step = steps[activeIndex];
    clearTargetHighlight();

    const targetId = step.dataset.storyTarget || "";
    jumpToStoryTarget(step, targetId);
  }

  function jumpToStoryTarget(step, targetId) {
    if (targetId) {
      const target = document.getElementById(targetId);
      if (target) {
        activeTarget = target;
        target.classList.add("story-target-active");
        animateWindowScrollToElement(target, jumpDurationMs);
      }
    } else {
      animateWindowScrollToElement(step, jumpDurationMs);
    }
  }

  function jumpToHash(hash, updateUrl) {
    const targetId = decodeURIComponent(String(hash || "").replace(/^#/, ""));
    if (!targetId) {
      return false;
    }
    const target = document.getElementById(targetId);
    if (!target) {
      return false;
    }
    clearTargetHighlight();
    activeTarget = target;
    target.classList.add("story-target-active");
    animateWindowScrollToElement(target, jumpDurationMs);
    if (updateUrl && history.replaceState) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    return true;
  }

  function jumpToTop() {
    clearTargetHighlight();
    navigationToken += 1;
    animateWindowScrollToY(0, jumpDurationMs, navigationToken);
    const nav = document.getElementById("review-comments");
    if (nav) {
      nav.scrollTop = 0;
      nav.scrollLeft = 0;
    }
    if (history.replaceState) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    updateTopButtonState();
  }

  function resetPageScrollOnLoad() {
    const nav = document.getElementById("review-comments");
    window.scrollTo(0, 0);
    if (nav) {
      nav.scrollTop = 0;
      nav.scrollLeft = 0;
    }
    document.body.classList.remove("has-left-top");
    document.body.classList.remove("has-pinned-story");
  }

  function animateWindowScrollToElement(element, durationMs) {
    window.clearTimeout(activeScrollTimer);
    window.clearTimeout(activeScrollEndTimer);
    navigationToken += 1;
    const token = navigationToken;
    const startY = window.scrollY;
    const scrollElement = scrollContextElement(element);
    const rect = scrollElement.getBoundingClientRect();
    const safeTop = scrollSafeTop();
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const targetY = Math.max(0, Math.min(maxY, startY + rect.top - safeTop));
    animateWindowScrollToY(targetY, durationMs, token, function () {
      flashTargets(element, scrollElement);
    });
  }

  function scrollSafeTop() {
    const value = getComputedStyle(document.documentElement).getPropertyValue("--story-offset");
    const storyOffset = Number.parseFloat(value || "0");
    return (Number.isFinite(storyOffset) ? storyOffset : 0) + 72;
  }

  function scrollContextElement(element) {
    if (!element || !element.classList || !element.classList.contains("review-comment")) {
      return element;
    }
    const row = element.closest("tr.comment-row");
    if (!row) {
      return element;
    }
    let context = row;
    let visibleLines = 0;
    let cursor = row.previousElementSibling;
    while (cursor && visibleLines < 3) {
      if (cursor.matches("tr[id], tr.add, tr.ctx, tr.del")) {
        context = cursor;
        visibleLines += 1;
      }
      cursor = cursor.previousElementSibling;
    }
    return context;
  }

  function flashTargets(element, contextElement) {
    clearFlashTargets();
    const commentTargets = element && element.classList && element.classList.contains("review-comment")
      ? [element]
      : [];
    const codeTargets = codeFlashTargets(element, contextElement);
    for (const target of commentTargets) {
      target.classList.remove("story-target-flash");
      void target.offsetWidth;
      target.classList.add("story-target-flash");
      activeFlashClearTimer = window.setTimeout(function () {
        target.classList.remove("story-target-flash");
      }, 460);
    }
    for (const target of codeTargets) {
      target.classList.remove("code-target-flash");
      target.classList.remove("code-target-flash-start");
      target.classList.remove("code-target-flash-end");
      void target.offsetWidth;
      target.classList.add("code-target-flash");
      activeFlashClearTimer = window.setTimeout(function () {
        target.classList.remove("code-target-flash");
        target.classList.remove("code-target-flash-start");
        target.classList.remove("code-target-flash-end");
      }, 460);
    }
  }

  function codeFlashTargets(element, contextElement) {
    if (element && element.dataset && element.dataset.commentFile) {
      const file = element.dataset.commentFile;
      const start = Number(element.dataset.commentRangeStart || element.dataset.commentLine || 0);
      const end = Number(element.dataset.commentRangeEnd || start);
      if (file && Number.isFinite(start) && Number.isFinite(end)) {
        const rows = Array.from(document.querySelectorAll("tr[data-file]")).filter(function (row) {
          const line = Number(row.dataset.newLine || 0);
          return row.dataset.file === file && line >= start && line <= end;
        });
        if (rows.length) {
          rows[0].classList.add("code-target-flash-start");
          rows[rows.length - 1].classList.add("code-target-flash-end");
        }
        return rows;
      }
    }
    const row = contextElement && contextElement.closest ? contextElement.closest("tr[data-file]") : null;
    if (row) {
      row.classList.add("code-target-flash-start");
      row.classList.add("code-target-flash-end");
      return [row];
    }
    return [];
  }

  function clearFlashTargets() {
    window.clearTimeout(activeFlashClearTimer);
    for (const target of document.querySelectorAll(".story-target-flash")) {
      target.classList.remove("story-target-flash");
    }
    for (const target of document.querySelectorAll(".code-target-flash")) {
      target.classList.remove("code-target-flash");
      target.classList.remove("code-target-flash-start");
      target.classList.remove("code-target-flash-end");
    }
  }

  function animateWindowScrollToY(targetY, durationMs, token, onDone) {
    window.clearTimeout(activeScrollTimer);
    window.clearTimeout(activeScrollEndTimer);
    const startY = window.scrollY;
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    targetY = Math.max(0, Math.min(maxY, targetY));
    const distance = targetY - startY;
    const startedAt = performance.now();
    if (durationMs <= 0) {
      window.scrollTo(0, targetY);
      updateTopButtonState();
      if (onDone) {
        onDone();
      }
      return;
    }
    if (!distance) {
      if (onDone) {
        onDone();
      }
      return;
    }
    function tick(now) {
      if (token && token !== navigationToken) {
        return;
      }
      const elapsed = Math.min(1, (now - startedAt) / durationMs);
      const eased = elapsed < 0.5
        ? 4 * elapsed * elapsed * elapsed
        : 1 - Math.pow(-2 * elapsed + 2, 3) / 2;
      window.scrollTo(0, startY + distance * eased);
      if (elapsed < 1) {
        activeScrollTimer = window.setTimeout(function () {
          tick(performance.now());
        }, 16);
      }
    }
    tick(performance.now());
    activeScrollEndTimer = window.setTimeout(function () {
      if (token && token !== navigationToken) {
        return;
      }
      window.scrollTo(0, targetY);
      updateTopButtonState();
      if (onDone) {
        onDone();
      }
    }, durationMs + 30);
  }

  document.addEventListener("click", function (event) {
    const nav = event.target.closest("[data-story-nav]");
    if (nav) {
      if (steps.length) {
        openStep(activeIndex + (nav.dataset.storyNav === "prev" ? -1 : 1));
      }
      return;
    }
    if (event.target.closest("[data-story-top]")) {
      event.preventDefault();
      jumpToTop();
      return;
    }
    if (event.target.closest("[data-review-nav-reset]")) {
      event.preventDefault();
      resetReviewNavTree();
      return;
    }
    const navFileLink = event.target.closest(".review-nav-file .review-nav-row a");
    if (navFileLink && jumpToHash(navFileLink.getAttribute("href"), true)) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    const anchor = event.target.closest('a[href^="#"]');
    if (anchor && jumpToHash(anchor.getAttribute("href"), true)) {
      event.preventDefault();
      return;
    }
    const step = event.target.closest("[data-story-index]");
    if (step) {
      const index = Number(step.dataset.storyIndex);
      if (Number.isFinite(index)) {
        event.stopPropagation();
        openStep(index);
      }
    }
  });

  document.addEventListener("keydown", function (event) {
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (!steps.length) {
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      openStep(activeIndex + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      openStep(activeIndex - 1);
    }
  });

  initReviewNavResize();
  initReviewNavTree();
  initReviewNavActiveFile();
  updateStoryOffset();
  updateTopButtonState();
  resetPageScrollOnLoad();
  if (steps.length) {
    setActive(0);
  }
  if (location.hash && history.replaceState) {
    history.replaceState(null, "", location.pathname + location.search);
  }
  window.addEventListener("scroll", function () {
    updateTopButtonState();
    scheduleStoryOffsetUpdate();
  }, { passive: true });
  window.addEventListener("resize", scheduleStoryOffsetUpdate);
  window.addEventListener("pageshow", function () {
    updateStoryOffset();
    updateTopButtonState();
    resetPageScrollOnLoad();
  });
  window.setTimeout(function () {
    updateStoryOffset();
    updateTopButtonState();
    resetPageScrollOnLoad();
  }, 60);
}());
	</script>
	"""
