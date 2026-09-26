import {
  PURL, beliefOf, day, el, fragment, installTip, lab, link as linkTo, responsive, rgb, scatter, statement,
  tableView, timeline, yearOf,
} from "./charts.js";

const STACKS = "https://stacks.stanford.edu/image/iiif";

const crop = (druid, roll, size) =>
  `${STACKS}/${druid}%2F${druid}_0001/${roll.box}/${size}/${roll.rot}/default.jpg`;

const purl = (druid) => `${PURL}/${druid}`;

const caption = (roll) => [roll.performer, roll.title].filter(Boolean).join(" — ");

function thumbnail(druid, roll, size, height) {
  const img = el("img");
  img.src = crop(druid, roll, size);
  img.loading = "lazy";
  img.alt = roll.inscription || "";
  if (height) img.height = height;
  return img;
}

/* Hovering a crop shows the same region at its native resolution. */

const overlay = el("div", "overlay");

function rendered(roll) {
  const [, , w, h] = roll.box.split(",").map(Number);
  return roll.rot % 180 ? { width: h, height: w } : { width: w, height: h };
}

function place(anchor) {
  const gutter = 12;
  const target = anchor.getBoundingClientRect();
  const panel = overlay.getBoundingClientRect();
  const room = window.innerHeight - target.bottom - gutter * 2;
  const left = Math.min(
    Math.max(gutter, target.left + target.width / 2 - panel.width / 2),
    Math.max(gutter, window.innerWidth - panel.width - gutter)
  );
  const top = panel.height <= room
    ? target.bottom + gutter
    : Math.max(gutter, target.top - gutter - panel.height);
  overlay.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
}

function hide() {
  overlay.classList.remove("on");
}

function preview(anchor, druid, roll, reading) {
  let pending;

  const show = () => {
    const size = rendered(roll);
    const full = el("img");
    Object.assign(full, { width: size.width, height: size.height, decoding: "async", alt: "" });
    full.src = crop(druid, roll, "full");
    full.addEventListener("load", () => place(anchor));
    const cap = el("div", "cap");
    if (roll.inscription) cap.append(el("div", "ins", roll.inscription));
    cap.append(el("div", "who",
      [reading, roll.date, caption(roll)].filter(Boolean).join(" · ")));
    overlay.replaceChildren(full, cap);
    overlay.classList.add("on");
    place(anchor);
  };

  const enter = () => {
    clearTimeout(pending);
    pending = setTimeout(show, 110);
  };
  const leave = () => {
    clearTimeout(pending);
    hide();
  };

  anchor.addEventListener("mouseenter", enter);
  anchor.addEventListener("mouseleave", leave);
  anchor.addEventListener("focus", show);
  anchor.addEventListener("blur", leave);
}

function rollCard(druid, roll) {
  const card = el("a", "card");
  card.href = purl(druid);
  card.target = "_blank";
  card.rel = "noopener";
  card.append(thumbnail(druid, roll, ",400", 108));
  const meta = el("div", "meta");
  meta.append(el("div", "when", roll.date), el("div", "what", caption(roll)));
  card.append(meta);
  preview(card, druid, roll);
  return card;
}

function signature(druid, roll, reading) {
  const anchor = el("a");
  anchor.href = purl(druid);
  anchor.target = "_blank";
  anchor.rel = "noopener";
  anchor.append(thumbnail(druid, roll, ",300", 72));
  preview(anchor, druid, roll, reading);
  return anchor;
}

function drawChart(data, onPick) {
  const chart = document.getElementById("chart");
  const labels = el("div", "years");
  const tallest = Math.max(...data.years.map((y) => y.count));
  const buttons = data.years.map(({ year, count }) => {
    const bar = el("button", "bar");
    bar.type = "button";
    bar.setAttribute("aria-pressed", "false");
    bar.setAttribute("aria-label", `${year}, ${count} rolls`);
    bar.disabled = count === 0;
    const fill = el("div", count ? "fill" : "fill empty");
    fill.style.height = `${Math.max(count ? 2 : 1, (count / tallest) * 100)}%`;
    bar.append(el("div", "n", count || ""), fill);
    bar.addEventListener("click", () => onPick(year, bar));
    chart.append(bar);
    labels.append(el("span", null, year));
    return bar;
  });
  chart.after(labels);
  return buttons;
}

function showYear(data, year, buttons, picked) {
  buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === picked)));
  document.getElementById("hint").textContent = `${year}`;
  const panel = document.getElementById("year");
  panel.replaceChildren();
  const grid = el("div", "grid");
  Object.entries(data.rolls)
    .filter(([, roll]) => roll.date && roll.date.startsWith(String(year)))
    .sort((a, b) => a[1].date.localeCompare(b[1].date) || a[1].no - b[1].no)
    .forEach(([druid, roll]) => grid.append(rollCard(druid, roll)));
  panel.append(grid);
}

