#!/bin/sh
set -e

echo "Starting ILM setup at $(date)"

# Создание политики ILM для nginx
echo "Applying ILM policy for nginx..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_ilm/policy/nginx_logs_policy" -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "30d",
            "max_size": "50gb"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "delete": {
        "min_age": "60d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}' && echo "Nginx ILM policy applied successfully" || echo "Nginx ILM policy already exists or failed"

# Создание политики ILM для flask-app
echo "Applying ILM policy for flask-app..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_ilm/policy/flask_app_logs_policy" -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "30d",
            "max_size": "50gb"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "delete": {
        "min_age": "60d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}' && echo "Flask-app ILM policy applied successfully" || echo "Flask-app ILM policy already exists or failed"

# Создание шаблона индекса для nginx
echo "Applying index template for nginx..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_index_template/nginx_template" -H 'Content-Type: application/json' -d '{
  "index_patterns": ["nginx-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.lifecycle.name": "nginx_logs_policy",
      "index.lifecycle.rollover_alias": "nginx"
    }
  }
}' && echo "Nginx index template applied successfully" || echo "Nginx index template already exists or failed"

# Создание шаблона индекса для flask-app
echo "Applying index template for flask-app..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_index_template/flask_app_template" -H 'Content-Type: application/json' -d '{
  "index_patterns": ["flask-app-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.lifecycle.name": "flask_app_logs_policy",
      "index.lifecycle.rollover_alias": "flask-app"
    }
  }
}' && echo "Flask-app index template applied successfully" || echo "Flask-app index template already exists or failed"

# Создание начального индекса для nginx
echo "Creating initial index for nginx..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/nginx-2025.04.14-000001" -H 'Content-Type: application/json' -d '{
  "aliases": {
    "nginx": {
      "is_write_index": true
    }
  }
}' && echo "Nginx initial index created successfully" || echo "Nginx initial index already exists or failed"

# Создание начального индекса для flask-app
echo "Creating initial index for flask-app..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/flask-app-2025.04.14-000001" -H 'Content-Type: application/json' -d '{
  "aliases": {
    "flask-app": {
      "is_write_index": true
    }
  }
}' && echo "Flask-app initial index created successfully" || echo "Flask-app initial index already exists or failed"

# Создание политики ILM для мониторинга
echo "Applying ILM policy for monitoring..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_ilm/policy/monitoring_policy" -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "7d",
            "max_size": "10gb"
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}' && echo "Monitoring ILM policy applied successfully" || echo "Monitoring ILM policy already exists or failed"

# Создание шаблона для мониторинга
echo "Applying index template for monitoring..."
curl -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}" -k -X PUT "https://elasticsearch:${ELASTICSEARCH_PORT}/_index_template/monitoring_template" -H 'Content-Type: application/json' -d '{
  "index_patterns": [".monitoring-*"],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.lifecycle.name": "monitoring_policy"
    }
  }
}' && echo "Monitoring index template applied successfully" || echo "Monitoring index template failed"

echo "ILM setup completed at $(date)"
exit 0
