# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all crisis & temporal tests
pytest tests/test_crisis_engine.py tests/test_temporal_graph.py -v

# Run crisis & experiment tests
pytest tests/test_crisis_engine.py tests/test_experiment.py -v

# Run single test
pytest tests/test_crisis_engine.py -v -k "test_name"

# Run crisis simulation demo (rule mode, no LLM needed)
python -m demos.crisis_simulation

# Web visualization (includes crisis simulation tab)
python run_viz.py
# http://localhost:8765 → 知识图谱 tab + 危机模拟 tab

# Scraper test (mock mode)
python test_scraper.py mock 杨幂

# Scraper test (real mode, needs network)
python test_scraper.py real 杨幂
```

## Environment Setup

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Other keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) optional. Config via env vars: `LLM_PROVIDER` (default `gemini`), `LLM_MODEL` (default `gemini-3-flash-preview`), `MAX_AGENTS`, `SIMULATION_TICK_INTERVAL`, `DEFAULT_TURNS`.

## Architecture

### Crisis Simulation Flow

```
CrisisSimulation.step() → per day:
  1. Timeline      → CrisisTimeline.advance_day() → determine CrisisPhase
  2. Intervention  → InterventionSystem.check() → apply user's what-if conditions
  3. Decision      → sequential agent actions with peer_actions + audience_reactions
  4. Effects       → CrisisActionSpace.compute_effect() → approval/heat/brand deltas
  5. Reactions     → InformationVacuumDetector → silence → rumor cascade
  6. Update        → trending topics, media headlines, brand statuses
  7. Decay         → heat -10%, approval regresses toward role-specific target
```

### Key Module Relationships

```
swarmsim/graph/
├── knowledge_graph.py    # networkx MultiDiGraph engine, loads from JSON/mock
└── temporal.py           # TemporalKnowledgeGraph — date-indexed, person timelines

swarmsim/crisis/          # Crisis simulation engine
├── models.py             # CrisisPhase(6), PRAction(10), CrisisRole(4), InteractionMode, FreeAction(8), CrisisState, etc.
├── timeline.py           # 1 turn = 1 day, 6-phase lifecycle
├── action_space.py       # 10 PR actions × 6 phases effect matrix + Big Five mods
├── free_action_space.py  # FreeActionSpace — simplified effect computation (no phase modifiers)
├── persona_agent.py      # CelebrityPersonaAgent (rule/LLM), builds persona from GraphRAG
│                         # crisis_role (PERPETRATOR/VICTIM/ACCOMPLICE/BYSTANDER) injected by engine
│                         # Role-aware decision: perp banned from comeback, victim won't apologize
│                         # Extended peer_influence: 绯闻对象/前配偶 relationship handling
│                         # LLM prompt enhanced with role context + gossip_type
│                         # Supports peer_actions + audience_reactions for inter-agent interaction
│                         # Free mode: generate_free_response() / _rule_decide_free() / _llm_decide_free()
├── vacuum_detector.py    # Silence → rumor cascade, probability escalates with days
├── intervention.py       # User what-if conditions with trigger types (TIME_ABSOLUTE/TIME_RELATIVE/STATE_THRESHOLD)
│                         # External events (MEDIA_REPORT/VIDEO_LEAK/COMPETITOR_ANNOUNCE/etc.)
├── experiment.py         # ExperimentManager, Experiment, ExperimentGroup, ComparisonResult — A/B testing
├── scenario_engine.py    # CrisisScenarioEngine (load + role inference) + CrisisSimulation (async run loop)
│                         # _infer_person_roles(): auto-infer PERPETRATOR/VICTIM/ACCOMPLICE from graph relations
│                         # Sequential decision making: later agents see earlier actions
│                         # Branches on interaction_mode (CRISIS vs FREE)
│                         # Role-aware daily decay: perp target=25 rate=0.1, victim target=60 rate=0.8
├── message_bus.py        # Agent-to-agent message bus (broadcast/direct/per-type filtering)
├── audience.py           # AudiencePool (30 agents: 粉丝/路人/理中客/黑粉) + reaction templates
└── outcome_analyzer.py   # Compare sim vs historical baseline, generate PR recommendations

