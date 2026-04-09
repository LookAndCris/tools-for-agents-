# Skill Registry — tools-for-agents

Generated: 2026-04-09
Project: tools-for-agents (Sistema Inteligente de Gestión de Citas)

---

## User-Level Skills

| Skill | Path | Trigger |
|-------|------|---------|
| `test-driven-development` | `~/.config/opencode/skills/test-driven-development/SKILL.md` | Use when implementing any feature or bugfix, before writing implementation code |
| `systematic-debugging` | `~/.config/opencode/skills/systematic-debugging/SKILL.md` | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| `mcp-builder` | `~/.config/opencode/skills/mcp-builder/SKILL.md` | Use when building MCP servers to integrate external APIs or services |
| `find-skills` | `~/.config/opencode/skills/find-skills/SKILL.md` | Use when the user is looking for functionality that might exist as an installable skill |
| `skill-creator` | `~/.config/opencode/skills/skill-creator/SKILL.md` | Use when user asks to create a new skill, add agent instructions, or document patterns for AI |
| `skill-registry` | `~/.config/opencode/skills/skill-registry/SKILL.md` | Use when user says "update skills", "skill registry", or after installing/removing skills |

## SDD Phase Skills

| Skill | Path | Phase |
|-------|------|-------|
| `sdd-init` | `~/.config/opencode/skills/sdd-init/SKILL.md` | Initialize SDD context |
| `sdd-explore` | `~/.config/opencode/skills/sdd-explore/SKILL.md` | Explore and investigate ideas |
| `sdd-propose` | `~/.config/opencode/skills/sdd-propose/SKILL.md` | Create change proposal |
| `sdd-spec` | `~/.config/opencode/skills/sdd-spec/SKILL.md` | Write specifications |
| `sdd-design` | `~/.config/opencode/skills/sdd-design/SKILL.md` | Create technical design |
| `sdd-tasks` | `~/.config/opencode/skills/sdd-tasks/SKILL.md` | Break down into tasks |
| `sdd-apply` | `~/.config/opencode/skills/sdd-apply/SKILL.md` | Implement tasks |
| `sdd-verify` | `~/.config/opencode/skills/sdd-verify/SKILL.md` | Validate implementation |
| `sdd-archive` | `~/.config/opencode/skills/sdd-archive/SKILL.md` | Archive completed change |

## Project Conventions

No project-level convention files found (AGENTS.md, CLAUDE.md, .cursorrules, etc.).
Reference: `PRD.md` — Full product requirements and database schema.

---

## Notes for Sub-Agents

- **Persistence mode**: `engram`
- **SDD context topic_key**: `sdd-init/tools-for-agents`
- This is a **greenfield** project — no existing source code yet, only PRD.md
- TDD inside-out: start from domain layer (scheduling engine → policies → use cases → repos → tools)
