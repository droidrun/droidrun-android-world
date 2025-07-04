import argparse
import asyncio
import logging
import time
import textwrap
import os
import math

from eval.tools import AndroidWorldTools
from eval.android_env_client import AndroidEnvClient
from eval.tracker import (
    write_task_result,
    write_task_trajectory,
    track_task,
    send_discord_exception,
)
from eval.portal.accessibility import enable_accessibility_service
from eval.portal.keepalive import OverlayKeepalive

from llama_index.core.workflow import WorkflowTimeoutError
from droidrun import DroidAgent, load_llm, DeviceManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("android_world_bench")
logger.level = logging.DEBUG
logging.getLogger("droidrun").level = logging.DEBUG
logging.getLogger("android_world_tools").level = logging.DEBUG


class AndroidWorldBenchmark:
    def __init__(
        self,
        device: str = "emulator-5554",
        base_url: str = "http://localhost:5000",
    ) -> None:
        logger.info(
            f"Initializing AndroidWorldBenchmark with env device: {device} base_url: {base_url}"
        )
        self.device = device
        self.base_url = base_url
        self.env = AndroidEnvClient(base_url)

    def wait_for_env(self):
        logger.debug("Waiting for environment to be healthy...")
        while True:
            if not self.env.health():
                print("Environment is not healthy, waiting for 1 second...")
                time.sleep(1)
            else:
                break
        logger.debug("Environment is healthy")

    def list_tasks(self):
        logger.info("Listing tasks...")
        tasks = self.env.get_suite_task_list()
        for i, task in enumerate(tasks):
            logger.info(f"{i}: {task}")

    async def install_portal(self, portal_apk: str):
        logger.info(f"Installing {portal_apk}...")
        device_manager = DeviceManager()
        device = await device_manager.get_device(self.device)
        await device.install_app(portal_apk, reinstall=True)
        logger.info("Portal installed successfully")

    async def run(
        self,
        # droidrun params
        llm_provider: str,
        llm_model: str,
        reasoning: bool = True,
        reflection: bool = False,
        temperature: float = 0.5,
        tracing: bool = False,
        debug: bool = False,
        # suite params
        n_task_combinations: int = 1,
        seed: int = 42,
        task_family: str = "android_world",
        max_steps_multiplier: int = 15,
        timeout_multiplier: int = 300,
        # task params
        min_task_idx: int = 0,
        max_task_idx: int = -1,
        tasks: list[str] = [],
    ):
        self.env.reset(go_home=True)
        logger.info(
            f"Reinitializing suite {task_family} with {n_task_combinations} combinations and seed {seed}"
        )
        self.env.reinitialize_suite(
            n_task_combinations=n_task_combinations, seed=seed, task_family=task_family
        )
        logger.debug("Suite reinitialized successfully")

        logger.debug("Fetching task list...")
        if len(tasks) > 0:
            all_tasks = self.env.get_suite_task_list()
            task_list = [task for task in tasks if task in all_tasks]
        else:
            task_list = self.env.get_suite_task_list(min_task_idx, max_task_idx)
        logger.info(f"Found {len(task_list)} tasks")
        logger.debug("Loading LLM...")
        llm = load_llm(llm_provider, model=llm_model, temperature=temperature)
        logger.debug("LLM loaded successfully")

        logger.debug("Initializing droidrun portal keepalive...")
        keepalive = OverlayKeepalive(device_serial=self.device)
        logger.debug("Droidrun portal keepalive initialized")

        for task_name in task_list:
            num_tasks = self.env.get_suite_task_length(task_name)

            for task_idx in range(num_tasks):
                self.env.reset(go_home=True)
                task_goal = self.env.get_task_goal(task_name, task_idx)
                task_complexity = self.env.get_task_complexity(task_name, task_idx)

                max_steps = math.ceil(task_complexity * max_steps_multiplier)
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
                    continue

                try:
                    logger.debug("Enabling accessibility service...")
                    await enable_accessibility_service(
                        device_serial=self.device,
                        disable_first=True,
                    )
                    logger.debug("Accessibility service enabled")
                    logger.debug("Starting droidrun portal keepalive...")
                    keepalive.start()
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
                    continue

                logger.info(
                    f"Initializing DroidAgent with {max_steps} steps and {timeout} timeout"
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
                    logger.warn(
                        f"Droidrun timed out for task {task_name} {task_idx}: {e}"
                    )
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
                    write_task_result(
                        task_result, agent, error=repr(e), device=self.device
                    )
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
                    keepalive.stop()
                except Exception as e:
                    logger.error(f"Error tearing down task {task_name} {task_idx}: {e}")
                    logger.info("Continuing to next task...")
                    keepalive.stop()
                    send_discord_exception(
                        e,
                        "couldn't tear down task",
                        task_name,
                        task_idx,
                        task_goal,
                        self.device,
                    )
                    continue


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Run AndroidWorld benchmark tasks with DroidRun",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Benchmark environment configuration
    env_group = parser.add_argument_group("Benchmark Environment Configuration")
    env_group.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:5000",
        help="Base URL for the Android environment",
    )
    env_group.add_argument(
        "--device",
        type=str,
        default="emulator-5554",
        help="Device serial to use for adb tools",
    )
    env_group.add_argument(
        "--portal-path",
        type=str,
        default=os.path.join(os.getcwd(), "droidrun-portal.apk"),
        help="Path to the droidrun portal APK file",
    )

    # Task selection arguments
    task_group = parser.add_argument_group("Task Selection")
    task_group.add_argument(
        "--min-task-idx", type=int, default=0, help="Minimum task index to run"
    )
    task_group.add_argument(
        "--max-task-idx",
        type=int,
        default=-1,
        help="Maximum task index to run (last task idx + 1)",
    )
    task_group.add_argument(
        "--tasks",
        type=str,
        nargs="+",
        help="Tasks to run",
    )
    task_group.add_argument(
        "--list-tasks", action="store_true", help="List available tasks and exit"
    )
    task_group.add_argument(
        "--n-task-combinations",
        type=int,
        default=1,
        help="Number of parameter combinations per task",
    )

    # LLM configuration
    droidrun_group = parser.add_argument_group("Droidrun Configuration")
    droidrun_group.add_argument(
        "--llm-provider",
        type=str,
        default="Gemini",
        help="LLM provider (OpenAI, Anthropic, Gemini, etc.)",
    )
    droidrun_group.add_argument(
        "--llm-model",
        type=str,
        default="models/gemini-2.5-pro",
        help="Model name to use",
    )
    droidrun_group.add_argument(
        "--temperature", type=float, default=0.2, help="Temperature for LLM sampling"
    )
    droidrun_group.add_argument(
        "--reasoning", action="store_true", help="Enable reasoning for LLM"
    )
    droidrun_group.add_argument(
        "--reflection",
        action="store_true",
        help="Enable reflection for Droidrun",
    )
    droidrun_group.add_argument(
        "--tracing",
        action="store_true",
        help="Enable tracing for Droidrun",
    )
    droidrun_group.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for Droidrun",
    )

    # Benchmark configuration
    suite_group = parser.add_argument_group("Benchmark Suite Configuration")
    suite_group.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    suite_group.add_argument(
        "--task-family",
        type=str,
        default="android_world",
        help="Task family to run",
    )
    suite_group.add_argument(
        "--max-step-multiplier",
        type=int,
        default=15,
        help="Used to calculate max steps (complexity * max_step_multiplier)",
    )
    suite_group.add_argument(
        "--timeout-multiplier",
        type=int,
        default=300,
        help="Used to calculate timeout (complexity * timeout_multiplier)",
    )

    args = parser.parse_args()

    # Create benchmark instance
    benchmark = AndroidWorldBenchmark(
        base_url=args.base_url,
        device=args.device,
    )
    benchmark.wait_for_env()

    # ensure device is connected
    device_manager = DeviceManager()
    device_parts = args.device.split(":")
    device_host = device_parts[0]
    device_port = device_parts[1] if len(device_parts) > 1 else 5555
    asyncio.run(device_manager.connect(device_host, device_port))
    logger.info(f"Connected to device {args.device}")
    asyncio.run(benchmark.install_portal(args.portal_path))

    # Just list tasks if requested
    if args.list_tasks:
        benchmark.list_tasks()
        return

    logger.info(
        textwrap.dedent(
            """

  ██████╗ ██████╗  ██████╗ ██╗██████╗ ██████╗ ██╗   ██╗███╗   ██╗
  ██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗██╔══██╗██║   ██║████╗  ██║
  ██║  ██║██████╔╝██║   ██║██║██║  ██║██████╔╝██║   ██║██╔██╗ ██║
  ██║  ██║██╔══██╗██║   ██║██║██║  ██║██╔══██╗██║   ██║██║╚██╗██║
  ██████╔╝██║  ██║╚██████╔╝██║██████╔╝██║  ██║╚██████╔╝██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ Android World Benchmark
"""
        )
    )

    # Run the benchmark
    asyncio.run(
        benchmark.run(
            # droidrun params
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            reasoning=args.reasoning,
            reflection=args.reflection,
            temperature=args.temperature,
            tracing=args.tracing,
            debug=args.debug,
            # suite params
            n_task_combinations=args.n_task_combinations,
            seed=args.seed,
            task_family=args.task_family,
            max_steps_multiplier=args.max_step_multiplier,
            timeout_multiplier=args.timeout_multiplier,
            # task params
            min_task_idx=args.min_task_idx,
            max_task_idx=args.max_task_idx,
            tasks=args.tasks,
        )
    )


if __name__ == "__main__":
    main()
