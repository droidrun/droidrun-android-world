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

3. Install `ffmpeg`, if not already installed.

    ```bash
    # Linux (Ubuntu/Debian)
    # sudo apt update && sudo apt install ffmpeg

    # macOS
    brew install ffmpeg
    ```

4. **Prepare AndroidWorld and Droidrun**
   ```bash
   # clone repo
   git clone https://github.com/droidrun/droidrun-android-world && \
   cd droidrun-android-world

   # initialize submodules (android_world + droidrun)
   git submodule update --init

   # optionally create a virtual environment beforehand
   pip install .
   ```

5. **Launch the Android Emulator**
   ```bash
   # Typically located in ~/Android/Sdk/emulator/emulator or 
   # ~/Library/Android/sdk/emulator/emulator
   EMULATOR_NAME=AndroidWorldAvd
   ~/Library/Android/sdk/emulator/emulator -avd $EMULATOR_NAME -no-snapshot -grpc 8554
   ```

6. **Set Environment Variables**
   ```bash
   export GEMINI_API_KEY=your-key  # Or other provider keys
   ```

7. **Important: Start Android World Environment**
   ```bash
   cd android_world && python -m server.android_server
   ```
   This is going to start the android world suite controller server on port 5000. If you're on mac you'll need to change this port to e.g. 5001 in the android_server.py file.
   If you change the server port remember to specify it for every command via the ``--env-url`` option. (e.g. http://localhost:5001)

8. **Ensure the Android World Environment is Ready**
   ```bash
   droidrun-android-world check
   ```

<!--## Docker setup

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
```-->

## Usage

### Basic Usage

Run a specific task by index:

```bash
droidrun-android-world --min-task-idx 0 --max-task-idx 1
```

Run a specific task by name:

```bash
droidrun-android-world --task ContactsAddContact --task BrowserMultiply
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
If you encounter issues with UI interaction:
   - Verify the DroidRun Portal app is installed correctly 
   - Make sure both Droidrun Portal and Google Accessibility Forwarder are configured and enabled as accessiblity service

To diagnose run ``droidrun-android-world check``

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

