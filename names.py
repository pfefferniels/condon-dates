"""The hands that signed the rolls, as authority records for an edition to name.

A hand is a person known by a signature, clustered in hands.json by comparing the
inscription images. It is not a premise: an edition names it as the actor of the act that
wrote an inscription, the way it names a pianist by the GND, and takes nothing from it to
date a copy. The hand and the date come off the same inscription, so a premise about when
a hand signed would date a roll by itself (punch-225/README.md).

The records stand under their own prefix, https://w3id.org/welte-names/, apart from the
premises, since an identity should outlast the evidence that moves a premise. They are
written from here for now; w3id/welte-names/.htaccess is all that changes if they move.

    docs/names/hands.jsonld      the hands, at hands, each at hands#<id>
"""
import json

BASE = "https://w3id.org/welte-names/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
REO = "https://w3id.org/reo/context.jsonld"


def hands_document(hands):
    return {
        "@context": [REO, {"comment": "rdfs:comment", "@base": BASE}],
        "@id": "hands",
        "title": "The hands that signed the red Welte rolls of the Condon collection",
        "license": LICENSE,
        "comment": hands["_"],
        "@included": [{"@id": f"hands#{c['id']}", "name": c["reading"], "sameAs": [],
                       "comment": c["note"]} for c in hands["clusters"]],
    }


def build(docs, hands):
    target = docs / "names" / "hands.jsonld"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(hands_document(hands), ensure_ascii=False, indent=1) + "\n")
    return hands["clusters"]
