ARG ELK_VERSION

FROM logstash:${ELK_VERSION}

HEALTHCHECK --interval=240s --timeout=120s --retries=5 \
  CMD curl -s -XGET 'http://127.0.0.1:9600'
