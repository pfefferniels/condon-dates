import {
  BASE, beliefOf, el, fragment, installTip, lab, link, responsive, rgb, statement, tableView, timeline,
} from "./charts.js";

/* An evidence IRI stands on w3id, which serves the file beside this page. */
const evidencePath = (iri) =>
  iri.startsWith(`${BASE}evidence/`) ? `evidence/${iri.slice(BASE.length + 9)}.json` : null;

/* The label a used file is shown by: a repository file at its commit, else the link itself. */
function usedLabel(iri) {
  const blob = iri.match(/github\.com\/pfefferniels\/([^/]+)\/blob\/([0-9a-f]{7})[0-9a-f]*\/(.+)$/);
  if (blob) return [`${blob[3]}`, ` in ${blob[1]} at ${blob[2]}`];
  if (evidencePath(iri)) return ["the dated copies", ` (${iri.slice(BASE.length)})`];
  if (iri === `${BASE}papers`) return ["the classes of paper", " (papers)"];
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
  field(facts, "Belief", el("code", null, iri), " ", copyButton(iri));
  field(facts, "Held", belief.certainty);
  const company = premise.company;
  const gnd = company?.sameAs?.find((s) => s.includes("d-nb.info/gnd"));
  if (company) field(facts, "Company", gnd ? link(gnd, company.name) : company.name);
  if (premise.system) field(facts, "System", link(premise.system["@id"], premise.system["@id"].split("/").pop()));
  if (premise.paper) field(facts, "Paper", link(`#${fragment(premise.paper["@id"])}`, premise.paper.name));
  block.append(facts);

  belief.reasons.forEach((reason) => {
    block.append(el("p", "reason", reason.note));
    if (reason.used?.length) {
      const list = el("ul", "used");
      reason.used.forEach((u) => {
        const [name, where] = usedLabel(u);
        const path = evidencePath(u);
        const here = path ? `#evidence-${path.split("/").pop().replace(".json", "")}`
          : u === `${BASE}papers` ? "#paper-classes" : u;
        const item = el("li");
        item.append(link(here, name), el("span", "where", where));
        list.append(item);
      });
      block.append(el("p", "rests", "Rests on"), list);
    }
  });
  return block;
}

/* A copy's tooltip, by what its evidence measured. */
const tipOf = (quantity, unit) => (copy) => [
  quantity === "lab" ? lab(copy.lab) : `${copy[quantity]} ${unit}`,
  `Welte ${copy.welte} · ${copy.date}`,
  `${copy.strength != null ? `strength ${copy.strength} · ` : ""}opens at Stanford`,
];

async function drawEvidence(iri, premises) {
  const path = evidencePath(iri);
  const evidence = await (await fetch(path)).json();
  const name = path.split("/").pop().replace(".json", "");
  const paper = evidence.quantity === "lab";
  const section = el("section", "evidence");
  section.id = `evidence-${name}`;
  section.append(el("h2", null, `Evidence: the ${paper ? "paper" : evidence.quantity} of dated copies`));
  section.append(el("p", "rule", `Counted: copies ${evidence.rule}. Each dot is a copy${paper ? ", in the colour of its paper" : ""}; hover or use the arrow keys for its values, click to open it at Stanford.`));
  const holder = el("div", "timeline");
  const strength = evidence.groups.some((g) => g.copies.some((c) => c.strength != null));
  const rows = evidence.groups.flatMap((g) => g.copies.map((c) => ({
    druid: c.druid,
    cells: [c.welte, c.date, g.label, paper ? c.lab.join(" / ") : c[evidence.quantity], ...(strength ? [c.strength] : [])],
  })));
  const total = rows.length;
  section.append(holder, tableView(`All ${total} copies as a table`,
    ["Welte", "Punched", "Group", paper ? "L* / a* / b*" : `${evidence.quantity} (${evidence.unit})`, ...(strength ? ["Strength"] : [])],
    rows));
  document.getElementById("evidence").append(section);
  const users = premises.filter((p) => beliefOf(p).reasons.some((r) => r.used?.includes(iri)));
  responsive(holder, () => timeline(holder, {
    groups: evidence.groups, premises: users, tipOf: tipOf(evidence.quantity, evidence.unit),
    fill: paper ? (c) => rgb(c.rgb) : null,
  }));
}

async function drawPapers() {
  const papers = await (await fetch("papers.jsonld")).json();
  const section = el("section", "papers");
  section.id = "paper-classes";
  section.append(el("h2", null, "Paper classes"));
  section.append(el("p", "rule", papers.comment));
  const list = el("dl", "facts classes");
  papers["@included"].forEach((paper) => {
    const term = el("dt", null, paper.name);
    term.id = fragment(paper["@id"]);
    const broader = paper.broader ? papers["@included"].find((p) => p["@id"] === paper.broader) : null;
    const dd = el("dd", null, paper.comment + (broader ? ` A narrower class of ${broader.name}.` : ""));
    dd.append(" ", el("code", "muted", BASE + paper["@id"]));
    list.append(term, dd);
  });
  section.append(list);
  document.getElementById("evidence").before(section);
}

async function main() {
  const catalogue = await (await fetch("premises.jsonld")).json();
  const premises = catalogue.productions;
  installTip();

  document.getElementById("iri").append(el("code", null, BASE + catalogue["@id"]));
  document.getElementById("published").textContent = catalogue.creation.publicationDate;
  const list = document.getElementById("premises");
  premises.forEach((p) => list.append(drawPremise(p)));
  if (premises.some((p) => p.paper)) await drawPapers();

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