swarmsim/viz/
├── server.py             # FastAPI app, uses TemporalKnowledgeGraph, mounts all routers
├── api_graph.py          # Graph API routes
├── api_crisis.py         # Crisis API: scenarios, start, step, run, intervene, etc.
│                         # Experiment API: POST /experiment/create, POST /experiment/{id}/run,
│                         #   GET /experiment/{id}/compare, GET /experiments
└── serializer.py         # networkx → D3 JSON

swarmsim/llm/client.py    # LLM client: Gemini, OpenAI, Anthropic via get_client()
swarmsim/memory/base.py   # MemoryStore ABC → InMemoryStore, SQLiteStore
celebrity_scraper/        # Independent module: 5 web spiders + mock data
```

### Crisis Simulation Architecture

`CrisisSimulation.step()` runs one simulated day, branching on `interaction_mode` (CRISIS vs FREE):

**CRISIS mode** (original flow):
1. `timeline.advance_day()` → determine CrisisPhase (breakout→escalation→peak→mitigation→resolution→aftermath)
2. `intervention_system.check()` → apply user's what-if conditions
3. **Sequential decision making**: agents act in order; each sees `peer_actions` (earlier agents' actions) + `audience_reactions` from `AudiencePool`
4. **Relationship influence**: agent queries `kg.get_relationship_context()` for each peer's action, adjusts weights (spouse apologizes → I soften; rival counterattacks → I harden)
5. **Audience reactions**: `AudiencePool` (30 agents: 粉丝/路人/理中客/黑粉) generates comments based on action templates + persona bias
6. **Propagation**: `_check_propagation()` marks agents whose close relations took significant actions
7. `InformationVacuumDetector` checks silence → generates rumors
8. `CrisisActionSpace.compute_effect()` → apply approval/heat/brand deltas
9. Generate trending topics, media headlines, update brand statuses
10. Daily decay: heat -10%, approval regresses toward 50

**FREE mode** (open interaction):
- Agents choose from `FreeAction` enum: SPEAK, SUPPORT, CRITICIZE, COLLABORATE, SOCIALIZE, ANNOUNCE, IGNORE, PRIVATE_MSG, MEDIATE, RUMOR, RETREAT
- `FreeActionSpace` computes simplified effects without phase modifiers
- `persona_agent.py` methods: `generate_free_response()`, `_rule_decide_free()`, `_llm_decide_free()`

**Intervention system** supports 3 trigger types:
- `TIME_ABSOLUTE` — fire on a specific simulated day number
- `TIME_RELATIVE` — fire N days after scenario start
- `STATE_THRESHOLD` — fire when a metric crosses a threshold (approval, heat, brand_value) with comparator (gt/lt/gte/lte/eq)

**External events** (`ExternalEventType` enum): MEDIA_REPORT, VIDEO_LEAK, COMPETITOR_ANNOUNCE, REGULATORY_ACTION, BRAND_DECISION, CUSTOM — injectable via intervention conditions.

**Relationship changes**: tracked with types `strengthen`, `weaken`, `break`, `new`.

**A/B Experiments** (`crisis/experiment.py`):
- `ExperimentManager` manages experiments, each containing `ExperimentGroup` arms
- `Experiment` / `ExperimentGroup` / `ComparisonResult` dataclasses for structured comparison
- API endpoints: `POST /experiment/create`, `POST /experiment/{id}/run`, `GET /experiment/{id}/compare`, `GET /experiments`

`CrisisAction` has `triggered_by` and `trigger_relation` fields for tracking inter-agent causality, plus `free_action` field for free-mode actions. `CrisisState` includes `audience_reactions` and `interaction_log`. Agent personality is built from GraphRAG data (biography keywords → Big Five traits). The persona_agent supports rule-based mode (decision matrix) and LLM mode (structured prompt → parse PRAction). Rule mode needs no API key.

## Code Conventions

- **Language**: All UI strings, comments, docstrings, and user-facing text are in Chinese. Variable/method names are English snake_case.
- **No build system**: `requirements.txt` only, no `pyproject.toml` or `setup.py`.
- **Testing**: pytest with class-based tests. Async tests use `pytest-asyncio`. No CI configured.
- **Deterministic personality**: `CelebrityPersonaAgent` uses `hashlib.md5(persona_name)` to seed random decisions, ensuring the same persona always produces the same personality traits across runs.
- **Always respond in Chinese** when communicating with the user.
