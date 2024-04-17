# Exit on Error
set -e

echo "Setting bootstrap.password..."
(echo "$ELASTIC_PASSWORD" | elasticsearch-keystore add -x 'bootstrap.password')
