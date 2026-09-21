"""Build portable diagrams and the viewer from the same SVG content (stdlib only)."""

import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
REVISION = "d97b5e9b83c0a3962494441542db9e7bbccef881"
DEPENDENCY_REVISION = "9193d476c58037fba7f4d047d03a577e84b6348e"
BASE = f"https://github.com/kirilklein/bonsai-causal/blob/{REVISION}/"
CE_BASE = f"https://github.com/kirilklein/CausalEstimate/blob/{DEPENDENCY_REVISION}/"
PAPER = "#f7fafb"


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def node(
    key,
    x,
    y,
    name,
    sub="",
    tag="",
    kind="",
    width=208,
    height=88,
    destination=None,
    link_kind="inside",
    shape="rect",
):
    return dict(
        id=key,
        x=x,
        y=y,
        name=name,
        sub=sub,
        tag=tag,
        kind=kind,
        width=width,
        height=height,
        destination=destination,
        link_kind=link_kind,
        shape=shape,
    )


def edge(points, label, x, y, dashed=False):
    return dict(points=points, label=label, x=x, y=y, dashed=dashed)


DIAGRAMS = [
    dict(
        id="overview",
        title="What does BONSAI Causal do?",
        short="Overview",
        subtitle="A batch analysis turns patient histories into exposure-effect estimates.",
        description="Local commands or Azure jobs run causal analysis on MEDS data. The analysis calls CausalEstimate with prediction tables and saves effect estimates and diagnostics.",
        nodes=[
            node("local", 80, 144, "Local commands", "python -m corebehrt…", "ENTRY"),
            node("azure", 80, 312, "Azure ML jobs", "pipeline components", "ENTRY"),
            node(
                "meds", 80, 480, "Patient histories", "MEDS shards", "INPUT", "artifact"
            ),
            node(
                "analysis",
                480,
                288,
                "Causal analysis",
                "prepare · predict · estimate",
                "BONSAI CAUSAL",
                "focal",
                width=272,
                height=128,
                destination="analysis",
            ),
            node(
                "estimators",
                944,
                272,
                "CausalEstimate",
                "0.13.0 · Python library",
                "DEPENDENCY",
                "external",
                height=144,
            ),
            node(
                "results",
                944,
                512,
                "Effects & diagnostics",
                "CSV tables + figures",
                "OUTPUT",
                "artifact",
            ),
        ],
        edges=[
            edge([(288, 188), (368, 188), (368, 316), (480, 316)], "RUNS", 424, 298),
            edge([(288, 356), (480, 356)], "RUNS", 372, 338),
            edge(
                [(288, 524), (400, 524), (400, 396), (480, 396)], "SUPPLIES", 356, 506
            ),
            edge([(752, 316), (944, 316)], "PREDICTION TABLE", 848, 298),
            edge([(944, 380), (752, 380)], "RESULT DICTS", 848, 362),
            edge([(616, 416), (616, 556), (944, 556)], "SAVES", 792, 538),
        ],
        related=[("config", "Run configuration & versions", 80, 648)],
        refs=[
            ("Local pipeline entry points", ".github/workflows/causal_pipeline.yml"),
            (
                "Azure artifact wiring",
                "corebehrt/azure/pipelines/FINETUNE_CALIBRATE_ESTIMATE.py",
            ),
            (
                "Estimator caller and table contract",
                "corebehrt/modules/causal/estimate.py",
            ),
            (
                "CausalEstimate 0.13.0 callee",
                CE_BASE + "CausalEstimate/core/multi_estimator.py",
            ),
        ],
    ),
    dict(
        id="analysis",
        title="What happens in one causal analysis?",
        short="One analysis",
        subtitle="The handoffs are patient data, checkpoints, and prediction files.",
        description="Data preparation supplies pretraining and causal cohort preparation. Prepared patients and pretrained weights feed fold training and prediction, followed by calibration and effect estimation.",
        nodes=[
            node(
                "data",
                80,
                288,
                "Prepare patient data",
                "sequences + event labels",
                "PREPARE",
                height=104,
            ),
            node(
                "pretrain",
                392,
                128,
                "Pretrain encoder",
                "masked-token training",
                "LEARN",
            ),
            node(
                "cohort",
                392,
                464,
                "Prepare causal cohort",
                "index dates · A/Y · folds",
                "PREPARE",
                height=104,
            ),
            node(
                "folds",
                704,
                288,
                "Fold training & prediction",
                "checkpoints + predictions",
                "PREDICT",
                "focal",
                height=104,
                destination="fold",
            ),
            node(
                "calibrate",
                1008,
                288,
                "Calibrate probabilities",
                "combined predictions.csv",
                "CALIBRATE",
                height=104,
            ),
            node(
                "estimate",
                1008,
                528,
                "Effect estimation",
                "effects + intervals",
                "ESTIMATE",
                "focal",
                destination="estimation",
            ),
        ],
        edges=[
            edge([(184, 288), (184, 172), (392, 172)], "SEQUENCES", 280, 154),
            edge(
                [(184, 392), (184, 516), (392, 516)],
                "COHORT INPUTS",
                280,
                498,
            ),
            edge([(600, 172), (808, 172), (808, 288)], "PRETRAINED WEIGHTS", 720, 154),
            edge([(600, 516), (808, 516), (808, 392)], "PREPARED PATIENTS", 712, 498),
            edge([(912, 340), (1008, 340)], "CSV", 960, 322),
            edge([(1112, 392), (1112, 528)], "CALIBRATED CSV", 1170, 464),
        ],
        related=[("config", "Run configuration & versions", 80, 648)],
        refs=[
            ("Concrete stage ordering", ".github/workflows/causal_pipeline.yml"),
            (
                "Joint fine-tuning entry point",
                "corebehrt/main_causal/finetune_exp_y.py",
            ),
            (
                "Calibration reads saved predictions",
                "corebehrt/modules/setup/causal/prediction_processor.py",
            ),
            (
                "Azure uses the same artifact chain",
                "corebehrt/azure/pipelines/FINETUNE_CALIBRATE_ESTIMATE.py",
            ),
        ],
    ),
    dict(
        id="fold",
        title="How does one fold produce predictions?",
        short="One fold",
        subtitle="Training writes a checkpoint; prediction reloads it before evaluating patients.",
        description="Training and prediction are separate responsibilities. Training uses the fold's training patients. A saved checkpoint is reloaded for validation and optional test evaluation. Validation predictions are combined across folds for calibration.",
        lanes=[
            ("TRAINING", 80, 100),
            ("PREDICTION", 80, 328),
            ("AGGREGATION", 80, 548),
        ],
        nodes=[
            node(
                "splits",
                200,
                136,
                "Training patients",
                "prepared fold IDs",
                "INPUT",
                "artifact",
            ),
            node(
                "train",
                520,
                136,
                "Fine-tune model",
                "pretrained encoder + A/Y",
                "TRAIN",
                "focal",
                destination="source-fold",
            ),
            node(
                "checkpoint",
                840,
                136,
                "Model checkpoint",
                "saved fold weights",
                "ARTIFACT",
                "artifact",
            ),
            node(
                "validation",
                200,
                364,
                "Evaluation patients",
                "validation / optional test",
                "INPUT",
                "artifact",
            ),
            node(
                "predict",
                520,
                364,
                "Reload & evaluate",
                "factual + flipped exposure",
                "PREDICT",
                "focal",
            ),
            node(
                "predictions",
                840,
                364,
                "Fold predictions",
                "propensity + outcomes",
                "OUTPUT",
                "artifact",
            ),
            node(
                "metrics",
                520,
                572,
                "Prediction metrics",
                "validation / optional test",
                "OUTPUT",
                "artifact",
                height=64,
            ),
            node(
                "combine",
                840,
                572,
                "Combine validation folds",
                "combined_predictions.csv",
                "OUTPUT",
                "artifact",
                height=64,
            ),
        ],
        edges=[
            edge([(408, 180), (520, 180)], "TRAINING DATA", 464, 162),
            edge([(728, 180), (840, 180)], "SAVES", 784, 162),
            edge([(944, 224), (944, 284), (624, 284), (624, 364)], "RELOADS", 784, 266),
            edge([(408, 408), (520, 408)], "EVAL DATA", 464, 390),
            edge([(728, 408), (840, 408)], "SAVES", 784, 390),
            edge([(624, 452), (624, 572)], "SCORES", 668, 516),
            edge([(944, 452), (944, 572)], "COMBINES", 992, 516),
        ],
        related=[
            ("estimation", "Related: use these predictions", 80, 684),
            ("config", "Run configuration & versions", 840, 684),
        ],
        refs=[
            (
                "Training, reload and evaluation",
                "corebehrt/main_causal/helper/finetune_exp_y.py",
            ),
            (
                "Factual and counterfactual prediction",
                "corebehrt/modules/trainer/causal/trainer.py",
            ),
            (
                "Only validation folds are accumulated",
                "corebehrt/modules/setup/causal/prediction_accumulator.py",
            ),
        ],
    ),
    dict(
        id="estimation",
        title="How do predictions become effect estimates?",
        short="Effect estimates",
        subtitle="Configured methods choose the uncertainty route; several methods can run together.",
        description="Load calibrated predictions, optionally filter common support, and prepare each outcome. Dispatch configured methods to bootstrap estimation or single-shot TMLE_TH, then combine results into tables and plots.",
        nodes=[
            node(
                "calibrated",
                80,
                100,
                "Calibrated predictions",
                "combined calibrated CSV",
                "INPUT",
                "artifact",
            ),
            node(
                "support",
                384,
                100,
                "Select analysis cohort",
                "optional common support",
                "FILTER",
            ),
            node(
                "outcome",
                688,
                100,
                "Prepare each outcome",
                "A · Y · ps · Q(1) · Q(0)",
                "LOOP",
            ),
            node(
                "dispatch",
                696,
                288,
                "Choose methods",
                "View dispatch source",
                "DISPATCH",
                "focal",
                width=192,
                height=112,
                destination="source-estimator",
                shape="diamond",
            ),
            node(
                "bootstrap",
                432,
                456,
                "IPW / AIPW / TMLE",
                "bootstrap when B > 1",
                "CAUSALESTIMATE",
                "external",
            ),
            node(
                "theoretical",
                944,
                456,
                "TMLE_TH",
                "single-shot analytic CI",
                "CAUSALESTIMATE",
                "external",
            ),
            node(
                "tables",
                688,
                616,
                "Effects & diagnostics",
                "tables · intervals · plots",
                "OUTPUT",
                "artifact",
                height=72,
            ),
        ],
        edges=[
            edge([(288, 144), (384, 144)], "READS", 336, 126),
            edge([(592, 144), (688, 144)], "PASSES", 640, 126),
            edge([(792, 188), (792, 288)], "PER OUTCOME", 858, 238),
            edge([(696, 344), (536, 344), (536, 456)], "BOOTSTRAP METHODS", 600, 326),
            edge([(888, 344), (1048, 344), (1048, 456)], "TMLE_TH", 976, 326),
            edge([(536, 544), (536, 580), (744, 580), (744, 616)], "RESULTS", 632, 562),
            edge(
                [(1048, 544), (1048, 580), (840, 580), (840, 616)], "RESULTS", 956, 562
            ),
        ],
        related=[
            ("fold", "Related: prediction generation", 80, 684),
            ("config", "Estimator configuration", 80, 632),
        ],
        refs=[
            (
                "Outcome loop and estimator dispatch",
                "corebehrt/modules/causal/estimate.py",
            ),
            (
                "Named columns become potential-outcome predictions",
                "corebehrt/functional/estimate/data_handler.py",
            ),
            (
                "Bootstrap versus single evaluation",
                CE_BASE + "CausalEstimate/core/multi_estimator.py",
            ),
            ("Pinned TMLE API", CE_BASE + "CausalEstimate/estimators/tmle.py"),
        ],
    ),
    dict(
        id="config",
        title="What controls a run and its versions?",
        short="Configuration & versions",
        subtitle="Stage YAML names the inputs and settings; requirements.txt pins direct package versions.",
        description="Local commands and Azure jobs both use stage YAML, whose paths reference artifacts. Package installation reads project metadata and requirements. Azure environment construction also reads requirements and adds unpinned extras.",
        lanes=[("RUN INPUTS", 80, 76), ("SOFTWARE ENVIRONMENT", 744, 76)],
        nodes=[
            node("local", 80, 128, "Local command", "--config_path", "ENTRY"),
            node(
                "job", 384, 128, "Azure component", "job config + input paths", "ENTRY"
            ),
            node(
                "yaml",
                232,
                344,
                "Stage YAML",
                "load_config → Config",
                "SHARED INPUT",
                "focal",
            ),
            node(
                "artifacts",
                232,
                544,
                "Data & checkpoints",
                "paths.* references",
                "ARTIFACT",
                "artifact",
            ),
            node(
                "install",
                744,
                128,
                "Package installation",
                "pip install .",
                "BUILD",
                width=200,
            ),
            node(
                "environment",
                1048,
                128,
                "Environment builder",
                "adds unpinned extras",
                "BUILD",
                width=192,
            ),
            node(
                "metadata",
                744,
                344,
                "Project metadata",
                "pyproject.toml",
                "METADATA",
                width=200,
            ),
            node(
                "pins",
                1048,
                344,
                "Direct dependency pins",
                "CausalEstimate==0.13.0",
                "REQUIREMENTS",
                "artifact",
                width=192,
            ),
        ],
        edges=[
            edge([(184, 216), (184, 272), (280, 272), (280, 344)], "READS", 232, 254),
            edge(
                [(488, 216), (488, 272), (392, 272), (392, 344)],
                "OVERRIDES",
                450,
                254,
            ),
            edge([(336, 432), (336, 544)], "REFERENCES", 400, 492),
            edge([(844, 216), (844, 344)], "READS", 882, 286),
            edge([(1144, 216), (1144, 344)], "READS", 1180, 286),
            edge([(944, 388), (1048, 388)], "LOADS", 996, 370),
        ],
        related=[],
        refs=[
            ("YAML loading and config objects", "corebehrt/modules/setup/config.py"),
            ("Azure job config and path overrides", "corebehrt/azure/util/job.py"),
            (
                "Example stage paths and settings",
                "corebehrt/configs/causal/finetune/simple.yaml",
            ),
            ("Direct version pins", "requirements.txt"),
            ("Dynamic package dependencies", "pyproject.toml"),
            (
                "Azure environment and unpinned additions",
                "corebehrt/azure/environment.py",
            ),
        ],
    ),
]


