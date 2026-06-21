# Evaluation Set Schema

This project now treats the evaluation set primarily as a retrieval-grounding benchmark, not a keyword-matching benchmark.

## Core fields

- `id`: stable case id
- `question`: user query sent to `/chat`
- `category`: one of `employee_handbook`, `compliance_guide`, `technical_spec`, `architecture_doc`
- `evaluation_group`: language or scenario slice such as `pure_english_en`, `pure_chinese_zh`, `bilingual_zh`
- `language`: `en` or `zh`
- `expected_behavior`: `answer` or `reject`
- `expect_rejection`: whether the system should refuse
- `retrieval_label_type`:
  - `single_source`: the answer should be supportable from one document
  - `multi_source_all_required`: the answer requires two documents at most
- `golden_source_files`: canonical evidence files used for retrieval evaluation

## Labeling constraints

- `single_source` cases must contain exactly one golden document when evidence exists.
- `multi_source_all_required` cases must contain at most two golden documents.
- Rejection cases keep `golden_source_files` empty.

## About `expected_terms` and `answer_points`

These fields may still exist in `eval/eval_set.json` as annotation notes, but they are no longer part of the primary online evaluation logic.

The main `eval/evaluate.py` script now scores:

- retrieval hit: whether the retrieved contexts contain the golden file(s)
- citation hit: whether the final cited contexts contain the golden file(s)
- overall accuracy: currently aligned with retrieval hit for answerable cases and correct refusal for rejection cases

This keeps the evaluation closer to the assignment constraints and avoids overfitting to handcrafted keyword lists.
