/* What both pages draw with: small DOM helpers, the tooltip, the timeline of dated copies
   and the scatter plot. Every value reaches the page as text, never as markup. */

export const BASE = "https://w3id.org/welte-premises/";
export const PURL = "https://purl.stanford.edu";
const SVG = "http://www.w3.org/2000/svg";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

export const svg = (tag, attrs = {}) => {
  const node = document.createElementNS(SVG, tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  return node;
};

export const link = (href, text) => {
  const a = el("a", null, text);
  a.href = href;
  return a;
};

/* A date as it reads: a day, or the month or year a partial date gives. */
export const day = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return d ? `${d} ${MONTHS[m - 1]} ${y}` : m ? `${MONTHS[m - 1]} ${y}` : `${y}`;
};

/* A partial date stands at the middle of its month or year. */
const instant = (iso) =>
  iso.length === 10 ? Date.parse(iso) : iso.length === 7 ? Date.parse(`${iso}-15`) : Date.parse(`${iso}-07-01`);

/* A date as a year with its fraction, for an axis of years. */
export const yearOf = (iso) => {
  const t = new Date(instant(iso));
  return t.getUTCFullYear() + (t - Date.UTC(t.getUTCFullYear(), 0, 1)) / (365.25 * 864e5);
};

export const fragment = (id) => id.split("#")[1];

export const beliefOf = (premise) => premise.date["@annotation"].belief;

export const rgb = (c) => `rgb(${c[0]}, ${c[1]}, ${c[2]})`;

export const lab = (v) => `L* ${v[0]} · a* ${v[1]} · b* ${v[2]}`;

/* What a premise holds, in a sentence: the setting or paper, then the bound. */
export function statement(premise) {
  const advance = premise.perforator?.condition?.advance;
  const what = advance ? `Punched with an advance of ${advance.value.toFixed(1)} mm`
    : premise.paper ? `Punched on ${premise.paper.name}` : "Punched";
  const { after, before } = premise.date;
  if (after && before) return `${what}: between ${day(after)} and ${day(before)}`;
  if (before) return `${what}: not after ${day(before)}`;
  return `${what}: not before ${day(after)}`;
}

/* One tooltip for the page: a value, a line, and a muted line. */
const tip = el("div", "tip");

export function installTip() {
  document.body.append(tip);
  addEventListener("scroll", hideTip, { passive: true });
}

export function showTip([value, line, muted], x, y) {
  tip.replaceChildren(el("strong", null, value), el("div", null, line), el("div", "muted", muted));
  tip.classList.add("on");
  const box = tip.getBoundingClientRect();
  const left = Math.min(Math.max(8, x - box.width / 2), window.innerWidth - box.width - 8);
  const top = y - box.height - 14 < 8 ? y + 16 : y - box.height - 14;
  tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
}

export const hideTip = () => tip.classList.remove("on");

const open = (druid) => window.open(`${PURL}/${druid}`, "_blank", "noopener");

/* Redraws a chart when its holder changes width. */
export function responsive(holder, draw) {
  draw();
  new ResizeObserver(() => holder.clientWidth !== Number(holder.firstChild?.getAttribute("width")) && draw())
    .observe(holder);
}

/* Dots placed along their row without overlapping: each takes the nearest free level. */
function swarm(points, spacing) {
  const placed = [];
  points
    .slice()
    .sort((a, b) => a.x - b.x)
    .forEach((p) => {
      for (let k = 0; ; k++) {
        const level = k === 0 ? 0 : (k % 2 ? 1 : -1) * Math.ceil(k / 2);
        const y = level * spacing;
        if (!placed.some((q) => Math.abs(q.x - p.x) < spacing && Math.abs(q.y - y) < spacing)) {
          placed.push({ ...p, y });
          break;
        }
      }
    });
  return placed;
}

