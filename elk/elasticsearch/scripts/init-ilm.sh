#!/bin/sh
set -eu

echo "Starting ILM setup at $(date)"

ELASTIC_URL="https://elasticsearch:${ELASTICSEARCH_PORT}"
AUTH_HEADER="${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}"
TODAY="$(date +%Y.%m.%d)"

NGINX_ROLLOVER_MAX_AGE="${NGINX_ROLLOVER_MAX_AGE:-7d}"
NGINX_ROLLOVER_MAX_SIZE="${NGINX_ROLLOVER_MAX_SIZE:-5gb}"
NGINX_DELETE_MIN_AGE="${NGINX_DELETE_MIN_AGE:-30d}"

FLASK_ROLLOVER_MAX_AGE="${FLASK_ROLLOVER_MAX_AGE:-7d}"
FLASK_ROLLOVER_MAX_SIZE="${FLASK_ROLLOVER_MAX_SIZE:-2gb}"
FLASK_DELETE_MIN_AGE="${FLASK_DELETE_MIN_AGE:-30d}"

MONITORING_ROLLOVER_MAX_AGE="${MONITORING_ROLLOVER_MAX_AGE:-3d}"
MONITORING_ROLLOVER_MAX_SIZE="${MONITORING_ROLLOVER_MAX_SIZE:-2gb}"
MONITORING_DELETE_MIN_AGE="${MONITORING_DELETE_MIN_AGE:-14d}"

put_json() {
  endpoint="$1"
  body="$2"
  curl -u "$AUTH_HEADER" -k -sS -o /dev/null -w "%{http_code}" \
    -X PUT "${ELASTIC_URL}/${endpoint}" \
    -H 'Content-Type: application/json' \
    -d "$body"
}

apply_ilm_policy() {
  policy_name="$1"
  rollover_age="$2"
  rollover_size="$3"
  delete_age="$4"

  body="$(cat <<EOF
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "${rollover_age}",
            "max_size": "${rollover_size}"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "delete": {
        "min_age": "${delete_age}",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
EOF
)"

  code="$(put_json "_ilm/policy/${policy_name}" "$body")"
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "ILM policy ${policy_name}: ok"
  else
    echo "ILM policy ${policy_name}: failed (HTTP ${code})"
  fi
}

apply_logs_template() {
  template_name="$1"
  index_pattern="$2"
  ilm_policy="$3"
  rollover_alias="$4"

  body="$(cat <<EOF
{
  "index_patterns": ["${index_pattern}"],
  "priority": 250,
  "template": {
    "settings": {
      "index.number_of_shards": 1,
      "index.number_of_replicas": 0,
      "index.refresh_interval": "30s",
      "index.lifecycle.name": "${ilm_policy}",
      "index.lifecycle.rollover_alias": "${rollover_alias}"
    },
    "mappings": {
      "dynamic": true,
      "properties": {
        "@timestamp": { "type": "date" },
        "message": { "type": "match_only_text" },
        "tags": { "type": "keyword" },
        "log": {
          "properties": {
            "file": {
              "properties": {
                "path": { "type": "keyword" }
              }
            }
          }
        },
        "host": {
          "properties": {
            "name": { "type": "keyword" }
          }
        },
        "http": {
          "properties": {
            "response": {
              "properties": {
                "status_code": { "type": "integer" }
              }
            }
          }
        }
      }
    }
  }
}
EOF
)"

  code="$(put_json "_index_template/${template_name}" "$body")"
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "Index template ${template_name}: ok"
  else
    echo "Index template ${template_name}: failed (HTTP ${code})"
  fi
}

ensure_initial_write_index() {
  rollover_alias="$1"
  index_prefix="$2"

  alias_status="$(curl -u "$AUTH_HEADER" -k -sS -o /dev/null -w "%{http_code}" "${ELASTIC_URL}/_alias/${rollover_alias}")"
  if [ "$alias_status" = "200" ]; then
    echo "Alias ${rollover_alias}: already exists"
    return
  fi

  initial_index="${index_prefix}-${TODAY}-000001"
  body="$(cat <<EOF
{
  "aliases": {
    "${rollover_alias}": {
      "is_write_index": true
    }
  }
}
EOF
)"

  code="$(put_json "${initial_index}" "$body")"
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "Initial index ${initial_index}: created"
  else
    echo "Initial index ${initial_index}: failed (HTTP ${code})"
  fi
}

apply_monitoring_policy_and_template() {
  policy_body="$(cat <<EOF
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "${MONITORING_ROLLOVER_MAX_AGE}",
            "max_size": "${MONITORING_ROLLOVER_MAX_SIZE}"
          }
        }
      },
      "delete": {
        "min_age": "${MONITORING_DELETE_MIN_AGE}",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
EOF
)"

  code_policy="$(put_json "_ilm/policy/monitoring_policy" "$policy_body")"
  if [ "$code_policy" = "200" ] || [ "$code_policy" = "201" ]; then
    echo "ILM policy monitoring_policy: ok"
  else
    echo "ILM policy monitoring_policy: failed (HTTP ${code_policy})"
  fi

  template_body="$(cat <<EOF
{
  "index_patterns": [".monitoring-*"],
  "priority": 100,
  "template": {
    "settings": {
      "index.number_of_shards": 1,
      "index.number_of_replicas": 0,
      "index.lifecycle.name": "monitoring_policy"
    }
  }
}
EOF
)"

  code_template="$(put_json "_index_template/monitoring_template" "$template_body")"
  if [ "$code_template" = "200" ] || [ "$code_template" = "201" ]; then
    echo "Index template monitoring_template: ok"
  else
    echo "Index template monitoring_template: failed (HTTP ${code_template})"
  fi
}

apply_ilm_policy "nginx_logs_policy" "$NGINX_ROLLOVER_MAX_AGE" "$NGINX_ROLLOVER_MAX_SIZE" "$NGINX_DELETE_MIN_AGE"
apply_ilm_policy "flask_app_logs_policy" "$FLASK_ROLLOVER_MAX_AGE" "$FLASK_ROLLOVER_MAX_SIZE" "$FLASK_DELETE_MIN_AGE"

apply_logs_template "nginx_template" "nginx-*" "nginx_logs_policy" "nginx"
apply_logs_template "flask_app_template" "flask-app-*" "flask_app_logs_policy" "flask-app"

ensure_initial_write_index "nginx" "nginx"
ensure_initial_write_index "flask-app" "flask-app"

apply_monitoring_policy_and_template

echo "ILM setup completed at $(date)"
exit 0