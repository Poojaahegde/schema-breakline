# Schema Breakline

**A small data contract gate for product teams that depend on trustworthy reporting.**

[View the sample decision report](https://poojaahegde.github.io/schema-breakline/) · [Read the product brief](PRD.md)

## The problem

An upstream event producer can change a field such as `user_id` from an integer to a string. A downstream ingestion job may then fail, drop records, or pass inconsistent data into a reporting model. The resulting investigation pulls engineers away from planned work and leaves PMs unsure whether a metric is reliable.

Schema Breakline checks a JSONL event batch against a versioned JSON contract **before ingestion**. It exits with a failing status when it finds a violation, writes machine readable `report.json`, and generates an HTML report with the exact line, field, rule, expected value, and received value. A GitHub Action runs the gate on every pull request and uploads the report as a workflow artifact.

The [live report](https://poojaahegde.github.io/schema-breakline/) intentionally uses a **synthetic breaking batch** so the decision state is visible without running code. The CI gate checks the passing `incoming/latest.jsonl` sample.

## Try it

Python 3.9+ is the only requirement.

```bash
python3 contract_guard.py --contract contract.json --input incoming/latest.jsonl --output reports
# PASS: exit code 0

python3 contract_guard.py --contract contract.json --input examples/breaking.jsonl --output reports
# BLOCKED: exit code 1; open reports/index.html
```

The breaking example identifies:

| Line | Field | Expected | Received |
| --- | --- | --- | --- |
| 2 | `user_id` | integer | string |
| 3 | `sync_status` | `success` or `error` | `pending` |
| 4 | `invoice_id` | present | missing |

Malformed JSON, unexpected fields, and an empty batch also block the gate. Runtime failures, such as a missing file, return exit code 2. The validator implements only the contract keywords this prototype uses: `type`, `required`, `properties`, `additionalProperties`, `enum`, and `const`. It does **not** claim full JSON Schema compliance or validate timestamp formats.

## PM decision behind the gate

**Data governance:** The contract makes the producer and consumer agree on required fields and accepted values. A breaking change should trigger an owner decision: restore the old shape, add a compatible field, or publish a versioned contract and migrate consumers.

**Operational churn:** I would track engineer hours spent diagnosing schema incidents per month, time to detect a breaking change, and the number of reporting discrepancies reaching stakeholders. A **40% reduction in schema-related investigation time** is a proposed success target for a pilot, **not an observed result**. It would need a measured baseline and comparable post-launch period.

**Release decision:** A blocked report is a clear stop signal for ingestion. The report makes the mismatch reviewable by both engineering and product owners before a dashboard or executive readout uses the affected events.

## Project structure

```text
contract.json                 Versioned event contract
contract_guard.py             Validator and HTML/JSON report generator
incoming/latest.jsonl         Passing synthetic input checked in CI
examples/breaking.jsonl      Synthetic breaking input used for the live demo
docs/index.html               Published sample report
docs/report.json              Machine readable sample report
PRD.md                        Product requirements and measurement plan
.github/workflows/contract-gate.yml  Pull request check
```

## Scope and provenance

This is an independent portfolio prototype using synthetic records. It is not a deployed integration with Matillion, Azure Data Factory, Power BI, Method CRM, or Wipro, and it does not report measured business impact.