function drawRegistry(data) {
  const registry = document.getElementById("registry");
  data.controllers.forEach((controller) => {
    const block = el("div", "controller");
    block.id = controller.id;
    const head = el("div", "head");
    head.append(el("span", "label", `Controller ${controller.n}`));
    if (controller.reading) head.append(el("span", "reading", controller.reading));
    head.append(el("span", "tally", `${controller.count} rolls`));
    block.append(head, el("p", "note", controller.note));
    const strip = el("div", "strip");
    controller.rolls.forEach((druid) =>
      strip.append(signature(druid, data.rolls[druid], controller.reading)));
    block.append(strip);
    registry.append(block);
  });

  const strip = el("div", "strip");
  data.singles.forEach(({ druid, reading, note }) => {
    const hand = el("div", "hand");
    hand.append(signature(druid, data.rolls[druid], reading));
    hand.append(el("div", "tag", [reading || "unread", note].filter(Boolean).join(" · ")));
    strip.append(hand);
  });
  document.getElementById("singles").append(strip);
}

/* The paper: its classes with the colour they are measured in, every roll in colour
   space, and the dated copies of each class over time. */
function drawPaper(measures, evidence, premises) {
  const section = document.getElementById("paper");
  const rolls = Object.entries(measures.rolls).filter(([, r]) => r.lab);
  const name = Object.fromEntries(measures.papers.map((p) => [p.id, p.name]));
  section.querySelector(".sub-count").textContent =
    `The paper of ${rolls.length} rolls is measured on the scans, in the colour of its blank paper corrected against the grey card scanned with each.`;

  const classes = el("div", "paper-classes");
  measures.papers.forEach((paper) => {
    const card = el("div", `paper-class${paper.broader ? " narrower" : ""}`);
    const swatch = el("span", "swatch");
    /* A ruled class shows its lines on the swatch: they are what defines it. */
    swatch.style.background = paper.ruled
      ? `repeating-linear-gradient(90deg, rgba(17, 24, 39, 0.6) 0 1px, transparent 1px 5px), ${rgb(paper.rgb)}`
      : rgb(paper.rgb);
    swatch.title = `median colour of its ${paper.count} rolls`;
    const head = el("div", "head");
    head.append(swatch, el("span", "label", paper.name), el("span", "tally", `${paper.count} rolls`));
    card.append(head, el("p", "note", paper.broader ? `${paper.rule}; within ${name[paper.broader]}` : paper.rule));
    if (paper.span) card.append(el("p", "note", `${paper.dated} dated, ${day(paper.span[0])} to ${day(paper.span[1])}`));
    const premise = premises.find((p) => p.paper && fragment(p.paper["@id"]) === paper.id);
    if (premise) {
      const line = el("p", "premise-line");
      line.append(linkTo(`premises.html#${fragment(premise["@id"])}`, statement(premise).split(": ")[1]),
        el("span", "held", ` · held ${beliefOf(premise).certainty}`));
      card.append(line);
    }
    classes.append(card);
  });

  const map = el("div", "scatter");
  const byDate = el("div", "timeline");
  section.append(classes,
    el("h3", null, "Every roll by its colour"),
    el("p", "rule", "Each dot is a roll, in the colour of its paper, placed by how red (a*) and how yellow (b*) it is; the lines are the rules that part the classes. Hover for the values, click to open the scan."),
    map,
    el("h3", null, "The dated copies of each class"),
    el("p", "rule", `Counted: copies ${evidence.rule}. Where a class is a premise, its bounds are drawn.`),
    byDate,
    tableView(`All ${rolls.length} rolls as a table`, ["Welte", "Punched", "Paper", "Ruled", "L* / a* / b*"],
      rolls.map(([druid, r]) => ({
        druid, cells: [r.no, r.date, name[r.batch || r.paper], r.ruled ? "ruled" : "", r.lab.join(" / ")],
      }))));

  const points = rolls.map(([druid, r]) => ({ druid, x: r.lab[1], y: r.lab[2], ...r }));
  responsive(map, () => scatter(map, {
    points, label: "The colour of every measured roll",
    x: { min: -8, max: 38, ticks: [-5, 0, 5, 10, 15, 20, 25, 30, 35], label: "a*, green to red" },
    y: { min: 4, max: 30, ticks: [5, 10, 15, 20, 25], label: "b*, blue to yellow" },
    guides: [{ axis: "x", at: 3, note: "a* 3" }, { axis: "x", at: 10, note: "a* 10" }, { axis: "y", at: 15, note: "b* 15" }],
    fill: (p) => rgb(p.rgb),
    tipOf: (p) => [lab(p.lab), `Welte ${p.no}${p.date ? ` · ${day(p.date)}` : ", not dated"}`,
      `${name[p.batch || p.paper]}${p.ruled ? ", ruled" : ""} · opens at Stanford`],
  }));
  responsive(byDate, () => timeline(byDate, {
    groups: evidence.groups, premises,
    tipOf: (c) => [lab(c.lab), `Welte ${c.welte} · ${day(c.date)}`, "opens at Stanford"],
    fill: (c) => rgb(c.rgb),
  }));
}