def rounded_path(points):
    """Route orthogonal connectors, rounding each bend by eight pixels."""
    result = [f"M {points[0][0]} {points[0][1]}"]
    for i in range(1, len(points) - 1):
        before, corner, after = points[i - 1 : i + 2]
        assert before[0] == corner[0] or before[1] == corner[1]
        dx1, dy1 = corner[0] - before[0], corner[1] - before[1]
        dx2, dy2 = after[0] - corner[0], after[1] - corner[1]
        length1, length2 = abs(dx1) + abs(dy1), abs(dx2) + abs(dy2)
        radius = min(8, length1 / 2, length2 / 2)
        a = (corner[0] - radius * dx1 / length1, corner[1] - radius * dy1 / length1)
        b = (corner[0] + radius * dx2 / length2, corner[1] + radius * dy2 / length2)
        result.append(f"L {a[0]} {a[1]} Q {corner[0]} {corner[1]} {b[0]} {b[1]}")
    result.append(f"L {points[-1][0]} {points[-1][1]}")
    return " ".join(result)


def svg_node(diagram_id, n):
    x, y, w, h = (n[k] for k in ("x", "y", "width", "height"))
    ident = f"{diagram_id}-{n['id']}"
    attrs = f'class="node {n["kind"]}" id="{ident}" data-node="{n["id"]}" data-label="{esc(n["name"])}"'
    if n["destination"]:
        start = f'<a class="node-link" href="{n["destination"]}.html" data-destination="{n["destination"]}" data-kind="{n["link_kind"]}" aria-label="Look inside: {esc(n["name"])}"><g {attrs}>'
    else:
        start = f"<g {attrs}>"
    if n["shape"] == "diamond":
        box = f'<path class="node-box" d="M {x + w / 2} {y} L {x + w} {y + h / 2} L {x + w / 2} {y + h} L {x} {y + h / 2} Z"/>'
        name_y, sub_y, tag_y = y + h / 2 - 2, y + h / 2 + 17, y + 24
    else:
        box = (
            f'<rect class="node-box" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
        )
        name_y, sub_y, tag_y = y + h / 2 + 3, y + h / 2 + 21, y + 19
    indicator = (
        f'<text class="disclosure" x="{x + w - 18}" y="{y + 20}" text-anchor="middle">+</text>'
        if n["destination"] and n["shape"] != "diamond"
        else ""
    )
    text = f'<text class="tag" x="{x + w / 2}" y="{tag_y}" text-anchor="middle">{esc(n["tag"])}</text><text class="node-name" x="{x + w / 2}" y="{name_y}" text-anchor="middle">{esc(n["name"])}</text><text class="node-sub" x="{x + w / 2}" y="{sub_y}" text-anchor="middle">{esc(n["sub"])}</text>'
    return (
        start + box + text + indicator + "</g>" + ("</a>" if n["destination"] else "")
    )