/* The pointer, or the arrow keys, pick the nearest mark; a click or Enter opens its scan. */
function hover(chart, hit, marks, tipOf) {
  let current = -1;
  const clear = () => {
    marks.forEach((m) => m.mark.classList.remove("on"));
    hideTip();
  };
  const pick = (i) => {
    marks.forEach((m) => m.mark.classList.remove("on"));
    current = i;
    const m = marks[i];
    m.mark.classList.add("on");
    const box = chart.getBoundingClientRect();
    showTip(tipOf(m.item), box.left + m.x, box.top + m.y);
  };
  const nearest = (px, py) =>
    marks.reduce((best, m, i) =>
      Math.hypot(m.x - px, m.y - py) < Math.hypot(marks[best].x - px, marks[best].y - py) ? i : best, 0);
  hit.addEventListener("pointermove", (e) => {
    const box = chart.getBoundingClientRect();
    pick(nearest(e.clientX - box.left, e.clientY - box.top));
  });
  hit.addEventListener("pointerleave", clear);
  hit.addEventListener("blur", clear);
  hit.addEventListener("click", () => current >= 0 && open(marks[current].item.druid));
  const order = marks.map((m, i) => i).sort((a, b) => marks[a].x - marks[b].x || marks[a].y - marks[b].y);
  hit.addEventListener("keydown", (e) => {
    const at = order.indexOf(current);
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const next = at < 0 ? 0 : Math.min(order.length - 1, Math.max(0, at + (e.key === "ArrowRight" ? 1 : -1)));
      pick(order[next]);
    } else if (e.key === "Enter" && current >= 0) {
      open(marks[current].item.druid);
    }
  });
}

function yearAxis(chart, x, from, to, y, width) {
  chart.append(svg("line", { x1: 0, x2: width, y1: y, y2: y, class: "axis" }));
  const first = new Date(from).getUTCFullYear();
  const last = new Date(to).getUTCFullYear();
  const step = width / (last - first) < 36 ? (width / (last - first) < 18 ? 5 : 2) : 1;
  for (let year = first; year <= last; year++) {
    const tx = x(`${year}-01-01`);
    chart.append(svg("line", { x1: tx, x2: tx, y1: y, y2: y + 4, class: "axis" }));
    if (year % step === 0) {
      const t = svg("text", { x: tx, y: y + 17, class: "tick", "text-anchor": "middle" });
      t.textContent = year;
      chart.append(t);
    }
  }
}

/**
 * Rows of dated copies along one time axis, one row a group. A group that names a
 * premise has the premise's bound drawn across it. `tipOf` gives a copy's tooltip,
 * `fill` its colour where the colour is what is measured.
 */
export function timeline(holder, { groups, premises = [], tipOf, fill }) {
  const width = holder.clientWidth;
  const r = 4;
  const spacing = 2 * r + 2;
  const times = groups.flatMap((g) => g.copies.map((c) => instant(c.date)));
  const from = Date.UTC(new Date(Math.min(...times)).getUTCFullYear(), 0, 1);
  const to = Date.UTC(new Date(Math.max(...times)).getUTCFullYear() + 1, 0, 1);
  const pad = 8;
  const x = (iso) => pad + ((instant(iso) - from) / (to - from)) * (width - 2 * pad);

  const chart = svg("svg", { width, role: "img", "aria-label": "Dated copies over time" });
  holder.replaceChildren(chart);
  let top = 0;

  groups.forEach((group) => {
    const dots = swarm(group.copies.map((c) => ({ item: c, x: x(c.date) })), spacing);
    const reach = Math.max(0, ...dots.map((d) => Math.abs(d.y)));
    const labelY = top + 14;
    const mid = labelY + 16 + reach + r;
    const bottom = mid + reach + r + 18;

    const label = svg("text", { x: 0, y: labelY, class: "row-label" });
    const count = `${group.copies.length} ${group.copies.length === 1 ? "copy" : "copies"}`;
    label.textContent = `${group.label} · ${count}`;
    chart.append(label);
    /* On a narrow screen a row keeps its name and loses the rule that follows it. */
    if (label.getComputedTextLength() > width) label.textContent = `${group.label.split(",")[0]} · ${count}`;

    const premise = premises.find((p) => fragment(p["@id"]) === group.premise);
    if (premise) {
      const { after, before } = premise.date;
      [after, before].filter(Boolean).forEach((bound) =>
        chart.append(svg("line", { x1: x(bound), x2: x(bound), y1: labelY + 6, y2: bottom - 8, class: "bound" })));
      /* The label stands beside the later line, or the earlier where it would run off the chart. */
      const words = after && before ? `between ${day(after)} and ${day(before)}`
        : before ? `not after ${day(before)}` : `not before ${day(after)}`;
      const right = x(before || after) + 6;
      const leftOf = x(after || before) - 6;
      const text = svg("text", { x: right, y: labelY + 20, class: "bound-label", "text-anchor": "start" });
      text.textContent = words;
      chart.append(text);
      /* Beside the later line, else the earlier; where neither has room, shorter and at the edge. */
      if (right + text.getComputedTextLength() > width) {
        if (text.getComputedTextLength() <= leftOf) {
          text.setAttribute("x", leftOf);
          text.setAttribute("text-anchor", "end");
        } else {
          if (after && before) text.textContent = `${day(after)} – ${day(before)}`;
          const w = text.getComputedTextLength();
          text.setAttribute("x", right + w <= width ? right : Math.max(0, leftOf - w));
        }
      }
    }

    const marks = dots.map((d) => {
      const mark = svg("circle", { cx: d.x, cy: mid + d.y, r, class: "dot" });
      if (fill) mark.style.fill = fill(d.item);
      chart.append(mark);
      return { item: d.item, mark, x: d.x, y: mid + d.y };
    });

    const hit = svg("rect", { x: 0, y: labelY + 6, width, height: bottom - labelY - 6, class: "hit", tabindex: 0 });
    hit.setAttribute("aria-label", `${group.label}: ${group.copies.length} dated copies; use the arrow keys`);
    if (marks.length) hover(chart, hit, marks, tipOf);
    chart.append(hit);
    top = bottom;
  });

  yearAxis(chart, x, from, to, top + 4, width);
  chart.setAttribute("height", top + 28);
}

