# print start of docker-compose.yaml
echo """networks:
  benchmark:

services:
"""

# print emulators
android_env_list=() 
for i in {1..10}; do
	android_env_list+=("android-world-env-$i:5555")

echo """
  android-world-env-$i:
    image: europe-west3-docker.pkg.dev/bonny-android-use-staging/droidrun/android-world:latest
    container_name: android-world-env-$i
    privileged: true
    networks:
      - benchmark
  droidrun-benchmark-$i:
    image: europe-west3-docker.pkg.dev/bonny-android-use-staging/droidrun/droidrun-android-world:latest
    container_name: droidrun-benchmark-$i
    networks:
      - benchmark
    volumes:
      - ./eval_results:/opt/shared/eval_results
    env_file:
      - .env
    command: --base-url http://android-world-env-$i:5000 --device android-world-env-$i:5555 --llm-provider Gemini --llm-model models/gemini-2.5-pro --debug --reasoning --min-task-idx 80 --max-task-idx 117 --timeout-multiplier 1000
    depends_on:
      - android-world-env-$i"""
done

# print ws-scrcpy service into docker-compose.yaml
echo """
  ws-scrcpy:
    image: europe-west3-docker.pkg.dev/bonny-android-use-staging/droidrun/ws-scrcpy:latest
    container_name: ws-scrcpy
    networks:
      - benchmark
    environment:
      - ADB_DEVICES=$(IFS=,; echo "${android_env_list[*]}")
    ports:
      - 8000:8080
"""
