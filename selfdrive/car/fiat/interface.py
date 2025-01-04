#!/usr/bin/env python3
from cereal import car
from openpilot.selfdrive.car.interfaces import CarInterfaceBase
from openpilot.selfdrive.car import create_button_events, get_safety_config

class CarInterface(CarInterfaceBase):
  def __init__(self, CP, CarController, CarState):
    super().__init__(CP, CarController, CarState)

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs):
    ret.carName = "fiat"

    ret.radarUnavailable = True
    ret.steerActuatorDelay = 0
    ret.steerLimitTimer = 0.4

    # safety config
    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.fiat)]

    CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    ret.centerToFront = ret.wheelbase * 0.44
    ret.enableBsm = False

    ret.experimentalLongitudinalAvailable = True
    ret.pcmCruise = not experimental_long
    ret.openpilotLongitudinalControl = experimental_long

    # Tuning for experimental long
    ret.longitudinalTuning.kiV = [2.0, 1.5]
    ret.stoppingDecelRate = 2.0  # reach brake quickly after enabling
    ret.vEgoStopping = 0.25
    ret.vEgoStarting = 0.25

    return ret
