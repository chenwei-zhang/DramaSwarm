# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_agent.py -v
pytest tests/test_agent.py -v -k "test_name"       # single test

# Run all crisis & temporal tests
pytest tests/test_crisis_engine.py tests/test_temporal_graph.py -v

# Run demo (rule engine, no LLM needed)
python -m demos.variety_show_simulation

# Run crisis simulation demo (rule mode, no LLM needed)
python -m demos.crisis_simulation

# Run demo with LLM
python -m demos.variety_show_simulation --llm --provider gemini --turns 10

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

### Core Simulation Flow

```
EventLoop.run() → per turn:
  1. Preparation   → select active agents
  2. Perception    → inject environment description + personalized reaction context
  3. Decision      → agent.think()
  4. Action        → agent speak/act/wait → bridge to Environment.add_event()
  5. Reflection    → memory decay
  6. Cleanup       → cap history, reaction system decay, snapshot
```

Agent actions are bridged to `Environment.add_event()` which triggers the full reaction chain via `ReactionBus.dispatch()`. Reactions feed back to agents through `perceive()` with personalized context from `get_agent_reaction_context()`.

### Multi-Layer Reaction System

The centerpiece of the environment module. `ReactionBus` dispatches events through 5 priority-ordered layers, each reading context enriched by previous layers:

1. **PublicOpinionLayer** — keyword-based sentiment shift, approval scores (0-100), fan reaction generation
2. **MediaLayer** — template-based headline generation with media-type amplification (tabloid vs mainstream)
3. **SocialPlatformLayer** — hot search board with rank/heat management
4. **GovernmentLayer** — 5-level sensitive keyword scanning → regulatory escalation (warning → ban)
5. **CommercialLayer** — brand endorsement tracking, approval-driven brand actions (continue → terminated)

Cross-layer effect: Government layer can censor social platform topics, reducing visibility. Commercial layer reads public opinion approval scores.

All layers share `ReactionLayer` ABC with `react()`, `get_state()`, `get_description()`, `decay()`.

### Key Module Relationships

```
swarmsim/core/
├── agent.py              # Agent → SimpleAgent (rule) / LLMAgent (LLM)
│                         # Has internal Memory class (not from memory/base.py)
├── environment/          # Package, not a single file
│   ├── base.py           # Environment base, integrates ReactionBus
│   ├── variety_show.py   # VarietyShowEnvironment (budget, tasks, screen time)
│   ├── reaction_bus.py   # Dispatches events to 5 layers, manages snapshots
│   ├── models.py         # All enums and dataclasses for reaction system
│   └── layers/           # 5 reaction layer implementations
├── event_loop.py         # EventLoop → SequentialEventLoop → InteractiveEventLoop
├── factory.py            # AgentFactory, VarietyShowFactory with cast templates
└── observer.py           # Observer, Reporter, InteractiveObserver

swarmsim/graph/
├── knowledge_graph.py    # networkx MultiDiGraph engine, loads from JSON/mock
└── temporal.py           # TemporalKnowledgeGraph — date-indexed, person timelines

swarmsim/crisis/          # Crisis simulation engine
├── models.py             # CrisisPhase(6), PRAction(10), CrisisState, etc.
├── timeline.py           # 1 turn = 1 day, 6-phase lifecycle
├── action_space.py       # 10 PR actions × 6 phases effect matrix + Big Five mods
├── persona_agent.py      # CelebrityPersonaAgent (rule/LLM), builds persona from GraphRAG
├── vacuum_detector.py    # Silence → rumor cascade, probability escalates with days
├── intervention.py       # User what-if conditions (forced actions, external events)
├── scenario_engine.py    # CrisisScenarioEngine (load) + CrisisSimulation (async run loop)
└── outcome_analyzer.py   # Compare sim vs historical baseline, generate PR recommendations

swarmsim/viz/
├── server.py             # FastAPI app, uses TemporalKnowledgeGraph, mounts all routers
├── api_graph.py          # Graph API routes
├── api_simulation.py     # Simulation API routes
├── api_crisis.py         # Crisis API: 10 endpoints (scenarios, start, step, run, intervene, etc.)
└── serializer.py         # networkx → D3 JSON

swarmsim/llm/client.py    # LLM client: Gemini, OpenAI, Anthropic via get_client()
swarmsim/memory/base.py   # MemoryStore ABC → InMemoryStore, SQLiteStore
celebrity_scraper/        # Independent module: 5 web spiders + mock data
```

### Crisis Simulation Architecture

`CrisisSimulation.step()` runs one simulated day:
1. `timeline.advance_day()` → determine CrisisPhase (breakout→escalation→peak→mitigation→resolution→aftermath)
2. `intervention_system.check()` → apply user's what-if conditions
3. Each `CelebrityPersonaAgent` generates a `CrisisAction` (PRAction enum)
4. `InformationVacuumDetector` checks silence → generates rumors
5. `CrisisActionSpace.compute_effect()` → apply approval/heat/brand deltas
6. Generate trending topics, media headlines, update brand statuses
7. Daily decay: heat -10%, approval regresses toward 50

Agent personality is built from GraphRAG data (biography keywords → Big Five traits). The persona_agent supports rule-based mode (decision matrix) and LLM mode (structured prompt → parse PRAction). Rule mode needs no API key.

### Agent Types

- **SimpleAgent** — rule-based responses by role, no API needed, fast
- **LLMAgent** — calls LLM via `swarmsim.llm.get_client()`, falls back to SimpleAgent on failure
- Agent roles: `LEADER`, `PEACEMAKER`, `DRAMA_QUEEN`, `SLACKER`, `PERFECTIONIST`, `WILDCARD`

### Event Loop Variants

- **EventLoop** — standard, random action order, 60% speak / 20% act / 20% wait
- **SequentialEventLoop** — agents speak in order, later agents hear earlier ones
- **InteractiveEventLoop** — supports external event injection

## Code Conventions

- **Language**: All UI strings, comments, docstrings, and user-facing text are in Chinese. Variable/method names are English snake_case.
- **Reaction keywords**: Hardcoded Chinese in `public_opinion.py` and `government.py` (e.g., "出轨", "封杀", "吸毒"). When adding new keywords, maintain consistency with existing dictionaries.
- **No build system**: `requirements.txt` only, no `pyproject.toml` or `setup.py`.
- **Testing**: pytest with class-based tests. Async tests use `pytest-asyncio`. No CI configured.
- **Severity estimation**: `EventLoop._estimate_severity()` uses keyword matching on action content — extend the word lists when adding new event types.
- **Anti-repetition**: `EventLoop._is_repetitive()` checks word overlap to prevent agents from repeating content.
- **Always respond in Chinese** when communicating with the user.