/**
 * Points against two measured axes. `x` and `y` give each axis its range, ticks and
 * label; `guides` draws a rule at a value with a note; `fill` colours a point.
 */
export function scatter(holder, { points, x: xs, y: ys, guides = [], tipOf, fill, height = 320, label }) {
  const width = holder.clientWidth;
  const left = 40, right = 8, top = 24, bottom = 34;
  const x = (v) => left + ((v - xs.min) / (xs.max - xs.min)) * (width - left - right);
  const y = (v) => top + (1 - (v - ys.min) / (ys.max - ys.min)) * (height - top - bottom);
  const chart = svg("svg", { width, height, role: "img", "aria-label": label });
  holder.replaceChildren(chart);

  chart.append(svg("line", { x1: left, x2: width - right, y1: height - bottom, y2: height - bottom, class: "axis" }));
  chart.append(svg("line", { x1: left, x2: left, y1: top, y2: height - bottom, class: "axis" }));
  (xs.ticks || []).forEach((t) => {
    const text = svg("text", { x: x(t), y: height - bottom + 16, class: "tick", "text-anchor": "middle" });
    text.textContent = xs.format ? xs.format(t) : t;
    chart.append(text);
  });
  (ys.ticks || []).forEach((t) => {
    chart.append(svg("line", { x1: left, x2: width - right, y1: y(t), y2: y(t), class: "grid" }));
    const text = svg("text", { x: left - 6, y: y(t) + 4, class: "tick", "text-anchor": "end" });
    text.textContent = t;
    chart.append(text);
  });
  const xl = svg("text", { x: width - right, y: height - 2, class: "tick", "text-anchor": "end" });
  xl.textContent = xs.label;
  const yl = svg("text", { x: 0, y: 10, class: "tick" });
  yl.textContent = ys.label;
  chart.append(xl, yl);

  guides.forEach((g) => {
    const at = g.axis === "x" ? x(g.at) : y(g.at);
    chart.append(svg("line", g.axis === "x"
      ? { x1: at, x2: at, y1: top, y2: height - bottom, class: "guide" }
      : { x1: left, x2: width - right, y1: at, y2: at, class: "guide" }));
    if (g.note) {
      const text = svg("text", g.axis === "x"
        ? { x: at + 4, y: top + 10, class: "guide-label" }
        : { x: width - right, y: at - 4, class: "guide-label", "text-anchor": "end" });
      text.textContent = g.note;
      chart.append(text);
    }
  });

  const marks = points.map((p) => {
    const mark = svg("circle", { cx: x(p.x), cy: y(p.y), r: 4, class: "dot" });
    if (fill) mark.style.fill = fill(p);
    chart.append(mark);
    return { item: p, mark, x: x(p.x), y: y(p.y) };
  });
  const hit = svg("rect", { x: left, y: top, width: width - left - right, height: height - top - bottom, class: "hit", tabindex: 0 });
  hit.setAttribute("aria-label", `${label}; use the arrow keys`);
  if (marks.length) hover(chart, hit, marks, tipOf);
  chart.append(hit);
}

/* Every row of a chart as a table, folded away, so no value needs the pointer. */
export function tableView(caption, head, rows) {
  const details = el("details", "table-view");
  details.append(el("summary", null, caption));
  const table = el("table");
  const tr = el("tr");
  [...head, ""].forEach((h) => tr.append(el("th", null, h)));
  table.append(tr);
  rows.forEach(({ druid, cells }) => {
    const row = el("tr");
    cells.forEach((c) => row.append(el("td", typeof c === "number" ? "num" : null, c ?? "")));
    const cell = el("td");
    cell.append(link(`${PURL}/${druid}`, "Stanford"));
    row.append(cell);
    table.append(row);
  });
  details.append(table);
  return details;
}
