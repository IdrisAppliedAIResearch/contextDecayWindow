"""Generate and hash-lock Study 010's script, plant key, and rubric."""

import hashlib
import json
from pathlib import Path

OUT = Path("experiments/study_010")
INTERIM = {
    250: ("I1", "early"),
    251: ("I2", "recent"),
    252: ("I3", "breadth"),
    500: ("I4", "early"),
    501: ("I5", "recent"),
    502: ("I6", "breadth"),
    750: ("I7", "early"),
    751: ("I8", "recent"),
    752: ("I9", "breadth"),
}
TERMINAL_START = 987

# id, domain name, project, lead, primary value, specification, threshold
DOMAIN_ROWS = [
    ("structural", "structural engineering", "Aster Viaduct", "Dr. Leena Ortiz", "1,126 meters", "HPS 70W steel", "118.6 metric tons per axle"),
    ("epidemiology", "clinical epidemiology", "MERIDIAN-4 cohort", "Dr. Tomas Ilyin", "6,240 participants", "inverse-probability weighting", "1.7% annual incidence"),
    ("archives", "archival history", "Vellum Harbor Ledger", "Professor Amira Solano", "1572", "iron-gall ink", "folio 184"),
    ("battery", "battery chemistry", "Northstar Cell", "Dr. Pavel Nwosu", "4.35 volts", "NMC811 cathode", "92% retention at 1,200 cycles"),
    ("monetary", "monetary economics", "Orchid Corridor model", "Dr. Sanae Morimoto", "2.4% neutral rate", "three-quarter lag rule", "1.8% inflation floor"),
    ("astronomy", "observational astronomy", "Kepler Ridge Array", "Dr. Elias Varga", "18.7 light-years", "1.42 GHz hydrogen line", "0.031 arcsecond resolution"),
    ("ecology", "wetland ecology", "Marrowfen Survey", "Dr. Nia Okafor", "38 hectares", "Sphagnum palustre", "6.2 millimeters per year"),
    ("cryptography", "applied cryptography", "Citrine Handshake", "Dr. Yuki Bhandari", "192-bit security", "ML-KEM-768", "11.8 millisecond median latency"),
    ("geophysics", "marine geophysics", "Pelican Rift Transect", "Dr. Marta Quispe", "4,860 meters depth", "24-channel streamer", "3.6 centimeters per year"),
    ("linguistics", "historical linguistics", "Sable Isogloss Atlas", "Professor Idris Chen", "43 dialect sites", "retroflex lateral marker", "AD 1180 divergence"),
    ("robotics", "field robotics", "Kestrel Rover", "Dr. Hana Petrov", "14.2 kilometer range", "event-camera navigation", "8.5 centimeter obstacle clearance"),
    ("conservation", "materials conservation", "Blue Atrium Mosaic", "Dr. Omar Velasquez", "AD 612", "calcium-caseinate grout", "42% relative humidity"),
]
DOMAINS = [
    dict(
        zip(
            ("id", "name", "project", "person", "value", "spec", "threshold"),
            row,
        )
    )
    for row in DOMAIN_ROWS
]
FILLERS = [
    "Stay within the {name} thread and do not connect it to other subjects. Explain {facet} in two concise sentences.",
    "Stay within the {name} thread and do not connect it to other subjects. Identify one measurement error affecting {facet} and its consequence.",
    "Stay within the {name} thread and do not connect it to other subjects. Briefly compare two validation strategies for {facet}.",
    "Stay within the {name} thread and do not connect it to other subjects. State one practical quality-control check for {facet}.",
    "Stay within the {name} thread and do not connect it to other subjects. Give a short example of uncertainty reporting for {facet}.",
    "Stay within the {name} thread and do not connect it to other subjects. Explain one failure mode involving {facet}.",
    "Stay within the {name} thread and do not connect it to other subjects. Briefly describe provenance documentation for {facet}.",
    "Stay within the {name} thread and do not connect it to other subjects. Name one sensitivity analysis for {facet} and its purpose.",
]
FACETS = {
    "structural": ["aeroelastic flutter", "cable fatigue", "seismic isolation", "deck torsion", "bearing creep", "wind-tunnel scaling", "load combinations", "corrosion monitoring"],
    "epidemiology": ["immortal-time bias", "loss to follow-up", "propensity overlap", "competing risks", "outcome adjudication", "missing covariates", "cluster effects", "negative controls"],
    "archives": ["quire reconstruction", "watermark dating", "scribal hands", "ink corrosion", "provenance gaps", "folio collation", "seal impressions", "marginal annotations"],
    "battery": ["lithium plating", "electrolyte oxidation", "particle cracking", "thermal runaway", "impedance growth", "formation cycling", "state estimation", "gas evolution"],
    "monetary": ["output-gap uncertainty", "policy transmission", "expectation anchoring", "term premia", "balance-sheet effects", "forward guidance", "liquidity traps", "exchange-rate pass-through"],
    "astronomy": ["spectral calibration", "parallax bias", "radio interference", "adaptive optics", "proper motion", "beam synthesis", "flux standards", "atmospheric seeing"],
    "ecology": ["peat accretion", "water-table drawdown", "methane flux", "vegetation quadrats", "nutrient loading", "hydrologic connectivity", "seed-bank recovery", "invasive reeds"],
    "cryptography": ["side-channel leakage", "key encapsulation", "nonce reuse", "certificate rotation", "timing variance", "hybrid negotiation", "entropy sources", "downgrade resistance"],
    "geophysics": ["seismic refraction", "bathymetric correction", "sediment velocity", "magnetic anomalies", "streamer feathering", "navigation drift", "fault inversion", "crustal spreading"],
    "linguistics": ["sound correspondence", "lexical borrowing", "morphological leveling", "isogloss overlap", "dated inscriptions", "semantic shift", "contact zones", "phoneme reconstruction"],
    "robotics": ["visual odometry", "terrain slip", "loop closure", "power budgeting", "sensor fusion", "path replanning", "dust occlusion", "actuator backlash"],
    "conservation": ["salt crystallization", "mortar compatibility", "tessera adhesion", "moisture gradients", "pigment fading", "surface cleaning", "microcracking", "environmental logging"],
}


