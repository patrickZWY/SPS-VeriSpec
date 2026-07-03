# SPS-VeriSpec Agent Workbench

The local demo agent serves a browser workbench over checked-in replay artifacts
and can run allowlisted local targets for scheduled walkthroughs.

```bash
python3 -m pip install -r requirements-demo.txt
python3 -m sps_agent.server --host 127.0.0.1 --port 8765
```

Equivalent wrapper:

```bash
bash scripts/run_demo_agent.sh --port 8765
```

The public default is deterministic replay. `POST /api/run` accepts only local
requests and only allowlisted case ids; v1 does not accept arbitrary uploads or
user-provided project paths.

## Local LLM Semantic Assist

The agent can use a local model, such as a Qwen model served by Ollama or an
OpenAI-compatible local server, to propose semantic information for hard
test-generation cases. This stays in the quarantined candidate lane: the model
does not edit the trusted static rules and does not promote tests by itself.

Typical flow:

```bash
python3 tools/evaluate_pipeline.py \
  --target-project /path/to/project \
  --project-name sample \
  --work-dir /tmp/sps-sample \
  --with-plateau \
  --with-local-llm-semantic-assist \
  --local-llm-model qwen2.5-coder:7b
```

Manual flow:

```bash
python3 tools/llm_candidate_generation.py \
  --analysis-dir /tmp/sps-sample/analysis \
  --generated-tests /tmp/sps-sample/generated_tests/sample

python3 tools/local_llm_semantic_assist.py \
  --input /tmp/sps-sample/generated_tests/sample/llm_plateau_input.json \
  --output /tmp/sps-sample/generated_tests/sample/local_llm_semantic_proposals.json \
  --model qwen2.5-coder:7b

python3 tools/llm_candidate_generation.py \
  --analysis-dir /tmp/sps-sample/analysis \
  --generated-tests /tmp/sps-sample/generated_tests/sample \
  --llm-proposals /tmp/sps-sample/generated_tests/sample/local_llm_semantic_proposals.json
```

The proposal file uses the existing `--llm-proposals` shape and is rendered into
quarantined candidate tests plus a manifest. Run validation before any manual
promotion.

## API

- `GET /api/health`: service status, mode, and live-enabled cases.
- `GET /api/cases`: replay case manifests and compact metrics.
- `GET /api/cases/{case_id}`: normalized graph, metrics, artifacts, and safe excerpts.
- `GET /api/cases/{case_id}/artifacts/{artifact_id}`: checked-in replay artifact text.
- `POST /api/run`: allowlisted local live run through `tools/evaluate_pipeline.py`.
- `tools/local_llm_semantic_assist.py`: optional local-model proposal generator
  for quarantined semantic test candidates.

## Deployment Shape

This matches the TLA-Finance live-demo pattern:

- local FastAPI service binds to loopback;
- a Cloudflare tunnel points at the local service during scheduled walkthroughs;
- the public frontdoor can proxy `sps-demo.zhengwangyuan-patrick.com` to
  `live-sps-demo.zhengwangyuan-patrick.com`;
- when the tunnel is down, the frontdoor should return an offline page that
  says live SPS-VeriSpec analysis requires a scheduled local run.

Replay remains the default public experience. Live execution is deliberately
reserved for scheduled walkthroughs because dependency setup and target size vary
by case.
