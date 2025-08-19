import json
import os
from typing import Dict, Any, List
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from droidrun import DroidAgent
from pathlib import Path
import requests

logger = logging.getLogger("tracker")

"""
@dataclass
class TaskSummary:
    task_name: str
    task_idx: int
    task_id: int
    score: float
    success: bool
    steps_taken: int
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    trajectory_summary:


@dataclass
class Summary:
    total_tasks: int = 0
    successful_tasks: int = 0
    success_rate: float = 0.0
    tasks: List[TaskSummary] = field(default_factory=list)
    avg_steps: float = 0.0
    avg_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def update_progress():
    logger.debug("Updating progress")


def update_summary():
    logger.debug("Updating summary")
"""


@dataclass
class TrajectoryItem:
    pass


@dataclass
class TrajectoryStats:
    total_steps: int = field(default=0)
    planning_steps: int = field(default=0)
    execution_steps: int = field(default=0)


# legacy result format used in web repr
@dataclass
class TaskResult:
    task_id: int
    task_name: str
    task_idx: int
    task_description: str
    max_steps: int
    success: float = field(default=0.0)
    agent_success: bool = field(default=False)
    steps_taken: int = field(default=0)
    execution_time: float = field(default=0.0)
    reasoning: bool = field(default=False)
    final_thought: str = field(default="")
    logs: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str | None = field(default=None)
    trajectory: List[TrajectoryItem] = field(default_factory=list)
    trajectory_stats: TrajectoryStats = field(default_factory=TrajectoryStats)
    device: str = field(default="")


OUTPUT_DIR = "eval_results"


def get_task_result_path(task_name: str) -> Path:
    dname = f"{task_name.replace(' ', '_')}"
    opath = Path(OUTPUT_DIR, dname)
    opath.mkdir(parents=True, exist_ok=True)
    return opath


def track_task(task_name: str, task_idx: int, goal: str, max_steps: int) -> TaskResult:
    return TaskResult(
        task_id=0,
        task_name=task_name,
        task_idx=task_idx,
        task_description=goal,
        max_steps=max_steps,
    )


def get_task_result(
    task_result: TaskResult,
    agent: DroidAgent,
    score: float = 0.0,
    agent_result: Dict[str, Any] | None = None,
    error: str | None = None,
    device: str = None,
) -> TaskResult:
    task_result.success = score

    if agent_result is not None:
        task_result.agent_success = agent_result["success"]
        task_result.steps_taken = agent_result["steps"]
        task_result.final_thought = agent_result["reason"]

    if error is not None:
        task_result.error = error

    started_at = datetime.fromisoformat(task_result.timestamp)
    task_result.execution_time = (datetime.now() - started_at).total_seconds()

    task_result.logs = []
    task_result.trajectory = []
    task_result.trajectory_stats = TrajectoryStats(
        total_steps=0, execution_steps=0, planning_steps=0
    )
    task_result.reasoning = agent.reasoning
    if device is not None:
        task_result.device = device

    return task_result


def write_task_result(
    task_result: TaskResult,
):
    agent_result_str = json.dumps(
        {
            "success": task_result.agent_success,
            "steps": task_result.steps_taken,
            "output": task_result.final_thought,
        }
    )
    logger.debug(
        f"Writing task result for {task_result.task_name} {task_result.task_idx} with score {task_result.success}. Agent result: {agent_result_str}"
    )

    dpath = get_task_result_path(task_result.task_name)
    fpath = dpath / "result.json"
    try:
        with open(fpath, "w") as f:
            json.dump(asdict(task_result), f, indent=2)
        logger.debug(f"Wrote task {task_result.task_name} result to {fpath}")
    except Exception as e:
        logger.error(f"Error writing task result to {fpath}: {e}")

    send_discord_task_result(task_result)


def write_task_trajectory(task_name: str, task_idx: int, agent: DroidAgent):
    logger.debug(f"Writing task trajectory for {task_name} {task_idx}.")

    dpath = get_task_result_path(task_name)
    trk_path = agent.trajectory.save_trajectory(dpath)
    logger.debug(f"Wrote task {task_name} trajectory to {trk_path}")


def get_embed_author(device: str) -> dict:
    return {
        "name": f"Device: {device}",
        "url": f"https://supervisor.droidrun.ai/#!action=stream&udid={device}&player=webcodecs&ws=wss%3A%2F%2Fsupervisor.droidrun.ai%2F%3Faction%3Dproxy-adb%26remote%3Dtcp%253A8886%26udid%3D{device}",
    }