def plant_prompt(domain: dict, stage: str) -> str:
    if stage == "early":
        return (
            f"For our {domain['name']} case, lock these facts: the project is "
            f"{domain['project']}, led by {domain['person']}, with the primary "
            f"value {domain['value']}. Acknowledge the three facts in a concise "
            "numbered list."
        )
    if stage == "middle":
        return (
            f"Add two locked facts for {domain['project']}: the technical "
            f"specification is {domain['spec']}, and the decision threshold is "
            f"{domain['threshold']}. Restate only those two facts."
        )
    return (
        "Without repeating the values, explain in two sentences why the recorded "
        f"specification and threshold matter to {domain['project']}."
    )


def targeted(domain: dict, label: str) -> dict:
    return {
        "label": label,
        "domain": domain["id"],
        "question": (
            f"For {domain['name']}, name the project and lead, then state the "
            "primary value, technical specification, and decision threshold exactly."
        ),
        "expected": [
            domain["project"],
            domain["person"],
            domain["value"],
            domain["spec"],
            domain["threshold"],
        ],
    }


def breadth(domains: list[dict], label: str, mode: str) -> dict:
    if mode == "names":
        question = (
            f"Across the {len(domains)} subject areas discussed so far, list each "
            "locked project name. Do not omit earlier areas."
        )
        expected = [domain["project"] for domain in domains]
    elif mode == "values":
        question = (
            f"Across all {len(domains)} subject areas, list every locked project "
            "name and one exact numeric value associated with each."
        )
        expected = [
            f"{domain['project']} + {domain['value']}" for domain in domains
        ]
    else:
        question = (
            f"Before we finish, identify all {len(domains)} distinct projects from "
            "our conversation and give the lead person for each."
        )
        expected = [
            f"{domain['project']} + {domain['person']}" for domain in domains
        ]
    return {
        "label": label,
        "domain": "breadth",
        "question": question,
        "expected": expected,
    }


def interim_probe(turn: int, active_domain: int) -> dict | None:
    if turn not in INTERIM:
        return None
    label, kind = INTERIM[turn]
    if kind == "early":
        return targeted(DOMAINS[0], label)
    if kind == "recent":
        return targeted(DOMAINS[active_domain], label)
    return breadth(DOMAINS[: active_domain + 1], label, "names")


