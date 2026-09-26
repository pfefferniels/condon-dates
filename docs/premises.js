const BASE = "https://w3id.org/welte-premises/";
const PURL = "https://purl.stanford.edu";
const SVG = "http://www.w3.org/2000/svg";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

const svg = (tag, attrs = {}) => {
  const node = document.createElementNS(SVG, tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  return node;
};

const link = (href, text) => {
  const a = el("a", null, text);
  a.href = href;
  return a;
};

const day = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
};

/* A premise's IRI names its node in premises.jsonld; its fragment is its anchor here. */
const fragment = (id) => id.split("#")[1];

/* An evidence IRI stands on w3id, which serves the file beside this page. */
const evidencePath = (iri) =>
  iri.startsWith(`${BASE}evidence/`) ? `evidence/${iri.slice(BASE.length + 9)}.json` : null;

const beliefOf = (premise) => premise.date["@annotation"].belief;

/* What the premise holds, in a sentence: the setting or paper, then the bound. */
function statement(premise) {
  const advance = premise.perforator?.condition?.advance;
  const what = advance ? `Punched with an advance of ${advance.value.toFixed(1)} mm` : "Punched";
  const { after, before } = premise.date;
  if (after && before) return `${what}: between ${day(after)} and ${day(before)}`;
  if (before) return `${what}: not after ${day(before)}`;
  return `${what}: not before ${day(after)}`;
}

/* The label a used file is shown by: a repository file at its commit, else the link itself. */
function usedLabel(iri) {
  const blob = iri.match(/github\.com\/pfefferniels\/([^/]+)\/blob\/([0-9a-f]{7})[0-9a-f]*\/(.+)$/);
  if (blob) return [`${blob[3]}`, ` in ${blob[1]} at ${blob[2]}`];
  if (evidencePath(iri)) return ["the dated copies", ` (${iri.slice(BASE.length)})`];
  return [iri, ""];
}

function copyButton(text) {
  const button = el("button", "copy", "Copy");
  button.type = "button";
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = "Copied";
    } catch {
      button.textContent = "Select and copy";
    }
    setTimeout(() => (button.textContent = "Copy"), 1600);
  });
  return button;
}

function field(list, term, ...content) {
  list.append(el("dt", null, term));
  const dd = el("dd");
  dd.append(...content);
  list.append(dd);
}

function drawPremise(premise) {
  const belief = beliefOf(premise);
  const iri = BASE + belief["@id"];
  const block = el("article", "premise");
  block.id = fragment(premise["@id"]);
  const anchor = el("span", "anchor");
  anchor.id = fragment(belief["@id"]);
  block.append(anchor, el("h2", "statement", statement(premise)));

  const facts = el("dl", "facts");
  const code = el("code", null, iri);
  field(facts, "Belief", code, " ", copyButton(iri));
  field(facts, "Held", belief.certainty);
  const company = premise.company;
  const gnd = company?.sameAs?.find((s) => s.includes("d-nb.info/gnd"));
  if (company) field(facts, "Company", gnd ? link(gnd, company.name) : company.name);
  if (premise.system) field(facts, "System", link(premise.system["@id"], premise.system["@id"].split("/").pop()));
  block.append(facts);

  belief.reasons.forEach((reason) => {
    block.append(el("p", "reason", reason.note));
    if (reason.used?.length) {
      const list = el("ul", "used");
      reason.used.forEach((u) => {
        const [name, where] = usedLabel(u);
        const item = el("li");
        const path = evidencePath(u);
        item.append(link(path ? `#evidence-${path.split("/").pop().replace(".json", "")}` : u, name));
        item.append(el("span", "where", where));
        list.append(item);
      });
      block.append(el("p", "rests", "Rests on"), list);
    }
  });
  return block;
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
        const clash = placed.some((q) => Math.abs(q.x - p.x) < spacing && Math.abs(q.y - y) < spacing);
        if (!clash) {
          placed.push({ ...p, y });
          break;
        }
      }
    });
  return placed;
}

const tip = el("div", "tip");

function showTip(copy, quantity, unit, x, y) {
  const value = el("strong", null, `${copy[quantity]} ${unit}`);
  tip.replaceChildren(
    value,
    el("div", null, `Welte ${copy.welte} · ${day(copy.date)}`),
    el("div", "muted", `strength ${copy.strength} · opens at Stanford`)
  );
  tip.classList.add("on");
  const box = tip.getBoundingClientRect();
  const left = Math.min(Math.max(8, x - box.width / 2), window.innerWidth - box.width - 8);
  const top = y - box.height - 14 < 8 ? y + 16 : y - box.height - 14;
  tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
}