def svg_diagram(d):
    slug = d["id"]
    parts = [
        f'<svg class="diagram" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" role="img" aria-labelledby="{slug}-title {slug}-desc"><title id="{slug}-title">{esc(d["title"])}</title><desc id="{slug}-desc">{esc(d["description"])}</desc><defs>'
    ]
    for suffix, color in (
        ("arrow", "#4b586e"),
        ("arrow-accent", "#35b2bf"),
        ("arrow-link", "#2e5aa8"),
    ):
        parts.append(
            f'<marker id="{slug}-{suffix}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{color}"/></marker>'
        )
    parts.append(f'</defs><rect width="1280" height="720" fill="{PAPER}"/>')
    for label, x, y in d.get("lanes", []):
        parts.append(f'<text class="lane-label" x="{x}" y="{y}">{label}</text>')
        if slug == "fold":
            parts.append(
                f'<line x1="80" y1="{y + 12}" x2="1200" y2="{y + 12}" stroke="#dce2e8"/>'
            )
    for e in d["edges"]:
        dashed = ' stroke-dasharray="4 3"' if e["dashed"] else ""
        parts.append(
            f'<path class="connector" d="{rounded_path(e["points"])}" fill="none" stroke="#4b586e" stroke-width="1.2" marker-end="url(#{slug}-arrow)"{dashed}/>'
        )
    for e in d["edges"]:
        w = len(e["label"]) * 5.2 + 16
        parts.append(
            f'<g class="edge-caption"><rect x="{e["x"] - w / 2}" y="{e["y"] - 11}" width="{w}" height="16" fill="{PAPER}"/><text class="edge-label" x="{e["x"]}" y="{e["y"]}" text-anchor="middle">{esc(e["label"])}</text></g>'
        )
    parts.extend(svg_node(slug, n) for n in d["nodes"])
    for destination, label, x, y in d["related"]:
        parts.append(
            f'<a href="{destination}.html" data-destination="{destination}" data-kind="related" class="related-link" aria-label="Related view: {esc(label)}"><rect x="{x - 8}" y="{y - 28}" width="280" height="44" fill="transparent"/><text class="related" x="{x}" y="{y}">{esc(label)} ↗</text></a>'
        )
    parts.append("</svg>")
    return "".join(parts)


