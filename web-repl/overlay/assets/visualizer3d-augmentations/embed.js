/**
 * Praxis Visualizer3D embed mode (task C4; spec D12 "Embed mode").
 *
 * Loaded as a module at the end of the vendored page's <body> (index.html carries the tag).
 * It runs only when `location.search` has `embed=1`, which the shell's deck panel writes in the
 * iframe `src` (`?embed=1&view=top&viewer=<id>`). `viewer` is read by socket.js; here it is only
 * echoed in what is forwarded to the parent, so the shell can ignore a page it no longer shows.
 *
 * What it does, from inside the page, without editing any vendored file:
 *   - marks the document (`class="praxis-embed"`, `data-praxis-embed="1"` on <html>) and injects
 *     the sibling stylesheet `embed.css`, which hides the page's own chrome (navbar, left tool
 *     rail, stats footer, tree and its toggle strip) and sets the page ground to #EEF1F4. The
 *     header and footer of the deck panel belong to the shell;
 *   - forwards the page's `plr:status` and `plr:gone` events (static/transport.js:35, 74) to the
 *     parent window as `praxis:dock-status` CustomEvents, because the navbar that normally shows
 *     the status is hidden. `detail` is `{event: "plr:status", connected: boolean, viewer}` or
 *     `{event: "plr:gone", viewer}`, with `viewer` null when the page has none.
 */

export const EMBED_CLASS = "praxis-embed";
export const EMBED_ATTR = "data-praxis-embed";
export const DOCK_STATUS_EVENT = "praxis:dock-status";

function forwardToParent(win, detail) {
  try {
    const parent = win.parent;
    if (!parent || parent === win) return;
    const Ctor = parent.CustomEvent || win.CustomEvent;
    parent.dispatchEvent(new Ctor(DOCK_STATUS_EVENT, { detail }));
  } catch (error) {
    console.warn("the deck view could not tell its panel about the connection:", error);
  }
}

/**
 * Install embed mode on a page. Browser dependencies are injectable (`win`, `doc`, `cssHref`)
 * so that bun can exercise it. Returns `{active}`; it is idempotent.
 */
export function installEmbed(options = {}) {
  const win = options.win || window;
  const doc = options.doc || document;
  const params = new URLSearchParams(win.location.search);
  if (params.get("embed") !== "1") return { active: false };

  const root = doc.documentElement;
  if (root.getAttribute(EMBED_ATTR) === "1") return { active: true };
  root.classList.add(EMBED_CLASS);
  root.setAttribute(EMBED_ATTR, "1");

  const link = doc.createElement("link");
  link.setAttribute("rel", "stylesheet");
  link.setAttribute("href", options.cssHref || new URL("./embed.css", import.meta.url).href);
  doc.head.appendChild(link);

  const viewer = params.get("viewer") || null;
  win.addEventListener("plr:status", (event) => {
    const connected = !!(event && event.detail && event.detail.connected);
    forwardToParent(win, { event: "plr:status", connected, viewer });
  });
  win.addEventListener("plr:gone", () => {
    forwardToParent(win, { event: "plr:gone", viewer });
  });
  return { active: true };
}

if (typeof document !== "undefined" && typeof window !== "undefined") installEmbed();