def create_task_result_embed(task_result: TaskResult) -> dict:
    """
    Creates a Discord embed JSON structure for a TaskResult object.

    Args:
        task_result: TaskResult dataclass instance

    Returns:
        dict: Discord embed JSON structure
    """

    # Determine embed color and status based on benchmark results
    if task_result.success == 1.0:
        color = 0x0D9373  # Green for perfect benchmark score
        status_emoji = "✅"
    elif task_result.error:
        color = 0xE74C3C  # Red for error
        status_emoji = "❌"
    elif task_result.success != 1.0 and task_result.agent_success:
        color = 0xF5B041  # Orange for mismatch - needs manual verification
        status_emoji = "🔍"
    elif task_result.success > 0.0:
        color = 0xF7DC6F  # Yellow for partial success
        status_emoji = "⚠️"
    else:
        color = 0x5D6D7E  # Gray for failure
        status_emoji = "❌"

    # Format execution time for readability
    if task_result.execution_time < 60:
        exec_time_str = f"{task_result.execution_time:.2f}s"
    else:
        minutes = int(task_result.execution_time // 60)
        seconds = task_result.execution_time % 60
        exec_time_str = f"{minutes}m {seconds:.1f}s"

    # Create the embed structure
    embed = {
        "title": f"{status_emoji} {task_result.task_name}",
        "description": f"**Goal:** {task_result.task_description}",
        "color": color,
        "timestamp": task_result.timestamp,
        "fields": [
            {
                "name": "📊 Benchmark Results",
                "value": f"**Benchmark Score:** {task_result.success:.1%}\n"
                f"**Agent Self-Assessment:** {'Success' if task_result.agent_success else 'Failed'}\n"
                f"**Steps:** {task_result.steps_taken}/{task_result.max_steps}",
                "inline": True,
            },
            {
                "name": "⏱️ Execution",
                "value": f"**Time:** {exec_time_str}\n"
                f"**Reasoning:** {'Enabled' if task_result.reasoning else 'Disabled'}\n"
                f"**Task ID:** {task_result.task_id}",
                "inline": True,
            },
        ],
        "footer": {
            "text": f"Task Index: {task_result.task_idx} | {len(task_result.logs)} log entries"
        },
        "author": get_embed_author(task_result.device),
    }

    # Add manual verification notice if there's a mismatch
    if task_result.success != 1.0 and task_result.agent_success:
        embed["fields"].append(
            {
                "name": "🔍 Manual Verification Required",
                "value": "Agent believes it succeeded but benchmark score is not perfect. Please manually verify the results.",
                "inline": False,
            }
        )

    # Add final thought if available
    if task_result.final_thought and task_result.final_thought.strip():
        embed["fields"].append(
            {
                "name": "💭 Final Thought",
                "value": task_result.final_thought[:1024],  # Discord field value limit
                "inline": False,
            }
        )

    # Add error information if present
    if task_result.error:
        embed["fields"].append(
            {
                "name": "❌ Error",
                "value": f"```\n{task_result.error[:1000]}\n```",  # Truncate long errors
                "inline": False,
            }
        )

    # Add trajectory stats if available
    if hasattr(task_result.trajectory_stats, "__dict__"):
        stats_dict = task_result.trajectory_stats.__dict__
        if any(stats_dict.values()):  # Only add if there are actual stats
            stats_text = "\n".join(
                [
                    f"**{k.replace('_', ' ').title()}:** {v}"
                    for k, v in stats_dict.items()
                    if v
                ]
            )
            if stats_text:
                embed["fields"].append(
                    {"name": "📈 Trajectory Stats", "value": stats_text, "inline": True}
                )

    return embed


def create_suite_exception_embed(
    ex: Exception,
    state: str,
    task_name: str = None,
    task_idx: int = None,
    task_goal: str = None,
    device: str = None,
    timestamp: str = None,
) -> dict:
    """
    Creates a Discord embed JSON structure for benchmark suite exceptions.

    Args:
        ex: The Exception object
        state: Current state when exception occurred (e.g., "task_setup", "initialization", "cleanup")
        task_name: Optional task name if exception is task-specific
        task_idx: Optional task index if exception is task-specific
        task_goal: Optional task goal/description if exception is task-specific
        timestamp: Optional timestamp, defaults to current time

    Returns:
        dict: Discord embed JSON structure
    """
    import traceback
    from datetime import datetime

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    exception_type = type(ex).__name__
    exception_message = str(ex)

    # Always red for suite exceptions
    color = 0xFF0000

    # Different emojis based on exception type and state
    if "setup" in exception_type.lower() or "setup" in state.lower():
        status_emoji = "⚙️"
    elif "timeout" in exception_type.lower() or "timeout" in state.lower():
        status_emoji = "⏱️"
    elif "resource" in exception_type.lower() or "memory" in exception_type.lower():
        status_emoji = "💾"
    elif "network" in exception_type.lower() or "connection" in exception_type.lower():
        status_emoji = "🌐"
    elif "config" in exception_type.lower() or "initialization" in state.lower():
        status_emoji = "⚙️"
    elif "cleanup" in state.lower():
        status_emoji = "🧹"
    else:
        status_emoji = "💥"

    embed = {
        "title": f"{status_emoji} Benchmark Suite Exception",
        "description": f"**Exception Type:** `{exception_type}`\n**State:** `{state}`",
        "color": color,
        "timestamp": timestamp,
        "fields": [
            {
                "name": "❌ Error Details",
                "value": f"```\n{exception_message[:1000]}\n```",  # Truncate long messages
                "inline": False,
            }
        ],
        "footer": {"text": "Benchmark Suite Error"},
        "author": get_embed_author(device) if device is not None else {},
    }

    # Add task information if available
    if task_name is not None or task_idx is not None or task_goal is not None:
        task_info = []
        if task_idx is not None:
            task_info.append(f"**Task Index:** {task_idx}")
        if task_name is not None:
            task_info.append(f"**Task Name:** {task_name}")
        if task_goal is not None:
            task_info.append(f"**Goal:** {task_goal}")

        embed["fields"].insert(
            0,
            {"name": "🎯 Affected Task", "value": "\n".join(task_info), "inline": True},
        )

    # Add traceback
    traceback_info = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
    if traceback_info and traceback_info.strip():
        # Truncate traceback to fit Discord limits
        truncated_traceback = traceback_info[:1500]
        if len(traceback_info) > 1500:
            truncated_traceback += "\n... (truncated)"

        embed["fields"].append(
            {
                "name": "🔍 Traceback",
                "value": f"```python\n{truncated_traceback}\n```",
                "inline": False,
            }
        )

    return embed


def send_discord_embed(embed: dict):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url is None:
        logger.error("DISCORD_WEBHOOK_URL is not set")
        return

    try:
        res = requests.post(
            webhook_url,
            json={"embeds": [embed]},
        )
        res.raise_for_status()
        logger.debug(f"Sent discord embed {embed['title']}")
    except Exception as e:
        logger.error(f"Error sending discord embed: {e}")


def send_discord_task_result(result: TaskResult):
    embed = create_task_result_embed(result)
    send_discord_embed(embed)


def send_discord_exception(
    ex: Exception,
    state: str,
    task_name: str = None,
    task_idx: int = None,
    task_goal: str = None,
    device: str = None,
):
    embed = create_suite_exception_embed(
        ex, state, task_name, task_idx, task_goal, device
    )
    send_discord_embed(embed)


# Example usage:
if __name__ == "__main__":
    # Example TaskResult for testing
    from datetime import datetime

    sample_task = TaskResult(
        task_id=12345,
        task_name="Web Scraping Challenge",
        task_idx=1,
        task_description="Extract product information from e-commerce website",
        max_steps=50,
        success=0.85,
        agent_success=True,
        steps_taken=23,
        execution_time=45.7,
        reasoning=True,
        final_thought="Successfully extracted all required product data with minimal errors.",
        logs=["Step 1: Initialized", "Step 2: Connected", "Step 3: Scraped data"],
        timestamp=datetime.now().isoformat(),
        error=None,
    )

    send_discord_task_result(sample_task)

    try:
        # Simulate an exception
        raise ValueError("Docker container 'task_env_123' could not be started")
    except Exception as e:
        suite_exception_embed = create_suite_exception_embed(
            ex=e,
            state="task_setup",
            task_name="Web Scraping Challenge",
            task_idx=5,
            task_goal="Extract product information from e-commerce website",
        )
        send_discord_embed(suite_exception_embed)
