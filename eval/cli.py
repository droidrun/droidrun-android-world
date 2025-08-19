import click
import logging
import asyncio
import functools

from eval.env.client import AndroidEnvClient
from eval.runner import run_task_on_env
from eval.tracker import write_task_result
from droidrun import load_llm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("android_world_bench")
logger.level = logging.DEBUG
logging.getLogger("droidrun").level = logging.DEBUG
logging.getLogger("android_world_tools").level = logging.DEBUG


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--env-url",
    default="http://localhost:5000",
    help="Android World Environment URL to use.",
)
def list_tasks(env_url):
    env = AndroidEnvClient(env_url)
    logger.info("Listing tasks...")
    tasks = env.get_suite_task_list()
    for i, task in enumerate(tasks):
        logger.info(f"{i}: {task}")


@cli.command()
@click.option(
    "--env-url",
    default="http://localhost:5000",
    help="Android World Environment URL to use.",
)
@click.option("--env-serial", default="emulator-5554", help="Device serial to use.")
@click.option("--task-family", default="android_world", help="Task family to use.")
@click.option("--seed", default=42, help="Seed to use.")
@click.option("--min-task-idx", "-min", default=0, help="Min task index.")
@click.option("--max-task-idx", "-max", default=-1, help="Max task index.")
@click.option("--task", "-t", multiple=True, help="Tasks to run.")
@click.option(
    "--n-task-combinations", "-n", default=1, help="Number of task combinations."
)
@click.option("--llm-provider", default="Gemini", help="LLM provider to use.")
@click.option("--llm-model", default="gemini-2.5-pro", help="LLM model to use.")
@click.option("--vision", is_flag=True, help="Enable vision.")
@click.option("--reasoning", is_flag=True, help="Enable reasoning.")
@click.option("--reflection", is_flag=True, help="Enable reflection.")
@click.option("--debug", is_flag=True, help="Enable debug mode.")
@click.option("--temperature", default=0.5, help="Temperature to use.")
@click.option("--tracing", is_flag=True, help="Enable tracing.")
@click.option("--max-steps-multiplier", default=15, help="Max steps multiplier.")
@click.option("--timeout-multiplier", default=300, help="Timeout multiplier.")
@make_sync
async def run(
    env_url,
    env_serial,
    task_family,
    seed,
    min_task_idx,
    max_task_idx,
    task,
    n_task_combinations,
    llm_provider,
    llm_model,
    vision,
    reasoning,
    reflection,
    debug,
    temperature,
    tracing,
    max_steps_multiplier,
    timeout_multiplier,
):
    env = AndroidEnvClient(env_url)

    async def wait_for_env():
        logger.debug("Waiting for environment to be healthy...")
        while True:
            if not env.health():
                print("Environment is not healthy, waiting for 1 second...")
                await asyncio.sleep(1)
            else:
                break
        logger.debug("Environment is healthy")

    await wait_for_env()

    logger.debug("Resetting environment...")
    env.reset(go_home=True)
    logger.info(
        f"Reinitializing suite {task_family} with {n_task_combinations} combinations and seed {seed}"
    )
    env.reinitialize_suite(
        n_task_combinations=n_task_combinations, seed=seed, task_family=task_family
    )
    logger.debug("Suite reinitialized successfully")

    logger.debug("Fetching task list...")
    if len(task) > 0:
        all_tasks = env.get_suite_task_list()
        task_list = [task for task in task if task in all_tasks]
    else:
        task_list = env.get_suite_task_list(min_task_idx, max_task_idx)
        logger.debug(f"Task list: {task_list}")

    logger.info(f"Found tasks: {', '.join(task_list)} ({len(task_list)})")

    logger.debug(f"Loading LLM: {llm_provider} {llm_model} {temperature}")
    llm = load_llm(llm_provider, model=llm_model, temperature=temperature)
    logger.debug("LLM loaded successfully")

    for task_name in task_list:
        num_tasks = env.get_suite_task_length(task_name)

        for task_idx in range(num_tasks):
            logger.info(f"Running task {task_name} {task_idx}...")
            res, e = await run_task_on_env(
                env,
                env_serial,
                llm,
                task_name,
                task_idx,
                max_steps_multiplier,
                timeout_multiplier,
                vision,
                reasoning,
                reflection,
                tracing,
                debug,
            )
            if e:
                logger.error(f"Error running task {task_name} {task_idx}: {e}")
            else:
                logger.info(f"Task {task_name} {task_idx} completed successfully")

            write_task_result(res)


if __name__ == "__main__":
    cli()
