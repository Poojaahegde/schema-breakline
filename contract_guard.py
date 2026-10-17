"""Validate JSONL events against the contract and generate a decision dashboard.

This dependency-free prototype supports the JSON Schema keywords used in contract.json:
type, required, properties, additionalProperties, enum, and const. It is not a
complete JSON Schema implementation.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def matches_type(value: object, expected: str) -> bool:
    actual = type_name(value)
    return actual == expected or (expected == "number" and actual == "integer")


def issue(line: int, path: str, rule: str, expected: str, actual: str) -> dict:
    return {
        "line": line,
        "path": path,
        "rule": rule,
        "expected": expected,
        "actual": actual,
        "message": f"{path}: expected {expected}; received {actual}",
    }


def validate_event(event: object, schema: dict, line: int) -> list[dict]:
    findings: list[dict] = []
    if not isinstance(event, dict):
        return [issue(line, "$", "type", "object", type_name(event))]

    for name in schema.get("required", []):
        if name not in event:
            findings.append(issue(line, name, "required", "present", "missing"))

    properties = schema.get("properties", {})
    for name, value in event.items():
        if name not in properties:
            if schema.get("additionalProperties") is False:
                findings.append(issue(line, name, "additionalProperties", "not present", "unexpected field"))
            continue
        rules = properties[name]
        expected_type = rules.get("type")
        if expected_type and not matches_type(value, expected_type):
            findings.append(issue(line, name, "type", expected_type, type_name(value)))
            continue
        if "const" in rules and value != rules["const"]:
            findings.append(issue(line, name, "const", repr(rules["const"]), repr(value)))
        if "enum" in rules and value not in rules["enum"]:
            findings.append(issue(line, name, "enum", ", ".join(map(str, rules["enum"])), repr(value)))
    return findings


def check_stream(contract_path: Path, input_path: Path) -> dict:
    schema = json.loads(contract_path.read_text(encoding="utf-8"))
    if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
        raise ValueError("Contract must define an object with properties")

    findings: list[dict] = []
    checked = 0
    for line_number, raw in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        checked += 1
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(issue(line_number, "$", "json", "valid JSON", f"parse error at column {exc.colno}"))
            continue
        findings.extend(validate_event(event, schema, line_number))

    if checked == 0:
        findings.append(issue(0, "$", "empty", "at least one record", "empty batch"))

    return {
        "status": "BLOCKED" if findings else "PASS",
        "contract": contract_path.name,
        "source": input_path.as_posix(),
        "checked_records": checked,
        "issue_count": len(findings),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "issues": findings,
    }


def dashboard(report: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    blocked = report["status"] == "BLOCKED"
    rows = "".join(
        "<tr>"
        f"<td>{esc(item['line'])}</td><td><code>{esc(item['path'])}</code></td>"
        f"<td>{esc(item['rule'])}</td><td>{esc(item['expected'])}</td>"
        f"<td>{esc(item['actual'])}</td>"
        "</tr>"
        for item in report["issues"]
    ) or '<tr><td colspan="5" class="empty">No contract violations found.</td></tr>'
    guidance = (
        "Pause ingestion. Ask the upstream owner to restore the contract or approve a versioned change; then rerun the gate."
        if blocked else "The checked batch matches this contract and can proceed to the next ingestion step."
    )
    color = "#cf5b3d" if blocked else "#15936d"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Schema Breakline · Contract report</title>
<style>
:root{{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#17293d;background:#f5f3ee}}*{{box-sizing:border-box}}body{{margin:0}}.wrap{{width:min(1050px,calc(100% - 36px));margin:auto}}header{{background:#142a3e;color:white;padding:19px 0}}header b{{letter-spacing:.13em}}header span{{float:right;color:#9fb5bf;font-size:13px}}main{{padding:66px 0}}.eyebrow{{color:#9b543a;font-size:11px;font-weight:800;letter-spacing:.18em}}h1{{font-family:Georgia,serif;font-size:clamp(42px,7vw,70px);font-weight:500;letter-spacing:-.05em;line-height:1.05;margin:14px 0}}.intro{{color:#63717d;line-height:1.6;max-width:680px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:36px 0}}.card{{background:white;border:1px solid #dfe5e4;padding:23px;border-radius:9px}}.card small{{display:block;color:#6c7a82;font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:.1em}}.card strong{{display:block;font-size:27px;margin-top:10px}}.status{{color:{color}}}.panel{{background:white;border:1px solid #dfe5e4;border-radius:9px;padding:27px;margin:24px 0}}.panel h2{{font-family:Georgia,serif;font-size:28px;font-weight:500;margin:0 0 12px}}.panel p{{line-height:1.6;color:#566975}}.table-scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:580px;font-size:14px}}th{{text-align:left;background:#edf1f0;color:#455a63;font-size:11px;letter-spacing:.08em;text-transform:uppercase}}th,td{{border-bottom:1px solid #e0e8e5;padding:13px 11px}}code{{background:#f1f4f2;border-radius:3px;padding:3px 5px}}.empty{{text-align:center;color:#6c7a82}}.note{{color:#73818a;font-size:12px;line-height:1.5}}a{{color:#aa4f35}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}header span{{float:none;display:block;margin-top:6px}}}}
</style></head><body><header><div class="wrap"><b>SCHEMA BREAKLINE</b><span>Data contract gate · portfolio simulation</span></div></header>
<main class="wrap"><p class="eyebrow">PRE-INGESTION REPORT</p><h1>Catch the break<br>before the dashboard does.</h1>
<p class="intro">This report compares a synthetic incoming event batch with a versioned data contract. It surfaces the exact field, record, and rule that need attention.</p>
<div class="grid"><div class="card"><small>Gate result</small><strong class="status">{esc(report['status'])}</strong></div><div class="card"><small>Records checked</small><strong>{esc(report['checked_records'])}</strong></div><div class="card"><small>Contract violations</small><strong>{esc(report['issue_count'])}</strong></div></div>
<section class="panel"><h2>What changed</h2><div class="table-scroll"><table><thead><tr><th>Line</th><th>Field</th><th>Rule</th><th>Expected</th><th>Received</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="panel"><h2>Next decision</h2><p>{esc(guidance)}</p><p><b>Source:</b> {esc(report['source'])}<br><b>Contract:</b> {esc(report['contract'])}<br><b>Generated:</b> {esc(report['generated_at'])}</p></section>
<p class="note">Independent portfolio simulation with synthetic records. This report shows contract violations; it does not represent a production ETL incident or measured downtime reduction.</p>
<p><a href="https://github.com/Poojaahegde/schema-breakline">Repository and product brief ↗</a></p></main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("contract.json"))
    parser.add_argument("--input", type=Path, default=Path("incoming/latest.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)
    try:
        report = check_stream(args.contract, args.input)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (args.output / "index.html").write_text(dashboard(report), encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Gate could not run: {exc}", file=sys.stderr)
        return 2
    print(f"{report['status']}: {report['checked_records']} records, {report['issue_count']} violations")
    for item in report["issues"]:
        print(f"line {item['line']}: {item['message']}")
    print(f"Dashboard: {args.output / 'index.html'}")
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
