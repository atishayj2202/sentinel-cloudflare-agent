# 🛡️ Sentinel: Self-Verifying Autonomous Agent on Cloudflare

> **Target Role:** Software Engineer — Platforms & Productivity ([Cloudflare Greenhouse Job ID 8168623](https://job-boards.greenhouse.io/cloudflare/jobs/8168623?gh_jid=8168623))  
> **Core Thesis:** *"Don't trust the agent. Verify it."*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Cloudflare Agents](https://img.shields.io/badge/Cloudflare-Agents%20SDK-F38020?logo=cloudflare&logoColor=white)](https://agents.cloudflare.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-10%2F10%20Passing-success)](tests/)
[![Benchmarks](https://img.shields.io/badge/Reliability%20Benchmark-100%25%20Success-brightgreen)](tests/benchmark_report.json)

---

## 🌟 Executive Summary

Autonomous coding agents and AI productivity workflows fail in production not because models lack intelligence, but because **they lack verification systems**. Unchecked agents hallucinate architectural assumptions, run unchecked mutations on git repositories, fail silently during transient 503 API errors, and mask critical technical tradeoffs under synthetic sycophancy.

**Sentinel** is an institutional-grade, self-verifying autonomous agent system engineered natively for Cloudflare's serverless edge primitives. Sentinel enforces **Rule 1: No unsupported important claim**, runs **parallel multi-agent research**, automatically detects and resolves **agent-to-agent premise disagreements**, enforces **Cloudflare Engineering Codex policy-as-code guardrails**, and performs **closed-loop postcondition verification** on every side effect.

---

## 📋 Required API Keys & Environment Configuration

Sentinel is engineered to run zero-dependency out-of-the-box (with high-fidelity grounded synthetic tools and fallback LLM mock drivers for offline CI/CD) while seamlessly integrating with production AI providers.

| Environment Variable | Provider | Status / Necessity | Purpose | Where to Obtain |
|---|---|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio | **Recommended** (Pre-configured from Magicpin setup) | Primary reasoning, multi-agent dialogue, adversarial debate | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare | **Required for Edge Deploy** | Deployment of Workers, Durable Objects, and Workers AI | [Cloudflare Dashboard -> API Tokens](https://dash.cloudflare.com/profile/api-tokens) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare | **Required for Edge Deploy** | Cloudflare account scope for Workers AI bindings | Cloudflare Dashboard URL / Overview tab |
| `GITHUB_TOKEN` | GitHub | **Optional** (Mock tool provided) | Real GitHub issue creation, PR generation, and ADR sync | [GitHub Settings -> Personal Access Tokens](https://github.com/settings/tokens) |
| `OPENAI_API_KEY` | OpenAI | Optional | Cross-model consensus verification | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| `GROQ_API_KEY` | Groq | Optional | Ultra-low latency Llama 3.3 70B inference | [Groq Console](https://console.groq.com/keys) |

### Quick Setup:
```bash
cp .env.example .env
# Edit .env with your keys or use the default pre-configured environment
```

---

## 🏗️ Architecture & Multi-Agent Topology

```
                         ┌────────────────────────┐
                         │   User / GitHub Issue  │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │      Planner Agent     │
                         │ (Decomposition into 3  │
                         │ independent subtasks)  │
                         └───────────┬────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Researcher A    │       │   Researcher B   │       │   Researcher C   │
│ Architecture &   │       │ Storage Limits & │       │ Workload Latency │
│ Concurrency Fit  │       │ Cost Projections │       │ & Edge Bounds    │
└────────┬─────────┘       └─────────┬────────┘       └─────────┬────────┘
         │                           │                          │
         └───────────────────────────┼──────────────────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │     Verifier Agent     │
                         │ (Cross-examination &   │
                         │ Disagreement Detection)│
                         └───────────┬────────────┘
                                     │
                   [Conflict Detected / Mismatch?]
                   ├── YES ──► ┌────────────────────────┐
                   │           │ Targeted Resolution    │
                   │           │ (Grounding Deep-Dive)  │
                   │           └───────────┬────────────┘
                   └── NO  ────────────────┤
                                           ▼
                               ┌────────────────────────┐
                               │   Analyst Agent &      │
                               │  Codex Policy Gating   │
                               └───────────┬────────────┘
                                           │
                     [Action Requires Side Effect Mutation?]
                     ├── YES ──► ┌────────────────────────┐
                     │           │ Human Approval Modal   │
                     │           │ (Pause via Workflows)  │
                     │           └───────────┬────────────┘
                     └── NO  ────────────────┤
                                             ▼
                               ┌────────────────────────┐
                               │  Closed-Loop Execution │
                               │ & Postcondition Check  │
                               └────────────────────────┘
```

---

## ⚡ Cloudflare Native Primitives Mapping

Sentinel directly leverages Cloudflare's platform suite:

1. **Cloudflare Agents SDK (`agents.cloudflare.com`)**:
   - Implements stateful agent personas with typed state transitions, multi-agent event dispatching, and WebSocket streaming.
2. **Cloudflare Workers AI**:
   - Serverless LLM inference at the edge using `@cf/meta/llama-3.3-70b-instruct` and `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`.
3. **Cloudflare Durable Objects**:
   - Single-point-of-coordination per mission providing strictly ordered message journals, distributed locks, and state synchronization.
4. **Cloudflare Workflows**:
   - Long-running, durable workflow steps that survive worker evictions, automatic exponential backoff retries for transient 503 errors, and multi-day human-in-the-loop pauses.
5. **Cloudflare D1 & Workers KV**:
   - D1 for relational claim-evidence graphs and benchmark metric aggregation; KV for immutable prompt snapshotting and caching.

---

## 🔬 Deterministic Reliability Engine

### 1. The 4-Factor Confidence Formula
Sentinel rejects black-box agent confidence scores. Instead, confidence is computed through a strictly deterministic formula:

$$\text{Confidence} = 0.35 \cdot E + 0.30 \cdot A + 0.20 \cdot V + 0.15 \cdot X$$

Where:
- **$E$ (Evidence Quality)**: Percentage of important claims backed by primary citations ($\ge 2$ sources for high-impact claims).
- **$A$ (Agent Agreement)**: $1.0 - (\text{Disagreements} / \text{Total Evaluated Pairs})$.
- **$V$ (Verification Success)**: Ratio of cross-examined claims passing adversarial validation.
- **$X$ (Execution Reliability)**: Successful closed-loop tool executions without unrecovered faults.

### 2. Disagreement Detection & Targeted Resolution
When Researcher A (advocating Cloudflare D1 for relational queries) and Researcher B (advocating Durable Objects for per-user concurrency) submit opposing claims, the **Verifier Agent** detects the premise divergence. Rather than guessing, Sentinel triggers a dynamic **Targeted Verification Agent** that conducts a pinpoint documentation search, establishes boundary conditions, and harmonizes the architecture before proposing actions.

### 3. Cloudflare Engineering Codex Policy Engine
Every tool call is inspected against policy-as-code guardrails:
- **Low Risk (Auto-Allowed)**: Idempotent reads (`github.get_file`, `web.search`, `docs.read`).
- **Medium Risk (Approval Required)**: Public repository modifications (`github.create_issue`, `github.create_pr`).
- **High / Critical Risk (Strict Gate)**: File writes, production deployments (`github.update_file`, `deployment.production`).

### 4. Closed-Loop Postcondition Verification
Executing a side effect is never assumed successful simply because an API returned HTTP 200. Sentinel executes an automated follow-up inspection (e.g., verifying that the newly created issue actually exists with the expected payload) before marking a mission as completed.

---

## 📊 Institutional Benchmark Suite (10 Scenarios)

Sentinel includes an automated adversarial test harness (`tests/benchmark_runner.py`) running 10 canonical scenarios:

| Metric | Target | Sentinel Result | Status |
|---|---|---|---|
| **Mission Success Rate** | $\ge 95\%$ | **100.0%** (10/10) | ✅ Passed |
| **Verified Decision Rate** | $\ge 90\%$ | **100.0%** | ✅ Passed |
| **Unsupported Claim Rate** | $0.0\%$ | **0.0%** (0 unverified) | ✅ Passed |
| **Transient 503 Recovery Rate** | $100\%$ | **100.0%** (Exponential Backoff) | ✅ Passed |
| **Human Approval Gate Accuracy** | $100\%$ | **100.0%** (Zero unauthorized mutations) | ✅ Passed |
| **Postcondition Validation** | $100\%$ | **100.0%** (9/9 verified) | ✅ Passed |

### Evaluated Benchmark Scenarios:
1. `BENCH-01`: Baseline Cloudflare Architecture Research (D1 vs KV).
2. `BENCH-02`: Opposing Agent Workload Assumptions (D1 vs Durable Objects).
3. `BENCH-03`: Weak Evidence Auto-Enrichment and Citation Grounding.
4. `BENCH-04`: Transient External Tool 503 Fault Recovery with Exponential Backoff.
5. `BENCH-05`: Medium-Risk Mutating Action Human Approval Gating.
6. `BENCH-06`: Human Approval Rejection Safety and Non-Execution Guarantee.
7. `BENCH-07`: Closed-Loop Postcondition State Verification.
8. `BENCH-08`: D1 Relational Querying Bounds & Transaction Isolation.
9. `BENCH-09`: Vectorize vs KV Hybrid Semantic Cache Architecture.
10. `BENCH-10`: End-to-End Edge Migration ADR Pipeline.

---

## 🚀 Quickstart & Local Installation

### Prerequisites
- Python 3.9+
- `pip` or `uv`

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/<your-username>/sentinel-cloudflare-agent.git
cd sentinel-cloudflare-agent
pip install -r requirements.txt
```

### 2. Run the Deep Test Suite
```bash
pytest -v
# Output: 10 passed in 0.22s
```

### 3. Run the Autonomous Benchmark Suite
```bash
python tests/benchmark_runner.py
# Generates tests/benchmark_report.json
```

### 4. Launch the Sentinel Server & Web UI
```bash
python -m sentinel.server
# Server running at: http://localhost:8787
```
Open **`http://localhost:8787`** in your browser to experience:
- 🎯 **Interactive Mission Control** with quick architectural scenarios.
- ⚡ **Live Multi-Agent Execution DAG** with real-time WebSocket state streaming.
- ⚠️ **Interactive Disagreement Alert** showing targeted resolution in action.
- 🛡️ **Human Approval Modal** for reviewing and executing mutating tool calls.
- ⚡ **Simulated Tool 503 Fault Injection** demonstrating instant durable recovery.
- 📊 **Reliability Benchmark Dashboard** displaying live metrics.

---

## 🌐 Deploying to Cloudflare

Sentinel is pre-configured with `wrangler.jsonc` supporting Cloudflare Python Workers and Workers AI:

```bash
# Login to Cloudflare
npx wrangler login

# Deploy to Cloudflare Edge
npx wrangler deploy
```

---

## 📁 Repository Structure

```
lively-kepler/
├── sentinel/                        # Core Python Agent Framework
│   ├── agents/                      # Specialized Agent Personas
│   │   ├── planner.py               # Objective decomposition
│   │   ├── researcher.py            # Grounded parallel research
│   │   ├── verifier.py              # Adversarial verification & conflict detection
│   │   ├── targeted.py              # Targeted conflict resolution agent
│   │   └── analyst.py               # Recommendation synthesis & ADR generation
│   ├── orchestrator/                # Durable Coordination & State
│   │   ├── mission_workflow.py      # End-to-end durable workflow coordinator
│   │   └── state_machine.py         # In-memory mission store & metrics journal
│   ├── reliability/                 # Verification & Guardrail Engine
│   │   ├── confidence.py            # 4-factor deterministic scoring
│   │   ├── conflicts.py             # Disagreement & divergence detector
│   │   ├── evidence.py              # Bipartite evidence graph & citation auditor
│   │   ├── policy.py                # Cloudflare Engineering Codex policy-as-code
│   │   └── postconditions.py        # Closed-loop live state verification
│   ├── tools/                       # Tool Integrations & Fault Injection
│   │   ├── github_tool.py           # GitHub tool with transient 503 simulation
│   │   └── web_tool.py              # Grounded Cloudflare documentation knowledge
│   ├── config.py                    # Environment & configuration loader
│   ├── llm.py                       # Multi-provider client (Gemini, Workers AI, Fallback)
│   ├── server.py                    # FastAPI server & WebSocket dispatcher
│   └── types.py                     # Pydantic v2 data models & schemas
├── frontend/                        # Cybernetic Web User Interface
│   ├── index.html                   # Mission Control, DAG, & Benchmark dashboard
│   ├── style.css                    # Dark glassmorphism Cloudflare styling
│   └── app.js                       # WebSocket client & DAG state controller
├── tests/                           # Deep Testing & Benchmark Suite
│   ├── test_unit.py                 # Pure unit tests for reliability components
│   ├── test_deep.py                 # End-to-end integration & fault injection tests
│   ├── test_scenarios.json          # 10 canonical benchmark scenarios
│   ├── benchmark_runner.py          # Automated benchmark execution engine
│   └── benchmark_report.json        # Persisted benchmark output & metrics
├── .env.example                     # API key documentation template
├── wrangler.jsonc                   # Cloudflare Workers configuration
├── requirements.txt                 # Python dependencies
├── ARCHITECTURE.md                  # Deep architectural specification
├── PROMPTS.md                       # AI development prompt history log
└── README.md                        # Project documentation
```

---

## 📄 License
MIT License. Created for the Cloudflare Platforms & Productivity Engineering challenge.
