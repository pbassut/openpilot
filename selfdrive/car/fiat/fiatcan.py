def create_lkas_command(packer, frame, apply_steer, enabled):
  values = {
    "STEERING_TORQUE": apply_steer,
    "LKAS_WATCH_STATUS": enabled,
    "COUNTER": frame,
  }
  return packer.make_can_msg("LKAS_COMMAND", 0, values)

def create_lkas_hud_command(packer):
  values = {
    "SOMETHING_HANDS_ON_WHEEL_2": 0,
    "SOMETHING_HANDS_ON_WHEEL": 0,
    "HANDS_ON_WHEEL_WARNING": 1,
    "LANE_HUD_INDICATOR": 6,
    "LKAS_FAULT_TYPE": 0,
  }
  return packer.make_can_msg("LKA_HUD_2", 0, values)

def create_cruise_buttons(packer, frame, bus, activate=False):
  button = 32 if activate else 128
  values = {
    "CRUISE_BUTTON_PRESSED": button,
    "COUNTER": frame,
  }
  return packer.make_can_msg("DAS_1", bus, values)

def create_gas_command(packer, bus, throttle, frame):
  values = { "ACCEL_PEDAL_THRESHOLD": throttle, "COUNTER": frame }
  return packer.make_can_msg("ENGINE_1", bus, values)

def create_friction_brake_command(packer, bus, apply_brake, frame):
  values = { "BRAKE_PRESSURE": apply_brake, "COUNTER": frame }
  return packer.make_can_msg("ABS_6", bus, values)

def create_acc_dashboard_command(packer, bus, enabled, target_speed_kph, hud_control, fcw):
  target_speed = min(target_speed_kph, 255)

  values = { "ACC_SET_SPEED": target_speed }

  return packer.make_can_msg("DAS_2", bus, values)
