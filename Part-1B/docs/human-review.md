# US5 Human Review Record

Automated evaluation is evidence, not acceptance. A reviewer must inspect the
feature specification, the versioned case corpus, aggregate metrics, every
case and run result, failures, and limitations before recording a decision.

## Review procedure

1. Confirm the case-set version and digest match the evaluation report.
2. Confirm all nine FR-014 categories and all four FR-018 semantic dimensions
   are represented.
3. Inspect aggregate metrics, independent hard gates, per-case results, and
   failed properties.
4. Review repair results against the same unchanged case-set digest.
5. Record limitations and an explicit `approved` or `rejected` decision.

## Review record template

```yaml
reviewer: ""
review_date: "YYYY-MM-DD"
run_id: ""
case_set_version: ""
decision: null # approved or rejected
findings: []
limitations: []
evidence_references:
  specification: []
  aggregate_metrics: []
  per_case_results: []
  failures: []
  limitations: []
```

An `approved` decision is valid only after the reviewer has completed the
evidence review. Passing automated thresholds alone must not create or imply
human acceptance.
