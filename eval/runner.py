import logging
import time
import math

from llama_index.core.workflow import WorkflowTimeoutError
from llama_index.core.llms import LLM
from droidrun import DeviceManager, DroidAgent

from eval.android_env_client import AndroidEnvClient
from eval.tools import AndroidWorldTools
from eval.tracker import (
    track_task,
    write_task_result,
    write_task_trajectory,
    send_discord_exception,
)
from eval.portal.accessibility import enable_accessibility_service
from eval.portal.keepalive import OverlayKeepalive

logger = logging.getLogger("runner")


class Runner:
    def __init__(
        self, device: str = "emulator-5554", base_url: str = "http://localhost:5000"
    ):
        self.device = device
        self.base_url = base_url
        self.env = AndroidEnvClient(base_url)
        self.keepalive = OverlayKeepalive(device_serial=self.device)

    def wait_for_env(self):
        logger.debug("Waiting for environment to be healthy...")
        while True:
            if not self.env.health():
                print("Environment is not healthy, waiting for 1 second...")
                time.sleep(1)
            else:
                break
        logger.debug("Environment is healthy")

    async def install_portal(self, portal_apk: str):
        logger.info(f"Installing {portal_apk}...")
        device_manager = DeviceManager()
        device = await device_manager.get_device(self.device)
        await device.install_app(portal_apk, reinstall=True)
        logger.info("Portal installed successfully")

    async def run(
        self,
        llm: LLM,
        task_name: str,
        task_idx: int,
        max_steps_multiplier: int,
        timeout_multiplier: int,
        reasoning: bool,
        reflection: bool,
        tracing: bool,
        debug: bool,
    ):
        self.env.reset(go_home=True)
        task_goal = self.env.get_task_goal(task_name, task_idx)
        task_complexity = self.env.get_task_complexity(task_name, task_idx)

        max_steps = math.ceil(task_complexity * max_steps_multiplier)
        max_retries = math.ceil(max_steps / 10)
        timeout = math.ceil(task_complexity * timeout_multiplier)

        logger.info(
            f"Initializing Task {task_name} {task_idx} | Complexity {task_complexity} -> {max_steps} max steps | {task_goal} within {timeout} seconds"
        )

        try:
            self.env.initialize_task(task_name, task_idx)
            logger.debug("Task initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing task {task_name} {task_idx}: {e}")
            logger.info("Continuing to next task...")
            send_discord_exception(
                e,
                "couldn't initialize task",
                task_name,
                task_idx,
                task_goal,
                self.device,
            )
            return

        try:
            logger.debug("Enabling accessibility service...")
            await enable_accessibility_service(
                device_serial=self.device,
                disable_first=True,
            )
            logger.debug("Accessibility service enabled")
            logger.debug("Starting droidrun portal keepalive...")
            self.keepalive.start()
            logger.debug("Droidrun portal keepalive started")
        except Exception as e:
            logger.error(f"Error enabling accessibility service: {e}")
            logger.info("Continuing to next task...")
            send_discord_exception(
                e,
                "couldn't enable portal accessibility service",
                task_name,
                task_idx,
                task_goal,
                self.device,
            )
            return

        logger.info(
            f"Initializing DroidAgent with {max_steps} steps, {max_retries} retries, and {timeout} timeout"
        )

        tools = AndroidWorldTools(self.device, self.env)
        agent = DroidAgent(
            task_goal,
            llm,
            tools,
            reasoning=reasoning,
            enable_tracing=tracing,
            debug=debug,
            max_steps=max_steps,
            max_retries=max_retries,
            timeout=timeout,
            save_trajectories=False,
            reflection=reflection,
            device_serial=self.device,
        )

        logger.debug("DroidAgent initialized successfully")

        task_result = track_task(task_name, task_idx, task_goal, max_steps)

        try:

            logger.info("Running DroidAgent...")
            agent_result = await agent.run()
            logger.debug("DroidAgent completed successfully")

            score = self.env.get_task_score(task_name, task_idx)
            logger.info(f"Task {task_name} {task_idx} score: {score}")

            write_task_result(
                task_result,
                agent,
                score=score,
                agent_result=agent_result,
                device=self.device,
            )
        except WorkflowTimeoutError as e:
            logger.warn(f"Droidrun timed out for task {task_name} {task_idx}: {e}")
            score = self.env.get_task_score(task_name, task_idx)
            logger.info(f"Task {task_name} {task_idx} score: {score}")
            write_task_result(
                task_result,
                agent,
                score=score,
                agent_result={
                    "steps": agent.step_counter,
                    "success": False,
                    "reason": f"Timeout after {timeout} seconds",
                },
                device=self.device,
            )
        except Exception as e:
            logger.error(f"Error completing task {task_name} {task_idx}: {e}")
            write_task_result(task_result, agent, error=repr(e), device=self.device)
        finally:
            try:
                write_task_trajectory(task_name, task_idx, agent)
            except Exception as e:
                logger.warn(
                    f"Could not write task trajectory for {task_name} {task_idx}: {e}"
                )
                send_discord_exception(
                    e,
                    "couldn't save task trajectory",
                    task_name,
                    task_idx,
                    task_goal,
                    self.device,
                )

        try:
            logger.debug(f"Tearing down task {task_name} {task_idx}")
            self.env.tear_down_task(task_name, task_idx)
            self.keepalive.stop()
        except Exception as e:
            logger.error(f"Error tearing down task {task_name} {task_idx}: {e}")
            logger.info("Continuing to next task...")
            self.keepalive.stop()
            send_discord_exception(
                e,
                "couldn't tear down task",
                task_name,
                task_idx,
                task_goal,
                self.device,
            )
