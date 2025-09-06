FROM python:3.11-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1

WORKDIR /opt/shared

RUN apt-get update && \
    apt-get install -y --no-install-recommends adb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# copy project into container
COPY . .
RUN uv sync --locked

VOLUME ["/opt/shared/eval_results"]

ENTRYPOINT ["uv", "run", "droidworld"]
