# DroidRun Evaluation with AndroidWorld

This module provides tools for benchmarking DroidRun using the [AndroidWorld](https://github.com/droidrun/android_world) ([upstream](https://github.com/google-research/android_world)) task suite - a collection of 116 diverse tasks across 20 Android applications.

## Local Setup

### Prerequisites

1. **Python Version Requirements**
   - **Python 3.12** is required
   - Python 3.13 is currently not supported due to compatibility issues with pandas

2. **Android Emulator**
   - Download [Android Studio](https://developer.android.com/studio)
   - Create an Android Virtual Device (AVD):
     - Hardware: **Pixel 6**
     - System Image: **Tiramisu, API Level 33**
     - AVD name: **AndroidWorldAvd**

3. **Prepare AndroidWorld and Droidrun**
   ```bash
   # clone repo
   git clone https://github.com/droidrun/droidrun-android-world && \
   cd droidrun-android-world

   # initialize submodules (android_world + droidrun)
   git submodule update --init

   # optionally create a virtual environment beforehand
   pip install .
   ```

4. **Launch the Android Emulator**
   ```bash
   # Typically located in ~/Android/Sdk/emulator/emulator or 
   # ~/Library/Android/sdk/emulator/emulator
   EMULATOR_NAME=AndroidWorldAvd
   ~/Library/Android/sdk/emulator/emulator -avd $EMULATOR_NAME -no-snapshot -grpc 8554
   ```

5. **Install DroidRun Portal App**
   - The DroidRun Portal app must be installed on your Android device or emulator
   - This app provides the accessibility service required for DroidRun to interact with the UI
   - Download and install the APK:
     ```bash
     # Install the portal app using ADB
     adb install -r /path/to/droidrun-portal.apk
     ```
   - The app package name should be `com.droidrun.portal` with service name `com.droidrun.portal.DroidrunPortalService`


6. **Set Environment Variables**
   ```bash
   export OPENAI_API_KEY=your-key  # Or other provider keys
   ```

7. **Important: Start Android World Environment**
   ```bash
   cd android_world && python -m server.android_server
   ```

## Docker setup

### Prerequisites

1. **KVM Kernel module**

To run the Android emulator with hardware acceleration in Docker, you must enable KVM (Kernel-based Virtual Machine) on your Linux host.

**Setup steps:**

- **Install KVM and related packages:**
  ```bash
  sudo apt update
  sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils
  ```

- **Add your user to the `kvm` and `libvirt` groups:**
  ```bash
  sudo usermod -aG kvm $USER
  sudo usermod -aG libvirt $USER
  # Log out and log back in for group changes to take effect
  ```

- **Verify KVM installation:**
  ```bash
  kvm-ok  # On Ubuntu, from cpu-checker package
  # or
  lsmod | grep kvm
  ```

- **Check that your CPU supports virtualization:**
  ```bash
  egrep -c '(vmx|svm)' /proc/cpuinfo
  # Output should be 1 or more
  ```

- **Ensure `/dev/kvm` exists:**
  ```bash
  ls -l /dev/kvm
  # Should show a character device file
  ```

If you encounter issues, ensure virtualization is enabled in your BIOS/UEFI settings.

For more details, see the [KVM documentation](https://www.linux-kvm.org/page/Main_Page).

2. **Create an alias for easy of use**
```bash
alias droidrun-android-world='docker run --rm -it --name droidrun-android-world \
   --platform linux/amd64 --device /dev/kvm \
   -v ./eval_results:/opt/shared/eval_results \
   ${OPENAI_API_KEY:+-e OPENAI_API_KEY} \
   ${GEMINI_API_KEY:+-e GEMINI_API_KEY} \
   ${ANTHROPIC_API_KEY:+-e ANTHROPIC_API_KEY} \
   droidrun/droidrun-android-world:latest "$@"
'
```

## Usage

### Basic Usage

Run a specific task by index:

```bash
droidrun-android-world --min-task-idx 0 --max-task-idx 1
```

Run a specific task by name:

```bash
droidrun-android-world --tasks ContactsAddContact
```

### List Available Tasks

View all available tasks with their IDs:

```bash
droidrun-android-world --list-tasks
```

### Customizing the Benchmark

```bash
# Run with a different LLM provider and model
droidrun-android-world --llm-provider Anthropic --llm-model claude-3-sonnet-20240229

# Set maximum steps per task: multiplier * task complexity
droidrun-android-world --max-step-multiplier 15

# Run multiple parameter combinations per task
droidrun-android-world --n-task-combinations 3
```

## Results

Benchmark results are saved in the specified results directory (default: `eval_results/`). For each task run, the following files are generated:

1. **Individual task result files**: `TIMESTAMP_TASKNAME.json` with detailed information about each task run
2. **Summary file**: `summary.json` with aggregated results across all tasks

After completion, a summary is printed to the console showing:
- Total tasks run
- Success rate
- Average steps per task
- Average execution time

## Accessibility Service Notes

The benchmark script automatically manages the DroidRun accessibility service, which is required for proper interaction with Android UI elements:

1. Before each task, the script will:
   - Disable all existing accessibility services
   - Enable the DroidRun Portal accessibility service
   - Enable accessibility globally
   - Disable any overlay/box rendering if available

2. If you encounter issues with UI interaction:
   - Verify the DroidRun Portal app is installed correctly
   - Check the accessibility service name matches what's in your Portal app
   - Use the `--portal-service` option to provide the correct service name if needed

## Adding to Your Project

This evaluation module is designed as an add-on to the DroidRun framework, not a core dependency. To include it in your project:

1. Copy the `eval` directory to your DroidRun installation
2. Follow the setup instructions above
3. Run the benchmark as described

## Task Categories

AndroidWorld tasks span various applications and interaction types:

- **Contacts**: Add, edit, delete contacts
- **Clock**: Set alarms, use timer, stopwatch
- **Calculator**: Basic and scientific calculations
- **Messages**: Send SMS, share content
- **Settings**: Wi-Fi configuration, display settings
- **Calendar**: Create, edit events
- **Camera**: Take photos, record videos
- **Web Browsing**: Search, navigate websites
- **And more...**

Each task is designed to test agent capabilities across different UI interaction patterns and complexity levels. 

---


## Installation

1. Set up the Android Emulator
   1. Download Android Studio [here](https://developer.android.com/studio?gad_source=1&gclid=Cj0KCQjw3ZayBhDRARIsAPWzx8oLcadBD0vAq8xmUutaunLGSzhgEtLz4xVZ_SpV4G0xJazS7LxQkDsaAuveEALw_wcB&gclsrc=aw.ds)
   2. Create an Android Virtual Device (AVD) by following these instructions. For hardware select **Pixel 6**, for System Image select **Tiramisu, API Level 33**, and choose AVD name as **AndroidWorldAvd**. [Watch the setup video.](https://github.com/google-research/android_world/assets/162379927/efc33980-8b36-44be-bb2b-a92d4c334a50)

1. Launch the Android Emulator from the command line

    Launch the emulator from the command line, not using the Android Studio UI,
    with the `-grpc 8554` flag which is needed communication with accessibility
    forwarding app.

    ```bash
    # Typically it's located in ~/Android/Sdk/emulator/emulator or
    # ~/Library/Android/sdk/emulator/emulator
    EMULATOR_NAME=AndroidWorldAvd # From previous step
    ~/Library/Android/sdk/emulator/emulator -avd $EMULATOR_NAME -no-snapshot -grpc 8554
    ```

1. [Optional] It's recommended to use `conda`, which you can download [here](https://docs.anaconda.com/free/miniconda/miniconda-install/).

    ```
    conda create -n android_world python=3.11.8
    conda activate android_world
    ```

**check if neccessary**
1. Install AndroidWorld. *Note: Python 3.11 or above is required.*

    ```python
    git clone https://github.com/google-research/android_world.git
    cd ./android_world
    pip install -r requirements.txt
    python setup.py install
    ```

1. Add model provider APIs as environment variables.

    ```bash
    # Add to .bashrc.
    export OPENAI_API_KEY=your-key
    export GCP_API_KEY=your-key
    ```

1. Install `ffmpeg`, if not already installed.

    ```bash
    # Linux (Ubuntu/Debian)
    # sudo apt update && sudo apt install ffmpeg

    # macOS
    brew install ffmpeg
    ```

## Running

1. Launch the Android Emulator from the command line

    Launch the emulator from the command line, not using the Android Studio UI,
    with the `-grpc 8554` flag which is needed communication with accessibility
    forwarding app.

    ```bash
    # Typically it's located in ~/Android/Sdk/emulator/emulator or
    # ~/Library/Android/sdk/emulator/emulator
    EMULATOR_NAME=AndroidWorldAvd # From previous step
    ~/Library/Android/sdk/emulator/emulator -avd $EMULATOR_NAME -no-snapshot -grpc 8554
    ```

1. Start the Android World Server

    ```bash
    cd android_world && python -m server.android_server
    ```

1. Run the cli

    ```bash
    python -m eval.cli run --env-url http://localhost:5000 --task BrowserMultiply --reasoning --debug
    ```

## Issues:
- enable a11y service on every task is not working properly and causing the google a11y service to crash
- KeepOverlayDisabled not working (might not be executing)
- trajectory is not being safed
- task result has wrong task id