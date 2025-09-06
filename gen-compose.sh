#!/bin/bash

# Function to display help message
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Generate a docker-compose.yaml file for Android World benchmark environment.

OPTIONS:
    -n, --n <number>    Number of emulator instances to generate (default: 1)
                        Must be a positive integer
    -h, --help          Show this help message and exit

EXAMPLES:
    $0                  # Generate with 1 emulator instance (default)
    $0 -n 5             # Generate with 5 emulator instances
    $0 --n 10           # Generate with 10 emulator instances

DESCRIPTION:
    This script generates a docker-compose.yaml configuration that includes:
    - Android World emulator environments
    - DroidRun benchmark containers
    - ws-scrcpy service for screen mirroring
    - Proper networking configuration

    Each emulator instance creates two containers:
    - android-world-env-<N>: The Android emulator environment
    - droidrun-benchmark-<N>: The benchmark execution container

EOF
}

# Parse command line arguments
n=1  # default value
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--n)
      n="$2"
      # Validate that n is an integer
      if ! [[ "$n" =~ ^[0-9]+$ ]] || [ "$n" -le 0 ]; then
        echo "Error: -n must be a positive integer" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Error: Unknown option '$1'" >&2
      echo "Use '$0 --help' for usage information." >&2
      exit 1
      ;;
  esac
done

# print start of docker-compose.yaml
echo """networks:
  benchmark:

services:"""

# print emulators
android_env_list=() 
for i in $(seq 1 $n); do
	android_env_list+=("android-world-env-$i:5555")

echo """
  android-world-env-$i:
    image: timoatdroidrun/android-world:latest
    container_name: android-world-env-$i
    privileged: true
    networks:
      - benchmark
    healthcheck:
      test: ["CMD", "adb", "shell", "getprop", "sys.boot_completed"]
      interval: 30s
      timeout: 10s
      start_period: 180s
      retries: 3
  droidrun-benchmark-$i:
    image: timoatdroidrun/droidrun-android-world:latest
    container_name: droidrun-benchmark-$i
    networks:
      - benchmark
    volumes:
      - ./eval_results:/opt/shared/eval_results
    env_file:
      - .env
    command: run --env-url http://android-world-env-$i:5000 --env-serial android-world-env-$i:5555 --llm-provider Gemini --llm-model models/gemini-2.5-pro --debug --reasoning --min-task-idx 80 --max-task-idx 117 --timeout-multiplier 1000
    depends_on:
      android-world-env-$i:
        condition: service_healthy"""
done

# print ws-scrcpy service into docker-compose.yaml
echo """
  ws-scrcpy:
    image: timoatdroidrun/ws-scrcpy:latest
    container_name: ws-scrcpy
    networks:
      - benchmark
    environment:
      - ADB_DEVICES=$(IFS=,; echo "${android_env_list[*]}")
    ports:
      - 8000:8080
    depends_on:"""
for i in $(seq 1 $n); do
	echo """      android-world-env-$i:
        condition: service_healthy"""
done