def build() -> tuple[dict, list[dict], dict[str, dict[str, int]]]:
    turns: list[dict] = []
    probes: list[dict] = []
    plants: dict[str, dict[str, int]] = {}
    content_index = 0
    content_total = TERMINAL_START - 1 - len(INTERIM)

    for turn in range(1, TERMINAL_START):
        active_index = min(11, content_index * 12 // content_total)
        probe = interim_probe(turn, active_index)
        if probe:
            probes.append(probe | {"turn": turn})
            turns.append(
                {
                    "turn": turn,
                    "user": probe["question"],
                    "ground_truth_domain": "probe",
                    "probe_label": probe["label"],
                }
            )
            continue

        domain = DOMAINS[active_index]
        position = sum(
            item.get("ground_truth_domain") == domain["id"] for item in turns
        )
        domain_plants = plants.setdefault(domain["id"], {})
        stage = None
        if "early" not in domain_plants:
            stage = "early"
        elif position >= 39 and "middle" not in domain_plants:
            stage = "middle"
        elif position >= 74 and "late" not in domain_plants:
            stage = "late"

        if stage:
            user = plant_prompt(domain, stage)
            domain_plants[stage] = turn
        else:
            index = position % len(FILLERS)
            user = FILLERS[index].format(
                name=domain["name"],
                facet=FACETS[domain["id"]][index],
            )
        turns.append(
            {
                "turn": turn,
                "user": user,
                "ground_truth_domain": domain["id"],
                **({"plant_stage": stage} if stage else {}),
            }
        )
        content_index += 1

    for index, domain in enumerate(DOMAINS, start=1):
        probe = targeted(domain, f"Q{index}")
        turn = TERMINAL_START + index - 1
        probes.append(probe | {"turn": turn})
        turns.append(
            {
                "turn": turn,
                "user": probe["question"],
                "ground_truth_domain": "probe",
                "probe_label": probe["label"],
            }
        )
    for turn, probe in (
        (999, breadth(DOMAINS, "Q13", "values")),
        (1000, breadth(DOMAINS, "Q14", "people")),
    ):
        probes.append(probe | {"turn": turn})
        turns.append(
            {
                "turn": turn,
                "user": probe["question"],
                "ground_truth_domain": "probe",
                "probe_label": probe["label"],
            }
        )

    script = {
        "study": "study_010",
        "promotion_flush_turn": 986,
        "probe_turn_start": 987,
        "probe_turn_end": 1000,
        "interim_probe_turns": sorted(INTERIM),
        "emission_guard_turns": sorted(INTERIM) + list(range(987, 1001)),
        "rubric_turns": sorted(INTERIM) + list(range(987, 1001)),
        "condition_note": (
            "Locked 1,000-turn user-only script; assistant messages are generated."
        ),
        "system_prompt": (
            "You are a concise technical research assistant. Preserve exact "
            "user-supplied project facts across long conversations. Keep non-probe "
            "answers brief."
        ),
        "turns": turns,
    }
    assert len(turns) == 1000
    assert content_index == content_total
    assert [item["turn"] for item in turns] == list(range(1, 1001))
    assert all(set(("early", "middle", "late")) == set(value) for value in plants.values())
    return script, probes, plants


def write_key(plants: dict[str, dict[str, int]]) -> None:
    lines = [
        "# Study 010 Locked Plant Key",
        "",
        "Measurement-only. This file must never enter a retrieval path.",
        "",
        "| Domain | Project | Lead | Primary value | Specification | Threshold | Plant turns |",
        "|---|---|---|---|---|---|---|",
    ]
    for domain in DOMAINS:
        turns = plants[domain["id"]]
        lines.append(
            f"| {domain['name']} | {domain['project']} | {domain['person']} | "
            f"{domain['value']} | {domain['spec']} | {domain['threshold']} | "
            f"{turns['early']}, {turns['middle']}, {turns['late']} |"
        )
    (OUT / "q_facts_key_1000.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_rubric(probes: list[dict]) -> None:
    lines = [
        "# Study 010 Locked Rubric",
        "",
        "**Scale:** 0 / 0.5 / 1.0",
        "",
        "Targeted: 1.0 = all five expected items; 0.5 = three or four; "
        "0.0 = zero to two or cross-domain attribution.",
        "",
        "Breadth: 1.0 = at least 80% of expected paired anchors; "
        "0.5 = at least 60%; 0.0 = below 60% or an asserted absent domain.",
        "",
        "| Label | Turn | Type/domain | Expected locked items |",
        "|---|---:|---|---|",
    ]
    for probe in probes:
        lines.append(
            f"| {probe['label']} | {probe['turn']} | {probe['domain']} | "
            f"{'; '.join(probe['expected'])} |"
        )
    (OUT / "rubric_1000.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def sha(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def main() -> None:
    script, probes, plants = build()
    script_path = OUT / "script_1000.json"
    script_path.write_text(
        json.dumps(script, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    write_key(plants)
    write_rubric(probes)
    lock = {
        "status": "LOCKED_BEFORE_CALIBRATION",
        "hash_mode": "SHA-256 of UTF-8 decoded text normalized to LF",
        "artifacts": {
            name: sha(OUT / name)
            for name in (
                "script_1000.json",
                "q_facts_key_1000.md",
                "rubric_1000.md",
            )
        },
        "turn_count": 1000,
        "rubric_turn_count": len(probes),
        "interim_probe_turns": sorted(INTERIM),
        "terminal_probe_turns": list(range(987, 1001)),
    }
    (OUT / "artifact_lock.json").write_text(
        json.dumps(lock, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