def evidence(d):
    items = []
    for label, path in d["refs"]:
        # The standalone skill prohibits remote hrefs, even evidence links.
        # A local evidence document keeps diagrams self-contained and script-free.
        items.append(
            f"<li>{esc(label)} — <code>{esc(path if not path.startswith('https:') else path.split('/blob/')[1])}</code></li>"
        )
    return (
        '<details class="evidence"><summary>View source references</summary><p>Code evidence: BONSAI Causal <code>'
        + REVISION
        + "</code>; CausalEstimate 0.13.0 <code>"
        + DEPENDENCY_REVISION
        + "</code>.</p><ul>"
        + "".join(items)
        + '</ul><a href="evidence.html">Open revision-pinned source links ↗</a></details>'
    )


def page(title, content, css, script="", extra=""):
    return f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · BONSAI Causal</title><style>\n{css}\n</style></head><body><div class="shell"><a class="brand" href="index.html">BONSAI <span>Causal / architecture</span></a>{extra}{content}</div>{script}</body></html>\n'


def source_section(slug, title, filename, symbol, start, end):
    source = subprocess.check_output(
        ["git", "show", f"{REVISION}:{filename}"], cwd=REPO, text=True
    )
    lines = source.splitlines()
    excerpt = "\n".join(lines[start - 1 : end])
    assert symbol in excerpt
    body = f'<h1 tabindex="-1">{esc(title)}</h1><p class="source-meta">{esc(filename)} · lines {start}–{end}<br>Revision {REVISION}</p><pre tabindex="0" aria-label="{esc(title)} source code"><code>{esc(excerpt)}</code></pre><p class="evidence"><a href="evidence.html">Open revision-pinned source links ↗</a></p>'
    return dict(
        id=slug,
        short=title,
        title=title,
        body=body,
        filename=filename,
        start=start,
        end=end,
        source=excerpt,
    )


