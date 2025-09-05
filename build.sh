docker build -t droidrun/droidrun-android-world:latest --platform linux/amd64 "$@" .
docker build -t droidrun/ws-scrcpy:latest --platform linux/amd64 "$@" -f Dockerfile.ws-scrcpy .
docker build -t droidrun/android-world:latest --platform linux/amd64 "$@" ./android_world