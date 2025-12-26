#!/bin/bash
# Claude Flow Status Line Command
# This script provides real-time status information for Claude Code

# Get current swarm status
SWARM_STATUS=$(npx claude-flow@alpha swarm status --json 2>/dev/null | jq -r '.status // "idle"' 2>/dev/null || echo "idle")

# Get memory usage
MEMORY_COUNT=$(npx claude-flow@alpha memory list --count 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "0")

# Get active agents
AGENT_COUNT=$(npx claude-flow@alpha agent list --count 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "0")

# Get git branch
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "none")

# Output status line
echo "🌊 CF:${SWARM_STATUS} | 🧠 Mem:${MEMORY_COUNT} | 🤖 Agents:${AGENT_COUNT} | 🌿 ${GIT_BRANCH}"
