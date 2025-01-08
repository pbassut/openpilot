import time
PT_BUS = 0

DAS_BUS = 1

def create_lkas_command(packer, frame, apply_steer, enabled):
  values = {
    "STEERING_TORQUE": apply_steer,
    "LKAS_WATCH_STATUS": enabled,
    "COUNTER": frame,
  }
  return packer.make_can_msg("LKAS_COMMAND", PT_BUS, values)

def create_lkas_hud_command(packer, lat_active, eps_faulted):
  seconds = int(time.time()) % 36
  print("seconds: ", seconds)

  values = {
    "SOMETHING_HANDS_ON_WHEEL_2": seconds % 2 == 0,
    "SOMETHING_HANDS_ON_WHEEL": seconds % 3 == 0,
    "HANDS_ON_WHEEL_WARNING": seconds % 7 == 0,
    "LKAS_FAULTED_3": seconds % 5 == 0,
    "LKAS_FAULTED_2": seconds % 11 == 0,
    "LANE_HUD_INDICATOR": 6 if lat_active else 1,
    "LKAS_STATUS": seconds % 13 == 0,
    "LKAS_FAULT_TYPE": 7 if eps_faulted else 0,
  }
  return packer.make_can_msg("LKA_HUD_2", PT_BUS, values)

def create_cruise_buttons(packer, frame, activate=False):
  button = 32 if activate else 128
  values = {
    "CRUISE_BUTTON_PRESSED": button,
    "COUNTER": frame,
  }
  return packer.make_can_msg("DAS_1", DAS_BUS, values)

def create_gas_command(packer, throttle, frame):
  values = { "ACCEL_PEDAL_THRESHOLD": throttle, "COUNTER": frame }
  return packer.make_can_msg("ENGINE_1", PT_BUS, values)

def create_friction_brake_command(packer, apply_brake, frame):
  values = { "BRAKE_PRESSURE": apply_brake, "COUNTER": frame }
  return packer.make_can_msg("ABS_6", PT_BUS, values)
