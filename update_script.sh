#!/bin/bash

# Enable WireGuard VPN
sudo wg-quick up wg0

# Perform system update
make service-up

# Disable WireGuard VPN
sudo wg-quick down wg0