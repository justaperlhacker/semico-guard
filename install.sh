#!/usr/bin/env bash
# install semico-guard (root service) + systemd unit.
# Run: sudo ./install.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this as root, e.g.:" >&2
  echo "  sudo ./install.sh" >&2
  exit 1
fi

install -m 0755 "$(dirname "$0")/semico-guard.py" /usr/local/sbin/semico-guard
install -m 0644 "$(dirname "$0")/systemd/semico-guard.service" /etc/systemd/system/semico-guard.service
systemctl daemon-reload
systemctl enable --now semico-guard.service

echo
echo "Installed. Status:"
systemctl --no-pager --lines=3 status semico-guard
echo
echo "Live wedge/wreckage log:"
echo "  journalctl -u semico-guard -f"