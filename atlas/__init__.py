"""Atlas: a self-hosted, MCP-native multi-agent platform.

A planner decomposes a goal into a typed plan, executor agents run MCP tools to
carry out each step, and a critic verifies the output and triggers targeted
retries. Runs are durably checkpointed so a crashed run can resume from the last
committed step.
"""

__version__ = "0.4.0"
