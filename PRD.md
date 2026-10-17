# Product brief: Schema Breakline

## Opportunity

Product teams use event and operational data to decide what to build. When a producer changes a field without coordinating with downstream consumers, ingestion can fail and reported metrics may become unreliable. The failure is often discovered only after someone notices a broken pipeline or a surprising dashboard number.

## Users and job to be done

- **Data engineer:** Know which event and field broke before a batch enters the pipeline.
- **Producer engineer:** Get a specific, actionable reason for a rejected change.
- **Product manager / analyst:** Know whether data used for a decision passed the agreed contract.

## Proposed workflow

1. A producer and consumer agree on a versioned JSON contract for a specific event stream.
2. The incoming JSONL batch is checked before ingestion.
3. A passing batch proceeds to the next pipeline step. A breaking batch fails the check.
4. The report shows the exact record, field, expected rule, and received value.
5. The producer restores compatibility or proposes a new contract version with a consumer migration plan.

## MVP requirements

| Requirement | Acceptance criterion |
| --- | --- |
| Detect breaking fields | Type, required, enum, constant, and unexpected-field violations return exit code 1. |
| Give usable diagnostics | Every violation includes line, field path, rule, expected value, and actual value in JSON and HTML. |
| Block invalid input | Malformed JSON and empty batches fail the gate. Missing files or invalid contracts return exit code 2. |
| Fit a developer workflow | CI runs the gate on pull requests and retains the report as an artifact, including failures. |
| Demonstrate the decision | A public synthetic sample report shows a blocked batch and the next action. |

## Metrics and experiment

The North Star for a pilot is **schema incident investigation hours per month**. Baseline the prior 4–8 weeks of incidents, then compare with a similar period after adoption, normalized by event volume and number of producers. Target a **40% reduction**, subject to measurement. This project does not claim that reduction occurred.

Supporting measures: median detection time; count of breaking changes caught before ingestion; discrepancies reported by business users; false blocks per 100 checks; and time required to approve a legitimate contract change. A high false-block rate would undermine trust even if detection improves.

## Governance decisions

- Each contract needs a named producer owner and consumer owner before use in production.
- Additive fields can be accepted only when consumers have agreed to permit them; this prototype sets `additionalProperties` to `false` for a deliberately strict pilot.
- Renaming, deleting, or changing the type of a required field requires a new version and consumer migration.
- A blocked run should preserve the input reference and report for review; it should not silently coerce a value.

## Boundaries and next iteration

This prototype validates only a subset of JSON Schema and checks local JSONL files. It does not connect to a production stream, warehouse, ETL platform, or dashboard API. A production version would add complete schema validation, contract registry/version negotiation, ownership and approval records, access controls, and monitoring for the health of the gate itself.

## Evidence status

All records and failure examples are synthetic. The report demonstrates a working gate, not a measured reduction in downtime or a real incident.
