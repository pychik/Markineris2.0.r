#!/bin/bash

# Enable WireGuard VPN
sudo wg-quick up wg0

cd Markineris2.0r/ || exit
# Perform system update
make service-up

# Disable WireGuard VPN
sudo wg-quick down wg0