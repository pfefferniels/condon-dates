const STACKS = "https://stacks.stanford.edu/image/iiif";
const PURL = "https://purl.stanford.edu";

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

const crop = (druid, roll, size) =>
  `${STACKS}/${druid}%2F${druid}_0001/${roll.box}/${size}/${roll.rot}/default.jpg`;

const link = (druid) => `${PURL}/${druid}`;

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
  card.href = link(druid);
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
  anchor.href = link(druid);
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
  data.singles.forEach(({ druid, reading }) =>
    strip.append(signature(druid, data.rolls[druid], reading)));
  document.getElementById("singles").append(strip);
}

async function main() {
  const data = await (await fetch("data/rolls.json")).json();
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
}

main();
