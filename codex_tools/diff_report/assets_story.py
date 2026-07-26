from __future__ import annotations

def story_script() -> str:
    return """<script>
(function () {
  const steps = Array.from(document.querySelectorAll("[data-story-index]"));
  const storySteps = document.querySelector(".story-steps");
  const story = document.getElementById("story");
  const storyNavButtons = Array.from(document.querySelectorAll("[data-story-nav]"));
  const storyMoveButtons = Array.from(document.querySelectorAll("[data-diagram-story-step]"));
  const storyToggleButtons = Array.from(document.querySelectorAll("[data-diagram-story-toggle]"));
  const detailsTitle = document.getElementById("story-details-title");
  const detailsBody = document.getElementById("story-details-body");
  const jumpDurationMs = 0;
  let activeIndex = 0;
  let storyPage = 0;
  let storyPageCount = 1;
  let storyPageStart = 0;
  let storyPageColumns = 1;
  let storyPageMaxStart = 0;
  let storyPageUnitWidth = 1;
  let storyPagerRaf = 0;
  let storyPagerResizeTimer = 0;
  let activeTarget = null;
  let activeScrollTimer = 0;
  let activeScrollEndTimer = 0;
  let activeFlashClearTimer = 0;
  let navigationToken = 0;
  let topStateRaf = 0;
  let storyOffsetRaf = 0;
  const storySentinel = story ? document.createElement("div") : null;
  if (story && storySentinel) {
    storySentinel.className = "story-sentinel";
    story.before(storySentinel);
  }
  if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
  }

  function initVocabularyPopovers() {
    const wraps = Array.from(document.querySelectorAll(".vocabulary-ref-wrap"));
    if (!wraps.length) {
      return;
    }
    let activeWrap = null;

    function setStoryVocabularyPopover(wrap, open) {
      const storyPanel = wrap ? wrap.closest(".story") : null;
      if (storyPanel) {
        storyPanel.classList.toggle("has-vocabulary-popover", open);
      }
    }

    function clearVocabularyPopover(wrap) {
      setStoryVocabularyPopover(wrap, false);
      if (activeWrap === wrap) {
        activeWrap = null;
      }
    }

    function positionVocabularyPopover(wrap) {
      const trigger = wrap.querySelector(".vocabulary-ref");
      const popover = wrap.querySelector(".vocabulary-popover");
      if (!trigger || !popover) {
        return;
      }
      activeWrap = wrap;
      wrap.classList.add("is-positioned");
      setStoryVocabularyPopover(wrap, true);
      popover.style.maxWidth = Math.max(180, Math.min(360, window.innerWidth - 32)) + "px";
      const triggerRect = trigger.getBoundingClientRect();
      const popoverRect = popover.getBoundingClientRect();
      const margin = 16;
      const popoverWidth = Math.min(popoverRect.width || 360, Math.max(180, window.innerWidth - (margin * 2)));
      const popoverHeight = popoverRect.height || 120;
      const leftBias = Math.min(72, Math.max(24, popoverWidth * 0.22));
      const left = Math.max(margin, Math.min(triggerRect.left - leftBias, window.innerWidth - popoverWidth - margin));
      let top = triggerRect.bottom + 8;
      if (top + popoverHeight > window.innerHeight - margin) {
        top = Math.max(margin, triggerRect.top - popoverHeight - 8);
      }
      wrap.style.setProperty("--vocabulary-popover-left", left.toFixed(0) + "px");
      wrap.style.setProperty("--vocabulary-popover-top", top.toFixed(0) + "px");
    }

    wraps.forEach(function (wrap) {
      const trigger = wrap.querySelector(".vocabulary-ref");
      if (trigger) {
        trigger.addEventListener("pointerdown", function (event) {
          event.preventDefault();
        });
        trigger.addEventListener("click", function (event) {
          event.preventDefault();
          trigger.blur();
        });
      }
      wrap.addEventListener("pointerenter", function () {
        positionVocabularyPopover(wrap);
      });
      wrap.addEventListener("focusin", function () {
        positionVocabularyPopover(wrap);
      });
      wrap.addEventListener("pointerleave", function () {
        if (!wrap.matches(":focus-within")) {
          clearVocabularyPopover(wrap);
        }
      });
      wrap.addEventListener("focusout", function () {
        window.setTimeout(function () {
          if (!wrap.matches(":focus-within")) {
            clearVocabularyPopover(wrap);
          }
        }, 0);
      });
    });

    window.addEventListener("scroll", function () {
      if (activeWrap && (activeWrap.matches(":hover") || activeWrap.matches(":focus-within"))) {
        positionVocabularyPopover(activeWrap);
      }
    }, { passive: true });
    window.addEventListener("resize", function () {
      if (activeWrap && (activeWrap.matches(":hover") || activeWrap.matches(":focus-within"))) {
        positionVocabularyPopover(activeWrap);
      }
    });
  }

  function initReviewNavResize() {
    const nav = document.getElementById("review-comments");
    const resizer = nav ? nav.querySelector(".review-nav-resizer") : null;
    if (!nav || !resizer) {
      return;
    }
    let resizing = false;
    let resizeLayoutRaf = 0;
    let pendingResizeLayout = false;
    const defaultWidth = 430;

    function scheduleResizeLayout(flush) {
      pendingResizeLayout = true;
      if (resizeLayoutRaf) {
        if (!flush) {
          return;
        }
        window.cancelAnimationFrame(resizeLayoutRaf);
        resizeLayoutRaf = 0;
      }
      const run = function () {
        resizeLayoutRaf = 0;
        if (!pendingResizeLayout) {
          return;
        }
        pendingResizeLayout = false;
        updateStoryOffset();
        scheduleStoryPagerUpdate(false, "auto");
        document.dispatchEvent(new CustomEvent("codex-review-story-layout"));
      };
      if (flush) {
        run();
      } else {
        resizeLayoutRaf = window.requestAnimationFrame(run);
      }
    }

    function applyWidth(width, flushLayout) {
      const maxWidth = Math.max(320, Math.min(window.innerWidth * 0.58, 820));
      const nextWidth = Math.max(280, Math.min(maxWidth, width));
      document.documentElement.style.setProperty("--nav-width", nextWidth + "px");
      document.documentElement.style.setProperty("--brand-scale", String(Math.min(1, nextWidth / defaultWidth)));
      scheduleResizeLayout(Boolean(flushLayout));
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
      applyWidth(defaultWidth, true);
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
      applyWidth(event.clientX - 8, false);
      event.preventDefault();
    });

    function stopResize(event) {
      if (!resizing) {
        return;
      }
      resizing = false;
      document.body.classList.remove("is-resizing-review-nav");
      scheduleResizeLayout(true);
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
    let navScrollRaf = 0;
    let navScrollFollowupTimer = 0;

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
      scheduleNavScrollToItem(item);
    }

    function scheduleNavScrollToItem(item) {
      window.clearTimeout(navScrollFollowupTimer);
      if (navScrollRaf) {
        window.cancelAnimationFrame(navScrollRaf);
      }
      navScrollRaf = window.requestAnimationFrame(function () {
        navScrollRaf = 0;
        scrollNavToItem(item);
        navScrollFollowupTimer = window.setTimeout(function () {
          scrollNavToItem(item);
        }, 80);
      });
    }

    function scrollNavToItem(item) {
      const hasOwnScroll = nav.scrollHeight > nav.clientHeight + 2 || nav.scrollWidth > nav.clientWidth + 2;
      if (!hasOwnScroll) {
        return;
      }
      const navRect = nav.getBoundingClientRect();
      const itemRect = item.getBoundingClientRect();
      const topPadding = 44;
      const bottomPadding = 18;
      if (itemRect.top < navRect.top + topPadding) {
        nav.scrollTop += itemRect.top - navRect.top - Math.max(topPadding, (navRect.height - itemRect.height) / 2);
      } else if (itemRect.bottom > navRect.bottom - bottomPadding) {
        nav.scrollTop += itemRect.bottom - navRect.bottom + Math.max(bottomPadding, (navRect.height - itemRect.height) / 2);
      }
      if (itemRect.left < navRect.left + 8) {
        nav.scrollLeft += itemRect.left - navRect.left - 8;
      } else if (itemRect.right > navRect.right - 8) {
        nav.scrollLeft += itemRect.right - navRect.right + 8;
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
      const storyPinned = Boolean(
        hasLeftTop && storySentinel && storySentinel.getBoundingClientRect().top <= 0
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
    const step = steps[activeIndex];
    document.body.dataset.activeStoryTitle = step.dataset.storyTitle || "";
    document.body.dataset.activeStoryBody = step.dataset.storyBody || "";
    if (detailsTitle) {
      detailsTitle.textContent = step.dataset.storyTitle || "Details";
    }
    if (detailsBody) {
      detailsBody.innerHTML = step.dataset.storyBodyHtml || "";
    }
    updateStoryOffset();
    updateStoryMoveButtons();
    scheduleStoryPagerUpdate(true);
  }

  function setOpenStep(index) {
    for (const step of steps) {
      step.classList.remove("is-open");
      step.setAttribute("aria-pressed", "false");
    }
    if (Number.isInteger(index) && index >= 0 && index < steps.length) {
      steps[index].classList.add("is-open");
      steps[index].setAttribute("aria-pressed", "true");
    }
    updateStoryToggleButtons();
  }

  function updateStoryMoveButtons() {
    for (const button of storyMoveButtons) {
      const isPrev = button.dataset.diagramStoryStep === "prev";
      const disabled = isPrev ? activeIndex <= 0 : activeIndex >= steps.length - 1;
      button.disabled = disabled;
      button.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
    updateStoryToggleButtons();
  }

  function isActiveStepOpen() {
    return steps[activeIndex] ? steps[activeIndex].classList.contains("is-open") : false;
  }

  function updateStoryToggleButtons() {
    const open = isActiveStepOpen();
    const disabled = !steps.length;
    for (const button of storyToggleButtons) {
      const label = open ? "Close slide" : "Open slide";
      button.classList.toggle("is-open", open);
      button.textContent = "";
      button.dataset.tooltip = label;
      button.setAttribute("aria-label", label);
      button.setAttribute("aria-pressed", open ? "true" : "false");
      button.disabled = disabled;
      button.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
  }

  function scheduleStoryPagerUpdate(ensureActive, scrollBehavior) {
    if (storyPagerRaf) {
      window.cancelAnimationFrame(storyPagerRaf);
    }
    storyPagerRaf = window.requestAnimationFrame(function () {
      storyPagerRaf = 0;
      updateStoryPager(ensureActive, scrollBehavior);
    });
  }

  function scheduleStoryPagerResize() {
    scheduleStoryPagerUpdate(false, "auto");
    if (storyPagerResizeTimer) {
      window.clearTimeout(storyPagerResizeTimer);
    }
    storyPagerResizeTimer = window.setTimeout(function () {
      storyPagerResizeTimer = 0;
      scheduleStoryPagerUpdate(false, "auto");
    }, 220);
  }

  function initStoryPagerResizeObserver() {
    if (!storySteps || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(function () {
      scheduleStoryOffsetUpdate();
      scheduleStoryPagerResize();
    });
    observer.observe(storySteps);
    if (story) {
      observer.observe(story);
    }
  }

  function updateStoryPager(ensureActive, scrollBehavior) {
    if (!steps.length || !storySteps) {
      return;
    }
    const items = steps.map(function (step) {
      return step.closest("li");
    }).filter(Boolean);
    if (!items.length) {
      return;
    }
    const viewportWidth = Math.floor(storySteps.getBoundingClientRect().width || storySteps.clientWidth || 0);
    if (viewportWidth <= 0) {
      scheduleStoryPagerResize();
      return;
    }
    const columns = storyColumnsForWidth(viewportWidth);
    const gap = 6;
    const columnWidth = Math.max(1, Math.floor((Math.max(0, viewportWidth) - (gap * Math.max(0, columns - 1))) / columns));
    storySteps.style.setProperty("--story-step-column-width", columnWidth + "px");
    const totalColumns = Math.max(1, items.length);
    const maxStart = Math.max(0, totalColumns - columns);
    storyPageColumns = columns;
    storyPageMaxStart = maxStart;
    storyPageUnitWidth = columnWidth + gap;
    storyPageCount = Math.max(1, Math.ceil(totalColumns / columns));
    if (ensureActive) {
      storyPageStart = Math.min(Math.floor(activeIndex / columns) * columns, maxStart);
    }
    storyPageStart = Math.max(0, Math.min(storyPageStart, maxStart));
    storyPage = Math.floor(storyPageStart / columns);
    for (let index = 0; index < items.length; index += 1) {
      const page = Math.floor(index / columns);
      const indexInPage = index % columns;
      const column = (page * columns) + indexInPage + 1;
      const row = 1;
      items[index].style.gridColumn = String(column);
      items[index].style.gridRow = String(row);
    }
    const targetLeft = storyPageStart * (columnWidth + gap);
    if (scrollBehavior === "auto") {
      syncStoryScrollLeft(targetLeft);
    } else {
      storySteps.scrollTo({ left: targetLeft, behavior: "smooth" });
    }
    for (const button of storyNavButtons) {
      const isPrev = button.dataset.storyNav === "prev";
      const disabled = isPrev ? storyPageStart <= 0 : storyPageStart >= maxStart;
      button.disabled = disabled;
      button.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
  }

  function syncStoryScrollLeft(targetLeft) {
    const previousScrollBehavior = storySteps.style.scrollBehavior;
    storySteps.style.scrollBehavior = "auto";
    storySteps.scrollLeft = targetLeft;
    window.requestAnimationFrame(function () {
      storySteps.style.scrollBehavior = previousScrollBehavior;
    });
  }

  function storyColumnsForWidth(width) {
    const itemMinWidth = window.matchMedia("(max-width: 1100px)").matches ? 230 : 260;
    const gap = 6;
    return Math.max(1, Math.floor((Math.max(0, width) + gap) / (itemMinWidth + gap)));
  }

  function moveStoryPage(direction) {
    if (!steps.length) {
      return;
    }
    const currentStart = Math.max(0, Math.min(storyPageMaxStart, Math.round(storySteps.scrollLeft / storyPageUnitWidth)));
    const nextStart = direction < 0
      ? Math.max(0, currentStart - storyPageColumns)
      : Math.min(storyPageMaxStart, currentStart + storyPageColumns);
    if (nextStart === storyPageStart) {
      return;
    }
    storyPageStart = nextStart;
    updateStoryPager(false, "smooth");
  }

  function clearTargetHighlight() {
    if (activeTarget) {
      activeTarget.classList.remove("story-target-active");
      activeTarget = null;
    }
    clearFlashTargets();
  }

  function closeOpenStoryArtifact() {
    const modal = document.getElementById("diagram-modal");
    if (!modal || modal.hidden) {
      return;
    }
    const closeControl = modal.querySelector("[data-diagram-close]");
    if (closeControl instanceof HTMLElement) {
      closeControl.click();
    }
  }

  function closeCurrentStorySlide() {
    closeOpenStoryArtifact();
    clearTargetHighlight();
    setOpenStep(null);
  }

  function toggleCurrentStorySlide() {
    if (!steps.length) {
      return;
    }
    if (isActiveStepOpen()) {
      closeCurrentStorySlide();
      return;
    }
    openStep(activeIndex);
  }

  function openStep(index) {
    if (!steps.length) {
      return;
    }
    const nextIndex = Math.max(0, Math.min(steps.length - 1, index));
    if (nextIndex === activeIndex && steps[nextIndex].classList.contains("is-open")) {
      closeCurrentStorySlide();
      return;
    }
    setActive(nextIndex);
    const step = steps[activeIndex];
    clearTargetHighlight();

    if (openStoryArtifact(step)) {
      setOpenStep(activeIndex);
      document.body.classList.add("has-pinned-story");
      return;
    }

    closeOpenStoryArtifact();
    setOpenStep(activeIndex);
    const targetId = step.dataset.storyTarget || "";
    jumpToStoryTarget(step, targetId);
  }

  function openStoryArtifact(step) {
    const diagramId = step.dataset.storyDiagram || "";
    if (diagramId) {
      const preview = document.querySelector('[data-diagram-id="' + cssEscape(diagramId) + '"]');
      if (preview) {
        if (step.dataset.storyDiagramFocus) {
          preview.dataset.diagramFocus = step.dataset.storyDiagramFocus;
        }
        if (step.dataset.storyDiagramNotes) {
          preview.dataset.diagramNotes = step.dataset.storyDiagramNotes;
        }
        if (step.dataset.storyDiagramZoom) {
          preview.dataset.diagramZoom = step.dataset.storyDiagramZoom;
        }
        if (step.dataset.storyArtifactComment) {
          preview.dataset.artifactComment = step.dataset.storyArtifactComment;
        }
        preview.dataset.storyTitle = step.dataset.storyTitle || "";
        preview.dataset.storyBody = step.dataset.storyBody || "";
        preview.click();
        return true;
      }
    }
    const logId = step.dataset.storyLog || "";
    if (logId) {
      const preview = document.querySelector('[data-log-id="' + cssEscape(logId) + '"]');
      if (preview) {
        if (step.dataset.storyLogFocus) {
          preview.dataset.logFocus = step.dataset.storyLogFocus;
        }
        if (step.dataset.storyLogZoom) {
          preview.dataset.logZoom = step.dataset.storyLogZoom;
        }
        if (step.dataset.storyArtifactComment) {
          preview.dataset.artifactComment = step.dataset.storyArtifactComment;
        }
        preview.dataset.storyTitle = step.dataset.storyTitle || "";
        preview.dataset.storyBody = step.dataset.storyBody || "";
        preview.click();
        return true;
      }
    }
    return false;
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
    const file = element.dataset.commentFile || "";
    const rangeStart = Number(element.dataset.commentRangeStart || element.dataset.commentLine || 0);
    if (file && Number.isFinite(rangeStart)) {
      const target = document.querySelector(
        'tr[data-file="' + cssEscape(file) + '"][data-new-line="' + String(rangeStart) + '"]'
      );
      if (target) {
        return target;
      }
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

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }
    return String(value).replace(/["\\\\]/g, "\\\\$&");
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
    const overlayTargets = codeTargets.concat(commentTargets);
    if (overlayTargets.length) {
      createCodeTargetFlashOverlay(overlayTargets);
      activeFlashClearTimer = window.setTimeout(function () {
        clearCodeTargetFlashOverlays();
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
        return rowsWithIntermediateDeletes(rows);
      }
    }
    const row = contextElement && contextElement.closest ? contextElement.closest("tr[data-file]") : null;
    if (row) {
      return [row];
    }
    return [];
  }

  function rowsWithIntermediateDeletes(rows) {
    if (rows.length < 2) {
      return rows;
    }
    const first = rows[0];
    const last = rows[rows.length - 1];
    const allRows = Array.from(first.closest("tbody").children);
    const firstIndex = allRows.indexOf(first);
    const lastIndex = allRows.indexOf(last);
    if (firstIndex === -1 || lastIndex === -1 || firstIndex > lastIndex) {
      return rows;
    }
    return allRows.slice(firstIndex, lastIndex + 1).filter(function (row) {
      return row.matches("tr.add, tr.ctx, tr.del");
    });
  }

  function createCodeTargetFlashOverlay(targets) {
    const box = unionClientRects(targets);
    if (!box) {
      return;
    }
    const overlay = document.createElement("div");
    overlay.className = "code-target-flash-overlay";
    overlay.style.left = Math.max(0, box.left + window.scrollX - 3) + "px";
    overlay.style.top = Math.max(0, box.top + window.scrollY - 3) + "px";
    overlay.style.width = Math.max(1, box.width + 6) + "px";
    overlay.style.height = Math.max(1, box.height + 6) + "px";
    document.body.appendChild(overlay);
  }

  function unionClientRects(targets) {
    let box = null;
    for (const target of targets) {
      const rect = target.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        continue;
      }
      if (!box) {
        box = {
          left: rect.left,
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
        };
      } else {
        box.left = Math.min(box.left, rect.left);
        box.top = Math.min(box.top, rect.top);
        box.right = Math.max(box.right, rect.right);
        box.bottom = Math.max(box.bottom, rect.bottom);
      }
    }
    return box ? { left: box.left, top: box.top, width: box.right - box.left, height: box.bottom - box.top } : null;
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
    clearCodeTargetFlashOverlays();
  }

  function clearCodeTargetFlashOverlays() {
    for (const overlay of document.querySelectorAll(".code-target-flash-overlay")) {
      overlay.remove();
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
      event.preventDefault();
      moveStoryPage(nav.dataset.storyNav === "prev" ? -1 : 1);
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

  document.addEventListener("codex-review-story-move", function (event) {
    if (!steps.length) {
      return;
    }
    const direction = event.detail && Number(event.detail.direction) < 0 ? -1 : 1;
    const nextIndex = Math.max(0, Math.min(steps.length - 1, activeIndex + direction));
    if (nextIndex === activeIndex) {
      return;
    }
    openStep(nextIndex);
  });

  document.addEventListener("click", function (event) {
    const toggle = event.target.closest("[data-diagram-story-toggle]");
    if (!toggle) {
      return;
    }
    event.preventDefault();
    toggleCurrentStorySlide();
  });

  document.addEventListener("codex-review-story-layout", function () {
    updateStoryOffset();
    updateTopButtonState();
  });

  document.addEventListener("codex-review-story-artifact", function (event) {
    const detail = event.detail || {};
    if (detail.status === "closed") {
      setOpenStep(null);
    } else if (detail.status === "open" && Number.isInteger(detail.index)) {
      setOpenStep(detail.index);
    }
  });

  initVocabularyPopovers();
  initReviewNavResize();
  initReviewNavTree();
  initReviewNavActiveFile();
  initStoryPagerResizeObserver();
  updateStoryOffset();
  updateStoryPager(true, "auto");
  updateTopButtonState();
  resetPageScrollOnLoad();
  if (steps.length) {
    setActive(0);
  }
  updateStoryMoveButtons();
  if (location.hash && history.replaceState) {
    history.replaceState(null, "", location.pathname + location.search);
  }
  window.addEventListener("scroll", function () {
    updateTopButtonState();
    scheduleStoryOffsetUpdate();
  }, { passive: true });
  window.addEventListener("resize", function () {
    scheduleStoryOffsetUpdate();
    scheduleStoryPagerResize();
  });
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
