from droidrun.tools import AdbTools
from typing import Optional
from eval.android_env_client import AndroidEnvClient
from android_world.env import json_action
import logging

logger = logging.getLogger("android_world_tools")
logger.level = logging.DEBUG


class AndroidWorldTools(AdbTools):
    def __init__(self, serial: str, client: Optional[AndroidEnvClient] = None) -> None:
        logger.debug("Initializing AndroidWorldTools")
        super().__init__(serial, use_tcp=True)
        logger.debug("AdbTools initialized")
        self.client = client or AndroidEnvClient()
        logger.debug(f"AndroidWorldTools initialized with {self.client.base_url}")

    def complete(self, success: bool, reason: str = "") -> bool:
        """
        Mark the task as finished (copied from AdbTools).
        """
        if success:
            self.success = True
            self.reason = reason or "Task completed successfully."
            self.finished = True

            self.client.execute_action(
                json_action.JSONAction(action_type="answer", text=reason)
            )
            self.client.execute_action(
                json_action.JSONAction(action_type="status", goal_status="completed")
            )
        else:
            self.success = False
            self.client.execute_action(
                json_action.JSONAction(action_type="status", goal_status="failed")
            )
            if not reason:
                raise ValueError("Reason for failure is required if success is False.")
            self.reason = reason
            self.finished = True
        return self.finished
