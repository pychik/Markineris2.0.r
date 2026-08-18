#!/bin/sh
set -e

python3 - <<'PYEOF'
import os
with open('/tmp/ea-config.yaml') as f:
    c = f.read()
c = c.replace('__ES_USERNAME__', os.environ['ELASTIC_USERNAME'])
c = c.replace('__ES_PASSWORD__', os.environ['ELASTIC_PASSWORD'])
with open('/tmp/elastalert_config.yaml', 'w') as f:
    f.write(c)
PYEOF

elastalert-create-index --config /tmp/elastalert_config.yaml
elastalert --config /tmp/elastalert_config.yaml
