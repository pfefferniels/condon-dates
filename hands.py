"""The hands that signed the rolls, as authority records for an edition to name.

A hand is a person known by a signature, clustered in hands.json by comparing the
inscription images. It is the one thing about these rolls no authority file holds, so it
gets records of its own; everything else an edition names, the company or a pianist, it
names by the GND. A hand is not a premise: an edition names it as the actor of the act
that wrote an inscription and takes nothing from it to date a copy, since the hand and the
date come off the same inscription (punch-225/README.md).

Each hand has an IRI of its own under https://w3id.org/welte-hands/, made of the id of its
cluster in hands.json, e.g. https://w3id.org/welte-hands/fritz, which w3id redirects to the
one document that describes them all. An id is kept once published, even where the name
read off the signature changes, since the name is a reading and not an identification.

    docs/hands.jsonld            the hands, at https://w3id.org/welte-hands/
"""
import json

BASE = "https://w3id.org/welte-hands/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
REO = "https://w3id.org/reo/context.jsonld"


def document(hands):
    return {
        "@context": [REO, {"comment": "rdfs:comment", "@base": BASE}],
        "@id": BASE,
        "title": "The hands that signed the red Welte rolls of the Condon collection",
        "license": LICENSE,
        "comment": hands["_"],
        "@included": [{"@id": c["id"], "name": c["reading"], "sameAs": [], "comment": c["note"]}
                      for c in hands["clusters"]],
    }


def build(docs, hands):
    target = docs / "hands.jsonld"
    target.write_text(json.dumps(document(hands), ensure_ascii=False, indent=1) + "\n")
    return hands["clusters"]
