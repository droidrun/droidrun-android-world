import logging
from eval.env.client import AndroidEnvClient
from droidrun.portal import (
    download_portal_apk,
    enable_portal_accessibility,
    check_portal_accessibility,
    ping_portal,
    ping_portal_content,
    ping_portal_tcp,
    set_overlay_offset,
    setup_keyboard,
    A11Y_SERVICE_NAME as DROIDRUN_A11Y_SERVICE_NAME,
)
from async_adbutils import adb, AdbDevice
import time

logger = logging.getLogger(__name__)

GOOGLE_A11Y_SERVICE_NAME = "com.google.androidenv.accessibilityforwarder/com.google.androidenv.accessibilityforwarder.AccessibilityForwarder"
DROIDRUN_X_GOOGLE_A11Y_SERVICE_NAME = (
    f"{DROIDRUN_A11Y_SERVICE_NAME}:{GOOGLE_A11Y_SERVICE_NAME}"
)
DEFAULT_OVERLAY_OFFSET = -126

async def ensure_connected(serial: str) -> AdbDevice:
    try:
        # For emulator devices (emulator-*), they're already connected locally
        # Only try network connect for IP addresses
        if ":" in serial or not serial.startswith("emulator-"):
            res = adb.connect(serial)
            if res.count("failed") > 0 or res.count("unable") > 0:
                raise RuntimeError(f"Failed to connect: {res}")
        
        # Verify device is available
        device = await adb.device(serial)
        # Test if device is accessible
        await device.shell("echo test")
        return device
    except Exception as e:
        raise RuntimeError(f"Device {serial} is not connected: {e}")


async def install_portal(device: AdbDevice):
    logger.info("Installing portal...")

    try:
        with download_portal_apk() as apk_path:
            await device.install(apk_path, uninstall=True, flags=["-g"], silent=False)
            logger.info("Portal APK installed successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to download and install portal APK: {e}")

    try:
        logger.info("Enabling portal as accessibility service...")
        await enable_portal_accessibility(
            device, service_name=DROIDRUN_X_GOOGLE_A11Y_SERVICE_NAME
        )
        logger.info("Portal accessibility enabled successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to enable portal accessibility: {e}")

    try:
        logger.info("Setting up keyboard for environment...")
        await setup_keyboard(device)
        logger.info("Keyboard setup completed successfully!")
    except Exception as e:
        raise RuntimeError(f"Failed to setup keyboard: {e}")


async def check_portal(device: AdbDevice):
    if not await check_portal_accessibility(
        device, service_name=DROIDRUN_X_GOOGLE_A11Y_SERVICE_NAME
    ):
        raise RuntimeError("Accessibility settings invalid")
    
    try:
        await set_overlay_offset(device, DEFAULT_OVERLAY_OFFSET)
        logger.info("Overlay offset set successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to set overlay offset: {e}")

    try:
        await ping_portal(device)
    except Exception as e:
        raise RuntimeError(f"Failed to ping portal: {e}")

    try:
        await ping_portal_content(device)
    except Exception as e:
        raise RuntimeError(f"Failed to ping portal content: {e}")

    try:
        await ping_portal_tcp(device)
    except Exception as e:
        raise RuntimeError(f"Failed to ping portal TCP: {e}")

    logger.info("Portal is installed and accessible. You're good to go!")


def wait_ready(env: AndroidEnvClient, timeout: int = 300):
    """
    Wait for the environment to be ready (health check returns True).

    This is designed to be called from FastAPI BackgroundTasks, which handles
    threading automatically. No manual threading needed.

    Args:
        callback: Optional function to call when environment is ready
        timeout: Maximum time to wait in seconds (default: 5 minutes)
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if env.health():
                logger.info(f"Environment {env.base_url} is ready!")
                return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")

        time.sleep(2)  # Poll every 2 seconds

    raise RuntimeError(
        f"Environment {env.base_url} failed to become ready within {timeout} seconds"
    )


async def boot_environment(env: AndroidEnvClient, serial: str):
    try:
        logger.info(f"Waiting for environment {env.base_url} to be ready...")
        wait_ready(env, timeout=600)
        logger.info(f"Environment {env.base_url} is ready!")
    except Exception as e:
        logger.error(f"Environment {env.base_url} failed to boot: {e}")
        raise e

    try:
        device = await ensure_connected(serial)
    except Exception as e:
        logger.error(f"Environment {env.base_url} failed to connect via adb: {e}")
        raise e

    # check if portal is already installed
    try:
        logger.info(f"Checking portal for environment {env.base_url}...")
        await check_portal(device)
        logger.info("Portal is installed and accessible. You're good to go!")
        return
    except Exception as e:
        logger.info(
            f"Environment {env.base_url} failed to check portal: {e}. Trying to install and enable portal..."
        )

    try:
        logger.info(f"Installing portal for environment {env.base_url}...")
        await install_portal(device)
        logger.info(f"Portal installed successfully for environment {env.base_url}!")
    except Exception as e:
        logger.error(f"Environment {env.base_url} failed to install portal: {e}")
        raise e

    try:
        logger.info(f"Checking portal for environment {env.base_url}...")
        await check_portal(device)
        logger.info("Portal is installed and accessible. You're good to go!")
    except Exception as e:
        logger.error(f"Environment {env.base_url} failed to check portal: {e}")
        raise e
