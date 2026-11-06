"""py -m evaluation.run_evaluation [--dataset path] [--output-dir path]

No AI/API calls. Reports actual mismatches; does not rewrite expected labels.
Exit 0 means evaluation ran, NOT that all labelled cases passed.
"""

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

from app.services.ai_review import run_review
from app.services.contracts import ReviewContext
from .fixtures import knowledge


def _signature(issue):
    return (issue["category"],issue["verdict"],issue["quote"])


def compare(expected,actual):
    """Multiset comparison: duplicate warnings count as extra findings."""
    wanted=Counter(_signature(i) for i in expected)
    observed=Counter(_signature(i) for i in actual)
    tp=sum((wanted&observed).values())
    def unpack(counter):
        return [dict(category=k[0],verdict=k[1],quote=k[2],count=n) for k,n in sorted(counter.items())]
    return dict(tp=tp,fp=sum((observed-wanted).values()),fn=sum((wanted-observed).values()),
                missed=unpack(wanted-observed),unexpected=unpack(observed-wanted))


def validate_dataset(dataset):
    if not isinstance(dataset,dict) or dataset.get("schema_version")!=1 or not isinstance(dataset.get("cases"),list):
        raise ValueError("Expected schema_version=1 and a cases array.")
    ids=set()
    for case in dataset["cases"]:
        if not isinstance(case,dict) or not isinstance(case.get("id"),str) or not case["id"] or case["id"] in ids:
            raise ValueError("Case IDs must be nonempty and unique.")
        ids.add(case["id"])
        if case.get("group") not in ("baseline","challenge") or not isinstance(case.get("draft"),str):
            raise ValueError("Each case needs group baseline/challenge and a draft string.")
        if not isinstance(case.get("expected"),list):raise ValueError("Expected labels must be an array.")
        for label in case["expected"]:
            if not isinstance(label,dict) or set(label)!={"category","verdict","quote"} or any(not isinstance(v,str) for v in label.values()):
                raise ValueError("Labels need category/verdict/quote strings.")
            if label["quote"] and label["quote"] not in case["draft"]:
                raise ValueError("A labelled quote is absent from its case draft.")
            if not label["quote"] and label["category"]!="disclaimer":
                raise ValueError("Only missing-disclaimer labels use an empty quote.")


def _metrics(rows):
    tp=sum(r["tp"] for r in rows);fp=sum(r["fp"] for r in rows);fn=sum(r["fn"] for r in rows)
    return dict(cases=len(rows),exact_cases=sum(r["fp"]==0 and r["fn"]==0 for r in rows),tp=tp,fp=fp,fn=fn,
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None)


def evaluate(dataset):
    validate_dataset(dataset)
    rows=[]
    for case in dataset["cases"]:
        products,facts,rules,evidence=knowledge(case.get("knowledge_profile","standard"))
        overrides=case.get("context",{})
        context=ReviewContext(overrides.get("product","Veyra Beat 200"),overrides.get("market","IN"),
            date.fromisoformat(overrides.get("publication_date","2026-11-05")),
            channel=overrides.get("channel","instagram"),audience=overrides.get("audience","consumer"),
            content_type=overrides.get("content_type","social_post"),campaign=overrides.get("campaign"))
        result=run_review(case["draft"],context=context,products=products,rules=rules,numeric_facts=facts,
            claim_evidence=evidence,org_id="demo-org",brand_id="veyra",generator=None)
        actual=[dict(category=f.category,verdict=f.verdict,quote=f.quoted_text) for f in result.findings if f.verdict!="supported"]
        scored=compare(case["expected"],actual)
        span_errors=sum(case["draft"][f.span_start:f.span_end]!=f.quoted_text for f in result.findings)
        missing_sources=sum(f.source is None or not(f.fact_id or f.rule_code) for f in result.findings
                            if f.verdict!="needs_review")
        rows.append(dict(id=case["id"],group=case["group"],draft=case["draft"],rationale=case.get("rationale",""),
            expected=case["expected"],actual=actual,**scored,invalid_spans=span_errors,missing_evidence=missing_sources,
            ai_used=result.ai_used))
    return dict(dataset_name=dataset.get("name"),method="deterministic_only",live_ai_tested=False,
        label_status="Assistant-authored synthetic labels; independent human review still required.",
        scoring="Exact category + verdict + quoted text multiset; supported/info findings excluded from issue scoring.",
        summary=_metrics(rows),groups={g:_metrics([r for r in rows if r["group"]==g]) for g in ("baseline","challenge")},
        invalid_span_count=sum(r["invalid_spans"] for r in rows),missing_evidence_count=sum(r["missing_evidence"] for r in rows),
        cases=rows)


def render_report(report):
    lines=["# MindVault Role B evaluation report","",report["label_status"],"",
        "This evaluates the deterministic-only service on a small synthetic development dataset. It is not live Gemini evaluation, independent validation or a general accuracy claim.","",
        report["scoring"],"","| Group | Cases | Exact cases | Matched issues | Extra warnings | Missed labels | Precision | Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for group,metrics in [("All",report["summary"]),*report["groups"].items()]:
        fmt=lambda v:"n/a" if v is None else f"{v:.1%}"
        lines.append(f"| {group} | {metrics['cases']} | {metrics['exact_cases']} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} | {fmt(metrics['precision'])} | {fmt(metrics['recall'])} |")
    lines.extend(["",f"Invalid returned spans: {report['invalid_span_count']}. Missing evidence on conclusive findings: {report['missing_evidence_count']}.","",
        "Precision counts matched issue labels divided by all emitted issue warnings. Recall counts matched labels divided by expected issue labels. A wrong verdict or quote can count as both an extra warning and a missed label. needs_review is a warning class, not a confirmed violation. Blank disclaimers represent end insertions.","",
        "Supported facts are excluded from issue scoring. The evidence check verifies presence, not semantic correctness or that a cited claim is actually substantiated. Case/issue coverage is limited; review every mismatch before changing the engine or labels.","","## Case mismatches",""])
    for row in report["cases"]:
        if row["fp"] or row["fn"]:
            lines.extend([f"### {row['id']} ({row['group']})","",row["draft"],"",row["rationale"],"",
                "Missed: `"+json.dumps(row["missed"],ensure_ascii=False)+"`","",
                "Unexpected: `"+json.dumps(row["unexpected"],ensure_ascii=False)+"`",""])
    lines.extend(["## Next actions","","Have a teammate review the labels against the fictional policies. Prioritise negation, ordinary uses of superlative keywords, unit phrasing and product-attribution errors. Keep challenge labels visible. Add real user examples only with permission and appropriate privacy handling. Evaluate live AI separately and identify its model/version and usage status.",""])
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description="Run labelled evaluation without Gemini or a database.")
    parser.add_argument("--dataset",type=Path,default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--output-dir",type=Path,default=Path(__file__).with_name("results"))
    args=parser.parse_args()
    report=evaluate(json.loads(args.dataset.read_text(encoding="utf-8")))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"evaluation_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.output_dir/"evaluation_report.md").write_text(render_report(report),encoding="utf-8")
    print("DETERMINISTIC EVALUATION (synthetic labels, not independent accuracy validation)")
    for group,metrics in report["groups"].items():
        print(f"{group}: {metrics['exact_cases']}/{metrics['cases']} exact cases; {metrics['fp']} extra warnings; {metrics['fn']} missed labels")
    print("Live AI tested: false")
    print("Reports saved to:",args.output_dir.resolve())
    print("Exit 0 means evaluation completed; inspect reported mismatches.")


if __name__=="__main__":main()
