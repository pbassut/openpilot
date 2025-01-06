from opendbc.can.packer import CANPacker
from openpilot.selfdrive.car import apply_meas_steer_torque_limits
from openpilot.selfdrive.car.fiat import fiatcan
from openpilot.selfdrive.car.fiat.values import CarControllerParams
from openpilot.selfdrive.car.interfaces import CarControllerBase
from openpilot.common.numpy_fast import interp

DAS_BUS = 1

class CarController(CarControllerBase):
  def __init__(self, dbc_name, CP, VM):
    super().__init__(dbc_name, CP, VM)

    self.apply_steer_last = 0
    self.apply_brake = 0
    self.apply_gas = 0

    self.hud_count = 0
    self.last_lkas_falling_edge = 0

    self.packer = CANPacker(dbc_name)
    self.params = CarControllerParams(CP)

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators
    can_sends = []

    # longitudinal control
    if self.CP.openpilotLongitudinalControl:
      # Gas, brakes, and UI commands - all at 100Hz
      self.apply_gas = int(round(interp(actuators.accel)))
      self.apply_brake = int(round(interp(actuators.accel)))

      can_sends.append(fiatcan.create_gas_command(self.packer, DAS_BUS, self.apply_gas, CS.accel_counter + 1))
      can_sends.append(fiatcan.create_friction_brake_command(self.packer, DAS_BUS, self.apply_brake, CS.accel_counter + 1))

    # cruise buttons
    # ACC cancellation
    if CC.cruiseControl.cancel:
      can_sends.append(fiatcan.create_cruise_buttons(self.packer, CS.button_counter + 1, DAS_BUS, activate=False))

    # ACC resume from standstill
    elif CC.cruiseControl.resume:
      can_sends.append(fiatcan.create_cruise_buttons(self.packer, CS.button_counter + 1, DAS_BUS, activate=True))

    # steering
    if self.frame % self.params.STEER_STEP == 0:
      # steer torque
      new_steer = int(round(actuators.steer * self.params.STEER_MAX))
      apply_steer = apply_meas_steer_torque_limits(new_steer, self.apply_steer_last, CS.out.steeringTorqueEps, self.params)
      self.apply_steer_last = apply_steer

      can_sends.append(fiatcan.create_lkas_command(self.packer, self.frame, apply_steer, CC.enabled))

    self.frame += 1

    new_actuators = actuators.as_builder()
    new_actuators.steer = self.apply_steer_last / self.params.STEER_MAX
    new_actuators.steerOutputCan = self.apply_steer_last
    new_actuators.gas = self.apply_gas
    new_actuators.brake = self.apply_brake

    return new_actuators, can_sends
