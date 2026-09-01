# The crew runs as a cluster workload, never on a person's machine. Everything it needs to find
# the estate arrives as environment and mounted secrets; the image carries no address and no key.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CREWAI_DISABLE_TELEMETRY=true

RUN groupadd --gid 10001 crew && useradd --uid 10001 --gid 10001 --create-home crew

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && mkdir -p /var/lib/infra-crew /laws \
    && chown -R crew:crew /var/lib/infra-crew /laws

USER crew
# INFRA_CREW_STORAGE_DIR is a volume; INFRA_CREW_LAWS_DIR is filled by an init step that checks
# out the law files. Both are set by the workload manifest, not here.
ENTRYPOINT ["infra-crew"]