const hideTip = () => tip.classList.remove("on");

function drawChart(holder, evidence, premises) {
  const width = holder.clientWidth;
  const r = 4;
  const spacing = 2 * r + 2;
  const all = evidence.groups.flatMap((g) => g.copies.map((c) => c.date));
  const from = Date.UTC(Number(all.reduce((a, b) => (a < b ? a : b)).slice(0, 4)), 0, 1);
  const to = Date.UTC(Number(all.reduce((a, b) => (a > b ? a : b)).slice(0, 4)) + 1, 0, 1);
  const pad = 8;
  const x = (iso) => pad + ((Date.parse(iso) - from) / (to - from)) * (width - 2 * pad);

  const chart = svg("svg", { width, role: "img", "aria-label": `The ${evidence.quantity} of the dated copies over time` });
  holder.replaceChildren(chart);
  let top = 0;

  evidence.groups.forEach((group) => {
    const dots = swarm(group.copies.map((c) => ({ copy: c, x: x(c.date) })), spacing);
    const reach = Math.max(0, ...dots.map((d) => Math.abs(d.y)));
    const labelY = top + 14;
    const mid = labelY + 16 + reach + r;
    const bottom = mid + reach + r + 18;

    const label = svg("text", { x: 0, y: labelY, class: "row-label" });
    label.textContent = `${group.label} · ${group.copies.length} copies`;
    chart.append(label);

    const premise = premises.find((p) => fragment(p["@id"]) === group.premise);
    if (premise) {
      const bound = premise.date.before || premise.date.after;
      const bx = x(bound);
      chart.append(svg("line", { x1: bx, x2: bx, y1: labelY + 6, y2: bottom - 8, class: "bound" }));
      const text = svg("text", {
        x: premise.date.before ? bx - 6 : bx + 6,
        y: labelY + 20,
        class: "bound-label",
        "text-anchor": premise.date.before ? "end" : "start",
      });
      text.textContent = premise.date.before ? `not after ${day(bound)}` : `not before ${day(bound)}`;
      chart.append(text);
      /* A label that would run off the chart goes to the other side of its line. */
      const w = text.getComputedTextLength();
      if (premise.date.before && bx - 6 - w < 0) {
        text.setAttribute("x", bx + 6);
        text.setAttribute("text-anchor", "start");
      } else if (premise.date.after && bx + 6 + w > width) {
        text.setAttribute("x", bx - 6);
        text.setAttribute("text-anchor", "end");
      }
    }

    const marks = dots.map((d) => {
      const mark = svg("circle", { cx: d.x, cy: mid + d.y, r, class: "dot" });
      chart.append(mark);
      return { ...d, mark, cy: mid + d.y };
    });

    const hit = svg("rect", { x: 0, y: labelY + 6, width, height: bottom - labelY - 6, class: "hit", tabindex: 0 });
    hit.setAttribute("aria-label", `${group.label}: ${group.copies.length} dated copies; use the arrow keys`);
    let current = -1;
    const pick = (i, cx, cy) => {
      marks.forEach((m) => m.mark.classList.remove("on"));
      current = i;
      const m = marks[i];
      m.mark.classList.add("on");
      const box = chart.getBoundingClientRect();
      showTip(m.copy, evidence.quantity, evidence.unit, cx ?? box.left + m.x, cy ?? box.top + m.cy);
    };
    const nearest = (px, py) =>
      marks.reduce((best, m, i) =>
        Math.hypot(m.x - px, m.cy - py) < Math.hypot(marks[best].x - px, marks[best].cy - py) ? i : best, 0);
    hit.addEventListener("pointermove", (e) => {
      const box = chart.getBoundingClientRect();
      const i = nearest(e.clientX - box.left, e.clientY - box.top);
      pick(i, box.left + marks[i].x, box.top + marks[i].cy);
    });
    hit.addEventListener("pointerleave", () => {
      marks.forEach((m) => m.mark.classList.remove("on"));
      hideTip();
    });
    hit.addEventListener("click", () => current >= 0 && window.open(`${PURL}/${marks[current].copy.druid}`, "_blank", "noopener"));
    const byDate = marks.map((m, i) => i).sort((a, b) => marks[a].x - marks[b].x);
    hit.addEventListener("keydown", (e) => {
      const at = byDate.indexOf(current);
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const next = at < 0 ? 0 : Math.min(byDate.length - 1, Math.max(0, at + (e.key === "ArrowRight" ? 1 : -1)));
        pick(byDate[next]);
      } else if (e.key === "Enter" && current >= 0) {
        window.open(`${PURL}/${marks[current].copy.druid}`, "_blank", "noopener");
      }
    });
    hit.addEventListener("blur", () => {
      marks.forEach((m) => m.mark.classList.remove("on"));
      hideTip();
    });
    chart.append(hit);
    top = bottom;
  });

  const axisY = top + 4;
  chart.append(svg("line", { x1: 0, x2: width, y1: axisY, y2: axisY, class: "axis" }));
  const firstYear = new Date(from).getUTCFullYear();
  const lastYear = new Date(to).getUTCFullYear();
  const step = width / (lastYear - firstYear) < 36 ? 2 : 1;
  for (let year = firstYear; year <= lastYear; year++) {
    const tx = x(`${year}-01-01`);
    chart.append(svg("line", { x1: tx, x2: tx, y1: axisY, y2: axisY + 4, class: "axis" }));
    if ((year - firstYear) % step === 0) {
      const t = svg("text", { x: tx, y: axisY + 17, class: "tick", "text-anchor": "middle" });
      t.textContent = year;
      chart.append(t);
    }
  }
  chart.setAttribute("height", axisY + 24);
}

