ARG ELK_VERSION

FROM elasticsearch:${ELK_VERSION}

COPY scripts/docker-healthcheck .
HEALTHCHECK CMD sh ./docker-healthcheck
