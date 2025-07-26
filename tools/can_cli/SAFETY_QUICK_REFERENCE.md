# CAN CLI Safety Quick Reference

## 🚨 CRITICAL SAFETY RULES

1. **NEVER use on a moving vehicle**
2. **ALWAYS test on bench first**
3. **START with LOCKED mode to monitor**
4. **USE PRODUCTION mode by default**

## Safety Modes

| Mode | Send | Critical Addresses | Use Case |
|------|------|-------------------|----------|
| LOCKED | ❌ | N/A | Learning, monitoring only |
| PRODUCTION | ✅ | ❌ Blocked | Normal operations |
| TESTING | ✅ | ⚠️ Some allowed | Development testing |
| DEVELOPMENT | ✅ | ⚠️ All allowed* | Bench testing only |

*Still requires confirmation

## Critical CAN IDs (Never send without understanding)

| ID | System | Risk |
|----|--------|------|
| 0x180 | Steering | Loss of control |
| 0x200 | Brake | Brake failure |
| 0x220 | Throttle | Unintended acceleration |
| 0x2E4 | Transmission | Gear damage |
| 0x191 | Cruise Control | Speed control loss |

## Safe Testing Sequence

1. **Monitor First**
   ```bash
   ./can_cli.py monitor --timeout 60
   ```

2. **Test Non-Critical**
   ```bash
   ./can_cli.py send 0x7DF "02 01 00"  # OBD query
   ```

3. **Use DBC When Possible**
   ```bash
   ./can_cli.py send-dbc toyota "MSG_NAME" "SIGNAL=value"
   ```

4. **Gradual Testing**
   - Start with diagnostic messages (0x7xx)
   - Move to status queries
   - Only then consider control messages

## Emergency Procedures

### If Something Goes Wrong:

1. **Immediate**: Power off CAN interface
2. **Check**: Vehicle systems for errors
3. **Log**: Save `/var/log/can_cli/` for debugging
4. **Reset**: Clear DTCs if needed

### Rate Limit Hit:
- Reduce frequency
- Check for loops
- Use batch delays

### Unknown Response:
- Stop sending
- Monitor bus
- Research protocol

## Best Practices

✅ **DO:**
- Read vehicle's service manual
- Understand each message
- Keep detailed logs
- Have kill switch ready
- Work with partner watching

❌ **DON'T:**
- Send random messages
- Bypass confirmations  
- Test while driving
- Ignore warnings
- Share dangerous commands

## Common Safe Messages

```bash
# OBD-II Diagnostics (generally safe)
0x7DF - Broadcast diagnostic
0x7E8 - ECU response

# Information requests (read-only)
0x7DF "02 01 00" - Supported PIDs
0x7DF "02 01 0C" - Engine RPM
0x7DF "02 01 0D" - Vehicle speed
```

## Getting Help

1. Check: `./can_cli.py --help`
2. Examples: `./examples.py`
3. Logs: `~/.openpilot/can_cli/logs/`
4. Community: comma.ai Discord #dev

**Remember: When in doubt, DON'T SEND**