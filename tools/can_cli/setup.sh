#!/bin/bash
# Setup script for CAN CLI tool

set -e

echo "Setting up OpenPilot CAN CLI tool..."

# Make scripts executable
chmod +x can_cli.py
chmod +x test_can_cli.py
chmod +x examples.py

# Create config directory
CONFIG_DIR="$HOME/.openpilot/can_cli"
mkdir -p "$CONFIG_DIR/logs"
mkdir -p "$CONFIG_DIR/templates"

# Create default config if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "default_mode": "production",
  "rate_limits": {
    "global": 100,
    "per_address": 20,
    "window_size": 1.0
  },
  "critical_addresses": {
    "0x180": "STEERING",
    "0x200": "BRAKE", 
    "0x220": "THROTTLE",
    "0x2E4": "TRANSMISSION",
    "0x191": "CRUISE_CONTROL",
    "0x1D2": "PCM_CRUISE",
    "0x1FA": "CRUISE_BUTTONS"
  },
  "safety": {
    "require_confirmation_for_critical": true,
    "log_all_operations": true,
    "allow_custom_safety_modes": false
  }
}
EOF
    echo "Created default config at $CONFIG_DIR/config.json"
fi

# Create convenience symlink
if [ -w "/usr/local/bin" ]; then
    ln -sf "$(pwd)/can_cli.py" /usr/local/bin/openpilot-can-cli
    echo "Created symlink: openpilot-can-cli"
else
    echo "Cannot create symlink in /usr/local/bin (no write permission)"
    echo "You can run the tool directly with: $(pwd)/can_cli.py"
fi

# Run tests
echo -e "\nRunning safety tests..."
python3 test_can_cli.py -v

echo -e "\n✅ Setup complete!"
echo -e "\nUsage:"
echo "  ./can_cli.py --help"
echo "  ./examples.py         # See usage examples"
echo -e "\nSafety reminder:"
echo "  - Default mode is PRODUCTION (high safety)"
echo "  - Always test on bench before vehicle"
echo "  - Read the README.md for safety guidelines"