FROM python:3.12-slim

WORKDIR /opt/shared

RUN apt-get update && \
    apt-get install -y curl adb

# install droidrun-android-world cli
COPY . .
RUN --mount=type=cache,target=/root/.cache/pip pip install .

VOLUME ["/opt/shared/eval_results"]

ENTRYPOINT ["droidrun-android-world"]
