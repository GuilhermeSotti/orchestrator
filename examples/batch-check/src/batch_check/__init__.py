"""Consumer project of the Orchestrator that checks batch files and sends notifications."""

from batch_check.automation import Parameters, check_batch

__all__ = ["Parameters", "check_batch"]