/* The perforator: the chain pitch of every dated copy, and the advance of those it resolves on. */
function drawPerforator(measures, evidence, premises) {
  const section = document.getElementById("perforator");
  const dated = Object.entries(measures.rolls).filter(([, r]) => r.date && r.pitch);
  const pitch = el("div", "scatter");
  const advance = el("div", "timeline");
  section.append(
    el("h3", null, "The chain pitch against the date"),
    el("p", "rule", "Each dot is a dated copy. Above 2.75 mm the copy was cut on the wide perforator, below it on the narrow one; the narrow one first appears in February 1914 and the wide one ran beside it until 1917 at least, so a narrow pitch bounds a copy from below and a wide one says little (perforator/README.md)."),
    pitch,
    el("h3", null, "The advance against the date"),
    el("p", "rule", `Counted: copies ${evidence.rule}. The advance halved once, and both premises on it are drawn.`),
    advance,
    tableView(`All ${dated.length} dated copies as a table`, ["Welte", "Punched", "Chain pitch (mm)", "Advance (mm)"],
      dated.map(([druid, r]) => ({ druid, cells: [r.no, r.date, r.pitch, r.advance] }))));
  const points = dated.map(([druid, r]) => ({ druid, x: yearOf(r.date), y: r.pitch, ...r }));
  responsive(pitch, () => scatter(pitch, {
    points, label: "The chain pitch of every dated copy",
    x: { min: 1904, max: 1929, ticks: [1905, 1910, 1915, 1920, 1925], label: "punched" },
    y: { min: 2.2, max: 3.15, ticks: [2.3, 2.5, 2.7, 2.9, 3.1], label: "chain pitch, mm" },
    guides: [{ axis: "y", at: 2.75, note: "wide perforator above, narrow below" }],
    tipOf: (p) => [`${p.pitch} mm`, `Welte ${p.no} · ${day(p.date)}`,
      `${p.advance ? `advance ${p.advance} mm · ` : ""}opens at Stanford`],
  }));
  responsive(advance, () => timeline(advance, {
    groups: evidence.groups, premises,
    tipOf: (c) => [`${c.advance} mm`, `Welte ${c.welte} · ${day(c.date)}`, `strength ${c.strength} · opens at Stanford`],
  }));
}

/* The premises, one line each, with the page that states them in full. */
function drawPremises(premises) {
  const list = el("ul", "premise-list");
  premises.forEach((premise) => {
    const item = el("li");
    item.append(linkTo(`premises.html#${fragment(premise["@id"])}`, statement(premise)),
      el("span", "held", ` · held ${beliefOf(premise).certainty}`));
    list.append(item);
  });
  document.getElementById("premises").append(list);
}

async function main() {
  const [data, measures, catalogue, paperEvidence, advanceEvidence] = await Promise.all(
    ["data/rolls.json", "data/measures.json", "premises.jsonld", "evidence/paper.json", "evidence/advance.json"]
      .map(async (path) => (await fetch(path)).json()));
  const premises = catalogue.productions;
  installTip();
  const { scanned, dated } = data.totals;

  document.body.append(overlay);
  addEventListener("scroll", hide, { passive: true });
  addEventListener("keydown", (e) => e.key === "Escape" && hide());

  document.getElementById("count").textContent =
    `Of ${scanned} rolls, ${dated} can be dated.`;
  document.getElementById("generated").textContent = data.generated;

  let buttons;
  buttons = drawChart(data, (year, bar) => showYear(data, year, buttons, bar));
  drawRegistry(data);
  drawPaper(measures, paperEvidence, premises);
  drawPerforator(measures, advanceEvidence, premises);
  drawPremises(premises);

  /* A hand's IRI on w3id.org/welte-hands arrives here with the hand as the fragment. */
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target) {
    target.classList.add("target");
    target.scrollIntoView();
  }
}

main();
