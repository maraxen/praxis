// Notebook display prototype: renders PLR outputs from the serialized fixture.
// The shipped version emits the same SVG from Python (_repr_html_); see DESIGN.md.
(() => {
  'use strict';

  const FX = window.PRAXIS_FIXTURE;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const MAXV = FX.max_volume_ul;

  // ---- tree index: name -> { node, x, y } in deck coordinates (mm) ----------
  const index = new Map();
  (function walk(node, ox, oy, parent) {
    const x = ox + (node.location ? node.location.x : 0);
    const y = oy + (node.location ? node.location.y : 0);
    index.set(node.name, { node, x, y, parent });
    for (const c of node.children || []) walk(c, x, y, node.name);
  })(FX.deck, 0, 0, null);

  const byName = (n) => index.get(n);

  // ---- deck states the notebook steps through ------------------------------
  const allTips = Object.fromEntries(Object.keys(FX.tips).map((k) => [k, true]));
  const fill = (v) => Object.fromEntries(Object.keys(FX.volumes.source).map((k) => [k, v]));
  const STATES = {
    empty: { vols: { source: fill(0), assay: fill(0) }, tips: allTips },
    filled: { vols: { source: fill(200), assay: fill(0) }, tips: allTips },
    after: { vols: FX.volumes, tips: FX.tips },
  };

  // ---- small helpers --------------------------------------------------------
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };
  const title = (node, text) => {
    el('title', {}, node).textContent = text;
  };
  const fmt = (n) => n.toLocaleString('en-US', { maximumFractionDigits: 1 });
  const h = (html) => {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  };
  const wellsOf = (plate) =>
    Object.entries(plate.ordering).map(([id, childName]) => ({ id, node: byName(childName).node }));

  // Liquid disk radius: area proportional to volume, so half full looks half full.
  const liquidR = (r, v) => r * Math.sqrt(Math.max(0, Math.min(1, v / MAXV)));

  // ---- labware drawn in local mm coordinates (y up, flipped by the caller) ----
  function drawPlateBody(g, plate, vols, H, marks = {}) {
    el('rect', {
      class: 'sv-plate', x: 0, y: 0, width: plate.size_x, height: plate.size_y, rx: 2,
    }, g);
    for (const { id, node } of wellsOf(plate)) {
      const r = node.size_x / 2;
      const cx = node.location.x + r;
      const cy = H - (node.location.y + node.size_y / 2);
      const v = vols[id] || 0;
      const w = el('g', {}, g);
      el('circle', { class: 'sv-well', cx, cy, r }, w);
      if (v > 0) el('circle', { class: 'sv-liquid', cx, cy, r: liquidR(r, v) }, w);
      if (marks.changed && marks.changed.has(id)) el('circle', { class: 'sv-changed', cx, cy, r: r + 0.9 }, w);
      if (marks.fault && marks.fault.has(id)) el('circle', { class: 'sv-fault', cx, cy, r: r + 1 }, w);
      title(w, `${plate.name} ${id}: ${v > 0 ? fmt(v) + ' µL' : 'empty'}`);
    }
  }

  function drawTipsBody(g, rack, tips, H) {
    el('rect', { class: 'sv-plate', x: 0, y: 0, width: rack.size_x, height: rack.size_y, rx: 2 }, g);
    for (const [id, childName] of Object.entries(rack.ordering)) {
      const s = byName(childName).node;
      const cx = s.location.x + s.size_x / 2;
      const cy = H - (s.location.y + s.size_y / 2);
      const t = el('g', {}, g);
      if (tips[id]) {
        el('circle', { class: 'sv-tip-ring', cx, cy, r: 3.3 }, t);
        el('circle', { class: 'sv-tip', cx, cy, r: 1.5 }, t);
      } else {
        el('circle', { class: 'sv-tip-gone', cx, cy, r: 3.3 }, t);
      }
      title(t, `${rack.name} ${id}: ${tips[id] ? 'tip' : 'used'}`);
    }
  }

  // ---- standalone plate / tip rack figure with A-H, 1-12 addresses ----------
  function labwareFigure(name, { state = 'after', scale = 3, marks = {} } = {}) {
    const { node } = byName(name);
    const pad = { l: 16, t: 14, r: 4, b: 4 };
    const W = node.size_x + pad.l + pad.r;
    const H = node.size_y + pad.t + pad.b;
    const svg = el('svg', {
      viewBox: `0 0 ${W} ${H}`, width: W * scale, height: H * scale, role: 'img',
      'aria-label': `${name}, top view`,
    });
    const g = el('g', { transform: `translate(${pad.l} ${pad.t})`, 'data-res': name }, svg);
    const st = STATES[state];
    if (node.type === 'TipRack') drawTipsBody(g, node, st.tips, node.size_y);
    else drawPlateBody(g, node, st.vols[name], node.size_y, marks);

    // Addresses: the real well coordinates, so they are information, not decoration.
    const cols = new Map();
    const rows = new Map();
    for (const [id, childName] of Object.entries(node.ordering)) {
      const c = byName(childName).node;
      const m = id.match(/^([A-Z]+)(\d+)$/);
      cols.set(m[2], c.location.x + c.size_x / 2);
      rows.set(m[1], node.size_y - (c.location.y + c.size_y / 2));
    }
    const lab = { class: 'sv-grid', style: `font-size:${11 / scale * 1.05}px` };
    for (const [n, x] of cols) el('text', { ...lab, x: pad.l + x, y: pad.t - 4, 'text-anchor': 'middle' }, svg).textContent = n;
    for (const [n, y] of rows) el('text', { ...lab, x: pad.l - 5, y: pad.t + y + 1.3, 'text-anchor': 'end' }, svg).textContent = n;
    const fig = document.createElement('figure');
    fig.className = 'draw draw--labware';
    fig.appendChild(svg);
    return fig;
  }

  // ---- deck plan ------------------------------------------------------------
  const RAIL0 = 100;
  const RAIL_PITCH = 22.5;

  function deckFigure({ state = 'after', width = 820, focus = null, compact = false } = {}) {
    const deck = FX.deck;
    const H = deck.size_y;
    const minX = -70;
    const maxX = compact ? 860 : deck.size_x + 10;
    const rulerH = compact ? 26 : 34;
    const svg = el('svg', {
      // Crop to the band labware can occupy: nothing sits behind y = 580 or in front of y = 40.
      viewBox: `${minX} ${H - 600} ${maxX - minX} ${560 + rulerH}`, width,
      role: 'img', 'aria-label': 'Deck, top view, front edge at the bottom',
    });
    const Y = (y, sy = 0) => H - y - sy;
    const st = STATES[state];

    // Rails and their ruler along the front edge. Every fifth rail is numbered.
    const rails = deck.num_rails || 30;
    const railTop = 63 + 497;
    for (let r = 1; r <= rails; r++) {
      const x = RAIL0 + (r - 1) * RAIL_PITCH;
      const major = r === 1 || r % 5 === 0;
      el('line', { class: 'sv-rail' + (major ? ' sv-rail--major' : ''), x1: x, x2: x, y1: Y(railTop), y2: Y(63) }, svg);
      el('line', { class: 'sv-rail' + (major ? ' sv-rail--major' : ''), x1: x, x2: x, y1: H + 3, y2: H + (major ? 11 : 7) }, svg);
      if (major) {
        el('text', { class: 'sv-grid', x, y: H + 11 + (compact ? 12 : 13), 'text-anchor': 'middle', style: `font-size:${compact ? 15 : 13}px` }, svg).textContent = r;
      }
    }
    el('line', { class: 'sv-rail', x1: RAIL0, x2: RAIL0 + (rails - 1) * RAIL_PITCH, y1: H + 3, y2: H + 3 }, svg);

    for (const child of deck.children) {
      const { x, y } = byName(child.name);
      const isCarrier = /Carrier$/.test(child.type);
      const g = el('g', { 'data-res': child.name, class: focus === child.name ? 'is-focus' : undefined }, svg);
      const w = Math.max(child.size_x, 6);
      el('rect', {
        class: isCarrier ? 'sv-carrier' : 'sv-fixture',
        x: x, y: Y(y, child.size_y), width: w, height: child.size_y, rx: isCarrier ? 3 : 2,
      }, g);
      title(g, `${child.name} (${child.type})`);

      if (isCarrier) {
        el('text', { class: 'sv-label', x: x + child.size_x / 2, y: Y(y, child.size_y) - 8, 'text-anchor': 'middle', style: `font-size:${compact ? 20 : 16}px` }, svg).textContent = child.name;
        for (const holder of child.children) {
          for (const lw of holder.children || []) drawOnDeck(svg, lw, st, Y, focus);
        }
      } else {
        for (const sub of child.children || []) {
          const s = byName(sub.name);
          el('rect', { class: 'sv-fixture', x: s.x, y: Y(s.y, sub.size_y), width: sub.size_x, height: sub.size_y, rx: 1.5 }, svg);
        }
        if (child.size_y > 80) {
          el('text', {
            class: 'sv-label sv-label--soft', x: x + w / 2, y: Y(y, child.size_y) - 8, 'text-anchor': 'middle', style: `font-size:${compact ? 18 : 14}px`,
          }, svg).textContent = child.name;
        }
      }
    }

    const fig = document.createElement('figure');
    fig.className = 'draw';
    fig.appendChild(svg);
    return fig;
  }

  function drawOnDeck(svg, lw, st, Y, focus) {
    const { x, y } = byName(lw.name);
    const g = el('g', {
      'data-res': lw.name,
      transform: `translate(${x} ${Y(y, lw.size_y)})`,
      class: focus === lw.name ? 'is-focus' : undefined,
    }, svg);
    if (lw.type === 'TipRack') drawTipsBody(g, lw, st.tips, lw.size_y);
    else drawPlateBody(g, lw, st.vols[lw.name] || {}, lw.size_y);
    el('text', { class: 'sv-label', x: lw.size_x + 5, y: lw.size_y / 2 + 4, style: `font-size:${14}px` }, g).textContent = lw.name;
  }

  // ---- output grammar: name line + drawing + summary sentence --------------
  function nameLine(node, extra = '') {
    return h(`<div class="res__name">
      <span class="res__title">${node.name}</span>
      <span class="res__type">${node.type}</span>
      ${node.model ? `<span class="res__model">${node.model}</span>` : ''}${extra}
    </div>`);
  }

  function plateSummary(name, state) {
    const vols = Object.values(STATES[state].vols[name]);
    const held = vols.filter((v) => v > 0);
    const total = held.reduce((a, b) => a + b, 0);
    if (!held.length) return `All ${vols.length} wells are empty. Each holds up to ${fmt(MAXV)} µL.`;
    const lo = Math.min(...held);
    const hi = Math.max(...held);
    const range = lo === hi ? `${fmt(lo)} µL each` : `${fmt(lo)}–${fmt(hi)} µL`;
    const count = held.length === vols.length ? `All ${vols.length} wells hold liquid` : `${held.length} of ${vols.length} wells hold liquid`;
    return `${count}, ${range}. ${fmt(total)} µL in the plate.`;
  }

  function tipSummary(state) {
    const t = STATES[state].tips;
    const ids = Object.keys(t);
    const left = ids.filter((k) => t[k]).length;
    const usedCols = [...new Set(ids.filter((k) => !t[k]).map((k) => +k.slice(1)))].sort((a, b) => a - b);
    const used = usedCols.length
      ? ` Column${usedCols.length > 1 ? 's' : ''} ${usedCols.length > 1 ? `${usedCols[0]}–${usedCols[usedCols.length - 1]}` : usedCols[0]} used.`
      : '';
    return `${left} of ${ids.length} tips left.${used}`;
  }

  const OUTPUTS = {
    deck(state) {
      const d = FX.deck;
      const wrap = document.createElement('div');
      wrap.append(nameLine(d, `<span class="res__model">${d.num_rails} rails</span>`));
      wrap.append(deckFigure({ state, width: 820 }));
      const labware = [...index.values()].filter((e) => ['Plate', 'TipRack'].includes(e.node.type) && e.parent && /-\d+$/.test(e.parent));
      wrap.append(h(`<p class="res__summary">Tip carrier on rail 3, plate carrier on rail 9. ${labware.length} pieces of labware: ${labware.map((e) => e.node.name).join(', ')}.</p>`));
      return wrap;
    },
    plate(name, state, marks) {
      const wrap = document.createElement('div');
      wrap.append(nameLine(byName(name).node));
      wrap.append(labwareFigure(name, { state, marks }));
      wrap.append(h(`<p class="res__summary">${plateSummary(name, state)}</p>`));
      return wrap;
    },
    tips(name, state) {
      const wrap = document.createElement('div');
      wrap.append(nameLine(byName(name).node));
      wrap.append(labwareFigure(name, { state, scale: 3 }));
      wrap.append(h(`<p class="res__summary">${tipSummary(state)}</p>`));
      return wrap;
    },
    ledger() {
      const ACT = { pick_up_tips: 'Pick up tips', aspirate: 'Aspirate', dispense: 'Dispense', discard_tips: 'Discard tips' };
      const maxVol = Math.max(...FX.ops.filter((o) => o.volume_ul).map((o) => o.volume_ul));
      const rows = FX.ops.map((o, i) => {
        const where = o.target.replace(/ col (\d+)$/, ', column $1');
        const vol = o.volume_ul
          ? `<span class="vbar" style="width:${Math.round((o.volume_ul / maxVol) * 56)}px"></span>${fmt(o.volume_ul)} µL each`
          : '';
        return `<tr data-step="${i + 1}" class="${o.op === 'pick_up_tips' ? 'cycle-start' : ''}">
          <td class="step">${i + 1}</td><td class="act">${ACT[o.op]}</td>
          <td class="where">${where}</td><td class="vol">${vol}</td><td class="ch">${o.channels}</td></tr>`;
      }).join('');
      const moved = FX.ops.filter((o) => o.op === 'dispense').reduce((a, o) => a + o.volume_ul * o.channels, 0);
      const wrap = document.createElement('div');
      wrap.append(h(`<div class="res__name"><span class="res__title">run</span><span class="res__type">${FX.ops.length} steps, 3 tip cycles, ${fmt(moved)} µL moved</span></div>`));
      wrap.append(h(`<table class="ledger"><thead><tr><th class="step"></th><th>Action</th><th>Where</th><th>Volume</th><th class="ch">Channels</th></tr></thead><tbody>${rows}</tbody></table>`));
      const changed = new Set(Object.entries(FX.volumes.assay).filter(([, v]) => v > 0).map(([k]) => k));
      const after = document.createElement('div');
      after.className = 'after';
      after.append(h('<p class="after__label">The assay plate after the run. Wells this run changed are outlined.</p>'));
      after.append(OUTPUTS.plate('assay', 'after', { changed }));
      wrap.append(after);
      wrap.append(h(`<details class="tb"><summary>Show backend log (${FX.ops.length * 11} lines)</summary><pre>Picking up tips:
pip#  resource             offset           tip type     max volume (µL)  fitting depth (mm)   tip length (mm)  filter
  p0: tips_300_tipspot_A1  0,0,0            HamiltonTip  360              8                    59.9             Yes
  ...</pre></details>`));
      return wrap;
    },
    error() {
      const e = FX.error;
      const m = e.message.match(/([\d.]+)uL > ([\d.]+)uL/);
      const asked = m ? +m[1] : null;
      const held = m ? +m[2] : null;
      const fault = new Set(['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']);
      const wrap = document.createElement('div');
      wrap.append(h(`<p class="err__title">Not enough liquid in assay A1:H1.</p>`));
      wrap.append(h(`<p class="err__body">Each well holds ${fmt(held)} µL; the aspirate asked for ${fmt(asked)} µL. Nothing was aspirated, and the 8 tips from column 4 are still on the channels.</p>`));
      wrap.append(labwareFigure('assay', { state: 'after', scale: 2, marks: { fault } }));
      wrap.append(h(`<p class="err__fix">Lower <code>vols</code> to ${fmt(held)} µL or less, or aspirate from <code>source</code>, which holds 150 µL in column 1.</p>`));
      wrap.append(h(`<p class="err__plr">PyLabRobot raised <code>${e.type}: ${e.message}</code></p>`));
      const d = h('<details class="tb"><summary>Show traceback</summary><pre></pre></details>');
      d.querySelector('pre').textContent = e.traceback;
      wrap.append(d);
      return wrap;
    },
  };

  // ---- syntax colouring (Python subset, enough for the prototype) -------------
  const KW = new Set('from import await async for in with as def return if else True False None'.split(' '));
  function highlight(src) {
    const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    return src.replace(/(#[^\n]*)|(f?"[^"\n]*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)(\s*\()?|([^#"\w]+)/g,
      (all, com, str, num, word, paren, rest) => {
        if (com) return `<span class="tok-com">${esc(com)}</span>`;
        if (str) return `<span class="tok-str">${esc(str)}</span>`;
        if (num) return `<span class="tok-num">${num}</span>`;
        if (word) {
          if (KW.has(word)) return `<span class="tok-kw">${word}</span>${paren || ''}`;
          if (paren) return `<span class="tok-call">${word}</span>${paren}`;
          return word;
        }
        return esc(rest || all);
      });
  }
  document.querySelectorAll('pre.code').forEach((pre) => {
    pre.innerHTML = highlight(pre.textContent.replace(/^\n/, ''));
  });

  // ---- mount outputs ----------------------------------------------------------
  document.querySelectorAll('[data-output]').forEach((slot) => {
    const [kind, ...args] = slot.dataset.output.split(':');
    slot.append(OUTPUTS[kind](...args));
  });

  // ---- dock: live Visualizer3D when ?viewer= is given, else the plan ----------
  const view = document.querySelector('.dock__view');
  const selText = document.querySelector('.dock__sel');
  const viewerUrl = new URLSearchParams(location.search).get('viewer');
  let focus = 'assay';

  function renderDock() {
    if (viewerUrl) return;
    view.replaceChildren(deckFigure({ state: 'after', width: 1000, focus, compact: true }));
  }
  if (viewerUrl) {
    const frame = document.createElement('iframe');
    frame.className = 'dock__frame';
    frame.title = 'Deck, 3D view';
    frame.src = viewerUrl;
    view.replaceChildren(frame);
  }

  function describe(name) {
    const e = byName(name);
    if (!e) return name;
    const n = e.node;
    if (n.type === 'Plate') return `<strong>${name}</strong> ${plateSummary(name, 'after')}`;
    if (n.type === 'TipRack') return `<strong>${name}</strong> ${tipSummary('after')}`;
    return `<strong>${name}</strong> ${n.type}, ${fmt(n.size_x)} by ${fmt(n.size_y)} mm.`;
  }

  function setFocus(name) {
    focus = name;
    document.querySelectorAll('[data-res]').forEach((g) => g.classList.toggle('is-focus', g.dataset.res === name));
    selText.innerHTML = describe(name);
    renderDock();
  }
  document.addEventListener('click', (ev) => {
    const g = ev.target.closest('[data-res]');
    if (g) setFocus(g.dataset.res);
  });

  // Follow toggle and view presets.
  document.querySelectorAll('.switch').forEach((s) => s.addEventListener('click', () => {
    s.setAttribute('aria-checked', s.getAttribute('aria-checked') === 'true' ? 'false' : 'true');
  }));
  // Presets map to the page's own ?view= values; they drive the live viewer only.
  const segs = [...document.querySelectorAll('.seg button')];
  const press = (b) => segs.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  if (viewerUrl) press(segs.find((b) => b.textContent === 'Iso'));
  segs.forEach((b) => b.addEventListener('click', () => {
    press(b);
    const frame = document.querySelector('.dock__frame');
    if (frame) frame.src = viewerUrl.replace(/view=\w+/, `view=${b.textContent.toLowerCase()}`);
  }));

  // Motion scrub: one tick per ledger step, so a row and a moment are the same thing.
  const ticks = document.querySelector('.scrub__ticks');
  const scrubLabel = document.querySelector('.scrub__now');
  FX.ops.forEach((o, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = i + 1;
    b.setAttribute('aria-label', `Step ${i + 1}`);
    if (o.volume_ul) b.classList.add('is-liquid');
    b.addEventListener('click', () => setStep(i));
    ticks.append(b);
  });
  function setStep(i) {
    ticks.querySelectorAll('button').forEach((b, j) => (j === i ? b.setAttribute('aria-current', 'step') : b.removeAttribute('aria-current')));
    document.querySelectorAll('.ledger tr[data-step]').forEach((r) => r.classList.toggle('is-now', +r.dataset.step === i + 1));
    const o = FX.ops[i];
    const where = o.target.replace(/ col (\d+)$/, ', column $1');
    scrubLabel.textContent = `Step ${i + 1}: ${o.op.replace(/_/g, ' ')}, ${where}`;
    const res = o.target.split(' ')[0];
    if (byName(res)) setFocus(res);
  }

  setStep(5);
  setFocus('assay');
})();
