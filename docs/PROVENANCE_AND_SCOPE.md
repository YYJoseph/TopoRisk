# Provenance and scope

## Controlled results

Files under `results/controlled/` are outputs of the deterministic simulation
programs under `src/`. They contain no third-party benchmark records or remote
model conversations.

## Fixed-trace summary

`results/fixed_trace_summary/summary.json` contains aggregate statistics from a
constructed two-hazard, one-check allocation stress test over frozen real
conversational contexts. The underlying conversations are excluded. The table
must not be interpreted as a natural error-rate or deployment-safety estimate.

## Online summary

Files under `results/online_summary/` contain paired success indicators,
aggregate token counts, and estimated costs. They exclude prompts, responses,
provider request identifiers, API credentials, and private account data. The
`task_id` values are local study labels.

The GLM Airline extension replaces the DeepSeek agent with GLM-5.3-Flash while
retaining the DeepSeek user simulator and Qwen verifier. Two provider-level
empty-response runs were replaced by exact task--trial reruns. The public
summary records that replacement and omits a total GLM cost because inference
used a promotional token grant and the runtime lacked a reliable price map.

## Figures

The PNG files under `figures/` were generated from the packaged aggregate
results. Vector figures used in the unpublished manuscript are not included in
this preview release.

## External resources

The online and fixed-trace studies used public agent-evaluation contexts and
paid remote model APIs. This repository does not redistribute upstream
benchmark records. Users should obtain upstream resources from their original
maintainers and comply with their licenses and terms.
