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

function rollCard(druid, roll) {
  const card = el("a", "card");
  card.href = link(druid);
  card.target = "_blank";
  card.rel = "noopener";
  card.append(thumbnail(druid, roll, ",400", 108));
  const meta = el("div", "meta");
  meta.append(el("div", "when", roll.date), el("div", "what", caption(roll)));
  card.append(meta);
  return card;
}

function signature(druid, roll) {
  const anchor = el("a");
  anchor.href = link(druid);
  anchor.target = "_blank";
  anchor.rel = "noopener";
  anchor.title = [roll.inscription, caption(roll)].filter(Boolean).join("\n");
  anchor.append(thumbnail(druid, roll, ",300", 72));
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
    controller.rolls.forEach((druid) => strip.append(signature(druid, data.rolls[druid])));
    block.append(strip);
    registry.append(block);
  });

  const singles = document.getElementById("singles");
  const strip = el("div", "strip");
  data.singles.forEach(({ druid, reading }) => {
    const anchor = signature(druid, data.rolls[druid]);
    if (reading) anchor.title = `${reading}\n${anchor.title}`;
    strip.append(anchor);
  });
  singles.append(strip);
}

async function main() {
  const data = await (await fetch("data/rolls.json")).json();
  const { scanned, dated } = data.totals;

  document.getElementById("count").textContent =
    `Of ${scanned} rolls, ${dated} can be dated.`;
  document.getElementById("generated").textContent = data.generated;

  let buttons;
  buttons = drawChart(data, (year, bar) => showYear(data, year, buttons, bar));
  drawRegistry(data);
}

main();