def build():
    css = (ROOT / "diagrams.css").read_text()
    views = []
    routes = {}
    for d in DIAGRAMS:
        assert len(d["nodes"]) <= 9 and len(d["edges"]) <= 12
        body = f'<h1 tabindex="-1">{esc(d["title"])}</h1><p class="subtitle">{esc(d["subtitle"])}</p><div class="diagram-scroll" tabindex="0" role="region" aria-label="Scrollable diagram: {esc(d["short"])}">{svg_diagram(d)}</div>{evidence(d)}'
        views.append(dict(id=d["id"], short=d["short"], title=d["title"], body=body))
        for n in d["nodes"]:
            if n["destination"]:
                routes[f"{d['id']}:{n['id']}"] = dict(
                    to=n["destination"], kind="inside", label=n["name"], node=n["id"]
                )
        for destination, label, _, _ in d["related"]:
            routes[f"{d['id']}:{destination}"] = dict(
                to=destination, kind="related", label=label, node=None
            )
        nav = '<nav class="standalone-nav" aria-label="Document"><a href="index.html">Open interactive overview</a></nav>'
        (ROOT / f"{d['id']}.html").write_text(
            page(d["title"], nav + "<main>" + body + "</main>", css)
        )
    sources = [
        source_section(
            "source-fold",
            "finetune_fold()",
            "corebehrt/main_causal/helper/finetune_exp_y.py",
            "def finetune_fold",
            59,
            166,
        ),
        source_section(
            "source-estimator",
            "EffectEstimator._estimate_effects()",
            "corebehrt/modules/causal/estimate.py",
            "def _estimate_effects",
            189,
            260,
        ),
    ]
    for s, parent in zip(sources, ["fold", "estimation"]):
        views.append(s)
        nav = f'<nav class="standalone-nav" aria-label="Document"><a href="{parent}.html">Up</a><a href="index.html">Overview</a></nav>'
        (ROOT / f"{s['id']}.html").write_text(
            page(s["title"], nav + "<main>" + s["body"] + "</main>", css)
        )
    metadata = {v["id"]: dict(title=v["title"], short=v["short"]) for v in views}
    config = json.dumps(
        dict(brand="BONSAI Causal", views=metadata, routes=routes), ensure_ascii=False
    ).replace("<", "\\u003c")
    sections = "".join(
        f'<section id="view-{v["id"]}" data-view="{v["id"]}"{" hidden" if v["id"] != "overview" else ""}>{v["body"]}</section>'
        for v in views
    )
    chrome = '<div class="toolbar" hidden><nav class="breadcrumbs" aria-label="Location"></nav><div class="nav-actions"><button class="nav-button" id="up">← Up</button><button class="nav-button" id="overview">Overview</button></div></div><div class="context" hidden><div class="context-anchor"><small></small><strong></strong></div></div>'
    script = (
        "<script>\nconst PACKAGE = "
        + config
        + ";\n"
        + (ROOT / "viewer.js").read_text()
        + "\n</script>"
    )
    noscript = '<noscript><p>Open a component to follow its standalone diagram. <a href="overview.html">Standalone overview</a>.</p></noscript>'
    (ROOT / "index.html").write_text(
        page(
            "Logical architecture",
            "<main>"
            + sections
            + '</main><p class="sr-only" role="status" aria-live="polite" id="location-status"></p>'
            + noscript,
            css,
            script,
            chrome,
        )
    )
    claims = [
        dict(
            diagram=d["id"],
            claim=d["description"],
            sources=[
                dict(
                    label=label, url=path if path.startswith("https:") else BASE + path
                )
                for label, path in d["refs"]
            ],
        )
        for d in DIAGRAMS
    ]
    manifest = dict(
        repositories={
            "bonsai-causal": dict(ref="origin/main", sha=REVISION),
            "CausalEstimate": dict(
                ref="v0.13.0",
                sha=DEPENDENCY_REVISION,
                refreshed_main="b38e07e2013ee33c05505df98044a62d1f25974e",
            ),
        },
        claims=claims,
        snippets=[
            {k: v for k, v in s.items() if k not in ("body", "short", "title")}
            for s in sources
        ],
    )
    (ROOT / "evidence.json").write_text(json.dumps(manifest, indent=2) + "\n")
    links = "".join(
        "<h2>"
        + esc(d["short"])
        + "</h2><ul>"
        + "".join(
            f'<li><a href="{esc(path if path.startswith("https:") else BASE + path)}">{esc(label)}</a></li>'
            for label, path in d["refs"]
        )
        + "</ul>"
        for d in DIAGRAMS
    )
    (ROOT / "evidence.html").write_text(
        page(
            "Source evidence",
            '<main><h1>Source evidence</h1><p>Code inspection at fixed revisions; this document does not claim a runtime or statistical validation.</p><p class="source-meta">BONSAI Causal '
            + REVISION
            + "<br>CausalEstimate 0.13.0 "
            + DEPENDENCY_REVISION
            + "</p>"
            + links
            + "</main>",
            css,
        )
    )
    print(f"Built {len(DIAGRAMS)} diagrams, {len(sources)} source pages and index.html")


if __name__ == "__main__":
    build()
