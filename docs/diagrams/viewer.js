/* PACKAGE is embedded by build.py. The viewer only knows views and explicit routes. */
(() => {
  "use strict";
  const sections = new Map(
    [...document.querySelectorAll("[data-view]")].map((el) => [
      el.dataset.view,
      el,
    ]),
  );
  const toolbar = document.querySelector(".toolbar");
  const breadcrumbs = document.querySelector(".breadcrumbs");
  const context = document.querySelector(".context");
  const anchor = document.querySelector(".context-anchor");
  const up = document.querySelector("#up");
  const overview = document.querySelector("#overview");
  const status = document.querySelector("#location-status");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const cache = new Map();
  let state;
  let busy = false;
  let generation = 0;
  const animations = new Set();

  for (const [id, section] of sections) {
    section
      .querySelectorAll("a, button, [tabindex], summary")
      .forEach((el, i) => {
        if (!el.id) el.id = `${id}-focus-${i}`;
      });
    for (const link of section.querySelectorAll("[data-destination]")) {
      const node = link.querySelector("[data-node]");
      const key = `${id}:${node ? node.dataset.node : link.dataset.destination}`;
      if (!PACKAGE.routes[key])
        throw new Error(`Missing diagram route: ${key}`);
      link.dataset.route = key;
    }
  }

  const current = () => state.trail[state.trail.length - 1];
  const sectionFor = (entry) => sections.get(entry.id);
  const fresh = (id, via = null) => ({
    id,
    via,
    key: crypto.randomUUID(),
    view: null,
  });
  const hashFor = (trail) => "#" + trail.map((entry) => entry.id).join("/");

  function valid(candidate) {
    if (
      candidate?.diagramPackage !== 1 ||
      !Array.isArray(candidate.trail) ||
      !candidate.trail.length
    )
      return false;
    return candidate.trail.every((entry, index) => {
      if (!sections.has(entry.id) || typeof entry.key !== "string")
        return false;
      if (!index) return entry.id === "overview" && entry.via === null;
      const route = PACKAGE.routes[entry.via];
      return (
        route &&
        route.to === entry.id &&
        entry.via.startsWith(candidate.trail[index - 1].id + ":")
      );
    });
  }

  function capture() {
    if (!state) return;
    const entry = current();
    const section = sectionFor(entry);
    entry.view = {
      x: scrollX,
      y: scrollY,
      focus: section.contains(document.activeElement)
        ? document.activeElement.id
        : null,
      diagram: section.querySelector(".diagram-scroll")?.scrollLeft || 0,
      codeX: section.querySelector("pre")?.scrollLeft || 0,
      codeY: section.querySelector("pre")?.scrollTop || 0,
      evidence: !!section.querySelector("details")?.open,
    };
    cache.set(entry.key, entry.view);
  }

  function save() {
    if (busy || !state) return;
    capture();
    history.replaceState(state, "", hashFor(state.trail));
  }

  function restore(entry) {
    const section = sectionFor(entry);
    const view = cache.get(entry.key) || entry.view;
    const details = section.querySelector("details");
    if (details) details.open = !!view?.evidence;
    const diagram = section.querySelector(".diagram-scroll");
    if (diagram) diagram.scrollLeft = view?.diagram || 0;
    const code = section.querySelector("pre");
    if (code) {
      code.scrollLeft = view?.codeX || 0;
      code.scrollTop = view?.codeY || 0;
    }
    const focus = view?.focus ? document.getElementById(view.focus) : null;
    (focus && section.contains(focus)
      ? focus
      : section.querySelector("h1")
    ).focus({ preventScroll: true });
    scrollTo(view?.x || 0, view?.y || 0);
  }

  function renderChrome() {
    const entry = current();
    breadcrumbs.replaceChildren();
    state.trail.forEach((item, index) => {
      if (index) {
        const separator = document.createElement("span");
        separator.textContent =
          PACKAGE.routes[item.via].kind === "related" ? "↗" : "/";
        separator.setAttribute("aria-hidden", "true");
        breadcrumbs.append(separator);
      }
      const last = index === state.trail.length - 1;
      const crumb = document.createElement(last ? "span" : "button");
      crumb.textContent = PACKAGE.views[item.id].short;
      if (last) crumb.setAttribute("aria-current", "page");
      else crumb.addEventListener("click", () => backTo(index));
      breadcrumbs.append(crumb);
    });
    up.hidden = overview.hidden = state.trail.length === 1;
    context.hidden = !entry.via;
    if (entry.via) {
      const route = PACKAGE.routes[entry.via];
      const parent = state.trail[state.trail.length - 2];
      anchor.querySelector("small").textContent =
        route.kind === "inside"
          ? "Inside · " + PACKAGE.views[parent.id].short
          : "Related view · from " + PACKAGE.views[parent.id].short;
      anchor.querySelector("strong").textContent =
        route.kind === "inside" ? route.label : PACKAGE.views[entry.id].short;
      anchor.style.borderColor =
        route.kind === "inside" ? "var(--accent)" : "var(--rule)";
      anchor.style.background =
        route.kind === "inside" ? "#e5f3f6" : "transparent";
    }
    document.title = PACKAGE.views[entry.id].title + " · " + PACKAGE.brand;
    status.textContent = breadcrumbs.textContent;
  }

  function flightFor(node, rect) {
    const el = document.createElement("div");
    el.className = "flight";
    el.setAttribute("aria-hidden", "true");
    const treatment = getComputedStyle(node.querySelector(".node-box"));
    el.style.cssText = `left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;background:${treatment.fill};border-color:${treatment.stroke}`;
    const label = document.createElement("strong");
    label.textContent = node.dataset.label;
    el.append(label);
    document.body.append(el);
    return el;
  }

  function animate(el, frames, duration, easing = "cubic-bezier(.2,.8,.2,1)") {
    if (reduced.matches || !el.animate) return Promise.resolve();
    const animation = el.animate(frames, {
      duration,
      easing,
      fill: "both",
    });
    animations.add(animation);
    return animation.finished
      .catch((error) => {
        if (error.name !== "AbortError") throw error;
      })
      .finally(() => {
        animation.cancel();
        animations.delete(animation);
      });
  }

  async function show(next, initial = false) {
    const token = ++generation;
    for (const animation of animations) animation.cancel();
    document.querySelectorAll(".flight").forEach((el) => el.remove());
    anchor.style.visibility = "";
    const previous = state;
    const oldEntry = previous?.trail.at(-1);
    const oldSection = oldEntry && sectionFor(oldEntry);
    const target = next.trail.at(-1);
    const isForward =
      oldEntry &&
      next.trail.length === previous.trail.length + 1 &&
      next.trail.at(-2).key === oldEntry.key;
    const isBack =
      oldEntry &&
      previous.trail.length === next.trail.length + 1 &&
      previous.trail.at(-2).key === target.key;
    const via = isForward ? target.via : isBack ? oldEntry.via : null;
    const route = PACKAGE.routes[via];
    const moving = !initial && !reduced.matches && route?.kind === "inside";
    const oldAnchorRect =
      isBack && !context.hidden ? anchor.getBoundingClientRect() : null;
    const oldNode =
      isForward && route?.node
        ? oldSection.querySelector(`[data-node="${route.node}"]`)
        : null;
    let flight =
      moving && oldNode
        ? flightFor(oldNode, oldNode.getBoundingClientRect())
        : null;
    busy = true;
    if (!initial && oldSection)
      await animate(oldSection, [{ opacity: 1 }, { opacity: 0 }], 120);
    if (token !== generation) return;
    state = next;
    for (const [id, section] of sections) section.hidden = id !== target.id;
    renderChrome();
    restore(target);
    const newSection = sectionFor(target);
    if (moving) {
      let from, to;
      if (isForward && flight) {
        from = flight.getBoundingClientRect();
        to = anchor.getBoundingClientRect();
        anchor.style.visibility = "hidden";
      } else if (isBack && oldAnchorRect) {
        const parentNode = newSection.querySelector(
          `[data-node="${route.node}"]`,
        );
        if (parentNode) {
          from = oldAnchorRect;
          to = parentNode.getBoundingClientRect();
          flight = flightFor(parentNode, from);
        }
      }
      if (flight && from && to) {
        await Promise.all([
          animate(
            flight,
            [
              {
                transform: "translate(0, 0)",
                width: `${from.width}px`,
                height: `${from.height}px`,
              },
              {
                transform: `translate(${to.left - from.left}px, ${to.top - from.top}px)`,
                width: `${to.width}px`,
                height: `${to.height}px`,
              },
            ],
            280,
          ),
          animate(
            newSection,
            [
              { opacity: 0, offset: 0 },
              { opacity: 0, offset: 0.67 },
              { opacity: 1, offset: 1 },
            ],
            420,
            "linear",
          ),
        ]);
      }
    } else if (!initial) {
      await animate(newSection, [{ opacity: 0 }, { opacity: 1 }], 160);
    }
    flight?.remove();
    if (token !== generation) return;
    anchor.style.visibility = "";
    busy = false;
    save();
  }

  function navigate(key) {
    if (busy) return;
    const route = PACKAGE.routes[key];
    if (!route || !key.startsWith(current().id + ":")) return;
    save();
    const next = {
      diagramPackage: 1,
      trail: [...state.trail, fresh(route.to, key)],
    };
    history.pushState(next, "", hashFor(next.trail));
    void show(next);
  }

  function backTo(index) {
    if (busy || index === state.trail.length - 1) return;
    save();
    history.go(index - (state.trail.length - 1));
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-route]");
    if (
      !link ||
      event.button ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    navigate(link.dataset.route);
  });
  up.addEventListener("click", () => backTo(state.trail.length - 2));
  overview.addEventListener("click", () => backTo(0));
  document.querySelector(".brand").addEventListener("click", (event) => {
    if (
      event.button ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    backTo(0);
  });
  addEventListener("popstate", (event) => {
    capture();
    if (valid(event.state)) void show(event.state);
    else location.reload();
  });
  addEventListener("scroll", save, { passive: true, capture: true });
  document.addEventListener("focusin", save);
  document.addEventListener("toggle", save, true);
  addEventListener("pagehide", save);
  reduced.addEventListener("change", () => {
    if (reduced.matches) for (const animation of animations) animation.finish();
  });

  toolbar.hidden = false;
  if (valid(history.state) && hashFor(history.state.trail) === location.hash) {
    void show(history.state, true);
  } else {
    const requested = location.hash.slice(1).split("/");
    let seeded = { diagramPackage: 1, trail: [fresh("overview")] };
    history.replaceState(seeded, "", "#overview");
    // Seed a direct deep link with real parent history, so Up still works.
    if (requested[0] === "overview") {
      for (const id of requested.slice(1)) {
        const parent = seeded.trail.at(-1).id;
        const match = Object.entries(PACKAGE.routes).find(
          ([key, route]) => key.startsWith(parent + ":") && route.to === id,
        );
        if (!match) break;
        seeded = {
          diagramPackage: 1,
          trail: [...seeded.trail, fresh(id, match[0])],
        };
        history.pushState(seeded, "", hashFor(seeded.trail));
      }
    }
    void show(seeded, true);
  }
})();
