import logging
import time
import math
from typing import Tuple

from llama_index.core.workflow import WorkflowTimeoutError
from llama_index.core.llms import LLM
from droidrun import DroidAgent

from eval.portal.accessibility import enable_accessibility_service
from eval.env.client import AndroidEnvClient
from eval.tools import AndroidWorldTools
from eval.tracker import (
    track_task,
    TaskResult,
    get_task_result,
)
from eval.portal.keepalive import KeepOverlayDisabled

logger = logging.getLogger(__name__)


async def run_task_on_env(
    env: AndroidEnvClient,
    device_serial: str,
    llm: LLM,
    task_name: str,
    task_idx: int,
    max_steps_multiplier: int,
    timeout_multiplier: int,
    vision: bool,
    reasoning: bool,
    reflection: bool,
    tracing: bool,
    debug: bool,
) -> Tuple[TaskResult, Exception | None]:
    env.reset(go_home=True)
    task_goal = env.get_task_goal(task_name, task_idx)
    task_complexity = env.get_task_complexity(task_name, task_idx)

    max_steps = math.ceil(task_complexity * max_steps_multiplier)
    max_retries = math.ceil(max_steps / 10)
    timeout = math.ceil(task_complexity * timeout_multiplier)

    logger.info(
        f"Initializing Task {task_name} {task_idx} | Complexity {task_complexity} -> {max_steps} max steps | {task_goal} within {timeout} seconds"
    )

    try:
        env.initialize_task(task_name, task_idx)
        logger.debug("Task initialized successfully")
    except Exception as e:
        raise RuntimeError(f"Error initializing task {task_name} {task_idx}: {e}")

    # try:
    #     logger.debug("Enabling accessibility service...")
    #     await enable_accessibility_service(
    #         device_serial=device_serial,
    #         disable_first=True,
    #     )
    #     logger.debug("Accessibility service enabled")
    # except Exception as e:
    #     raise RuntimeError(f"Error enabling accessibility service: {e}")

    with KeepOverlayDisabled(device_serial):
        logger.info(
            f"Initializing DroidAgent with {max_steps} steps and {timeout} timeout"
        )

        tools = AndroidWorldTools(device_serial, env)
        agent = DroidAgent(
            goal=task_goal,
            llm=llm,
            tools=tools,
            reasoning=reasoning,
            enable_tracing=tracing,
            debug=debug,
            max_steps=max_steps,
            timeout=timeout,
            save_trajectories="none",
            reflection=reflection,
            vision=vision,
        )

        logger.debug("DroidAgent initialized successfully")

        task_result = track_task(task_name, task_idx, task_goal, max_steps)

        try:

            logger.info("Running DroidAgent...")
            agent_result = await agent.run()
            logger.debug("DroidAgent completed successfully")

            score = env.get_task_score(task_name, task_idx)
            logger.info(f"Task {task_name} {task_idx} score: {score}")

            result = get_task_result(
                task_result,
                agent,
                score=score,
                agent_result=agent_result,
                device=device_serial,
            )
        except WorkflowTimeoutError as e:
            logger.warn(f"Droidrun timed out for task {task_name} {task_idx}: {e}")
            score = env.get_task_score(task_name, task_idx)
            logger.info(f"Task {task_name} {task_idx} score: {score}")
            result = get_task_result(
                task_result,
                agent,
                score=score,
                agent_result={
                    "steps": agent.step_counter,
                    "success": False,
                    "reason": f"Timeout after {timeout} seconds",
                },
                device=device_serial,
            )
        except Exception as e:
            logger.error(f"Error completing task {task_name} {task_idx}: {e}")
            result = get_task_result(
                task_result,
                agent,
                error=repr(e),
                device=device_serial,
            )
        # finally:
        #     try:
        #         write_task_trajectory(task_name, task_idx, agent)
        #     except Exception as e:
        #         logger.warn(
        #             f"Could not write task trajectory for {task_name} {task_idx}: {e}"
        #         )
        #         send_discord_exception(
        #             e,
        #             "couldn't save task trajectory",
        #             task_name,
        #             task_idx,
        #             task_goal,
        #             device_serial,
        #         )

        try:
            logger.debug(f"Tearing down task {task_name} {task_idx}")
            env.tear_down_task(task_name, task_idx)
        except Exception as e:
            logger.error(f"Error tearing down task {task_name} {task_idx}: {e}")
            logger.info("Continuing to next task...")
            return (result, e)

        # TODO add trajectory to task result

        return (result, None)
