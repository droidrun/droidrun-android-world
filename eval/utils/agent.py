"""
Agent management utilities for AndroidWorld benchmarks.
"""

import logging
from typing import Dict, Any, Tuple, Optional

# Import DroidRun modules
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm

logger = logging.getLogger("android_world_bench")


def create_agent(
    device_serial: str,
    goal: str,
    llm_provider: str,
    llm_model: str,
    temperature: float = 0.2,
    max_steps: int = 50,
    timeout: int = 600,
    max_retries: int = 3,
    reasoning: bool = True,
    debug: bool = True,
) -> Tuple[DroidAgent, Dict[str, Any]]:
    """Create and configure a DroidRun agent.

    Args:
        device_serial: Device serial number
        goal: Description of the task
        llm_provider: LLM provider name
        llm_model: LLM model name
        temperature: Temperature for LLM
        max_steps: Maximum number of steps
        timeout: Timeout in seconds
        max_retries: Maximum number of retries

    Returns:
        Tuple of (agent, agent configuration)
    """
    logger.info(f"Creating DroidRun agent for task")

    # Load LLM
    logger.info(f"Loading LLM: provider={llm_provider}, model={llm_model}")
    llm = load_llm(provider_name=llm_provider, model=llm_model, temperature=temperature)

    # Create agent
    logger.info(f"Creating DroidAgent for task: {goal}")
    agent = DroidAgent(
        goal=goal,
        llm=llm,
        max_steps=max_steps,
        timeout=timeout,
        max_retries=max_retries,
        device_serial=device_serial,
        reasoning=reasoning,
        # trajectories are saved by the benchmark runner
        save_trajectories=False,
        debug=debug,
    )

    # Store configuration
    config = {
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "temperature": temperature,
        "max_steps": max_steps,
        "timeout": timeout,
        "max_retries": max_retries,
    }

    logger.info("Agent created successfully")
    return agent, config


async def run_agent(agent: DroidAgent, task_name: str) -> Dict[str, Any]:
    """Run the agent on a task.

    Args:
        agent: The agent to run
        task_name: Name of the task

    Returns:
        Result data
    """
    logger.info(f"Running agent for task: {task_name}")

    try:
        # Run the agent
        result = await agent.run()
        logger.info(f"Agent completed task: {task_name}")
        return result
    except Exception as e:
        logger.error(f"Error running agent for task {task_name}: {e}")
        return None