function drawTable(evidence) {
  const details = el("details", "table-view");
  const total = evidence.groups.reduce((n, g) => n + g.copies.length, 0);
  details.append(el("summary", null, `All ${total} copies as a table`));
  const table = el("table");
  const head = el("tr");
  ["Welte", "Punched", "Group", `${evidence.quantity} (${evidence.unit})`, "Strength", ""].forEach((h) =>
    head.append(el("th", null, h)));
  table.append(head);
  evidence.groups.forEach((group) =>
    group.copies.forEach((copy) => {
      const row = el("tr");
      row.append(
        el("td", "num", copy.welte),
        el("td", "num", copy.date),
        el("td", null, group.label),
        el("td", "num", copy[evidence.quantity]),
        el("td", "num", copy.strength)
      );
      const cell = el("td");
      cell.append(link(`${PURL}/${copy.druid}`, "Stanford"));
      row.append(cell);
      table.append(row);
    }));
  details.append(table);
  return details;
}

async function drawEvidence(iri, premises) {
  const path = evidencePath(iri);
  const evidence = await (await fetch(path)).json();
  const name = path.split("/").pop().replace(".json", "");
  const section = el("section", "evidence");
  section.id = `evidence-${name}`;
  section.append(el("h2", null, `Evidence: the ${evidence.quantity} of dated copies`));
  section.append(el("p", "rule", `Counted: copies ${evidence.rule}. Each dot is a copy; hover or use the arrow keys for its values, click to open it at Stanford.`));
  const holder = el("div", "timeline");
  section.append(holder, drawTable(evidence));
  document.getElementById("evidence").append(section);
  const users = premises.filter((p) => beliefOf(p).reasons.some((r) => r.used?.includes(iri)));
  const render = () => drawChart(holder, evidence, users);
  render();
  new ResizeObserver(() => holder.clientWidth !== Number(holder.firstChild?.getAttribute("width")) && render())
    .observe(holder);
}

async function main() {
  const catalogue = await (await fetch("premises.jsonld")).json();
  const premises = catalogue.productions;
  document.body.append(tip);
  addEventListener("scroll", hideTip, { passive: true });

  document.getElementById("iri").append(el("code", null, BASE + catalogue["@id"]));
  document.getElementById("published").textContent = catalogue.creation.publicationDate;
  const list = document.getElementById("premises");
  premises.forEach((p) => list.append(drawPremise(p)));

  const evidence = [...new Set(premises.flatMap((p) => beliefOf(p).reasons.flatMap((r) => r.used || [])))]
    .filter(evidencePath);
  for (const iri of evidence) await drawEvidence(iri, premises);

  /* A premise's IRI carries its fragment through w3id; the page is drawn after the
     browser looked for it, so it is found again here. */
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target) {
    const block = target.closest(".premise") || target;
    block.classList.add("target");
    block.scrollIntoView();
  }
}

main();
