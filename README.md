# DroidRun Evaluation with AndroidWorld

This module provides tools for benchmarking DroidRun using the [AndroidWorld](https://github.com/droidrun/android_world) ([upstream](https://github.com/google-research/android_world)) task suite - a collection of 116 diverse tasks across 20 Android applications.

---

## 1. Manual Environment Setup

Reference: [android_world official documentation](https://github.com/google-research/android_world/tree/main#installation).

### 1.1 Install Android Emulator

- Download [Android Studio](https://developer.android.com/studio)  
- Create an Android Virtual Device (AVD):
  - Hardware: **Pixel 6**  
  - System Image: **Tiramisu, API Level 33**  
  - AVD Name: **AndroidWorldAvd**  
- [Setup video tutorial](https://github.com/google-research/android_world/assets/162379927/efc33980-8b36-44be-bb2b-a92d4c334a50)

### 1.2 Launch Android Emulator

Launch the emulator **from command line** (not Android Studio UI) with the `-grpc 8554` flag, which is required for accessibility forwarding.

```bash
# Emulator path is usually located at:
# ~/Android/Sdk/emulator/emulator
# ~/Library/Android/sdk/emulator/emulator

EMULATOR_NAME=AndroidWorldAvd
~/Library/Android/sdk/emulator/emulator -avd $EMULATOR_NAME -no-snapshot -grpc 8554
```

---

## 2. Clone and Install

### 2.1 Clone repository and initialize submodules
```bash
git clone https://github.com/droidrun/droidrun-android-world && \
cd droidrun-android-world

# initialize submodules (android_world + droidrun)
git submodule update --init
```

### 2.2 Install dependencies
```bash
# install dependencies using uv
uv sync
# build cli
uv build
```

---

## 3. Configuration

### 3.1 Set API Key
```bash
export GEMINI_API_KEY=your-key  # Or other provider keys
```

### 3.2 Start AndroidWorld Environment
Must be executed in `droidrun-android-world/android_world` directory, and keep running:
```bash
cd android_world
python -m server.android_server
```

### 3.3 Common Issues

1. **adb not found**  
   Locate adb path:
   ```bash
   which adb
   ```
   Then update `adb_path` in `android_server.py`:
   ```python
   adb_path="/opt/android/platform-tools/adb"
   ```

---

## 4. Running Tasks

### 4.1 Verify Environment
Run in another terminal (keep `server.android_server` running):
```bash
droidworld check
```

### 4.2 Run a Task
Execute from `droidrun-android-world` directory:
```bash
# Example: add contact task
droidworld run --tasks ContactsAddContact
```

---

## 5. Summary

- **Android Emulator** must be launched via command line and kept running  
- **server.android_server** must be kept alive in background  
- Run tasks only under `droidrun-android-world` directory  


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
droidworld run --min-task-idx 0 --max-task-idx 1
```

Run a specific task by name:

```bash
droidworld run --task ContactsAddContact
```

### List Available Tasks

View all available tasks with their IDs:

```bash
droidworld list-tasks
```

### Customizing the Benchmark

```bash
# Run with a different LLM provider and model
droidworld run --llm-provider Anthropic --llm-model claude-3-sonnet-20240229

# Set maximum steps per task: multiplier * task complexity
droidworld run --max-step-multiplier 15

# Run multiple parameter combinations per task
droidworld run --n-task-combinations 3

# Check all available configuration options with
droidworld run --help
```

<!--## Results

Benchmark results are saved in the specified results directory (default: `eval_results/`). For each task run, the following files are generated:

1. **Individual task result files**: `TIMESTAMP_TASKNAME.json` with detailed information about each task run
2. **Summary file**: `summary.json` with aggregated results across all tasks

After completion, a summary is printed to the console showing:
- Total tasks run
- Success rate
- Average steps per task
- Average execution time-->

## Accessibility Service Notes

The benchmark script automatically manages the DroidRun accessibility service, which is required for proper interaction with Android UI elements:
If you encounter issues with UI interaction:
   - Verify the DroidRun Portal app is installed correctly 
   - Make sure both Droidrun Portal and Google Accessibility Forwarder are configured and enabled as accessiblity service

To diagnose run ``droidworld check``
