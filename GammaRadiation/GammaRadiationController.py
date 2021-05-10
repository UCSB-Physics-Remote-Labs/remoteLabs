#! /usr/bin/env python3
from labcontrol import Experiment, StepperI2C, PDUOutlet, ArduCamMultiCamera, DCMotorI2C, SingleGPIO, Multiplexer, AbsorberController, PWMChannel, PololuDCMotor, PololuStepperMotor
import visa
import argparse, os, json

parser = argparse.ArgumentParser(description="Used to select which mode to run in", prog="LabController")

parser.add_argument("-s", "--settings", required=True)
group = parser.add_mutually_exclusive_group()
group.add_argument("-r", "--reset", action="store_true")
group.add_argument("-a", "--admin", action="store_true")

args = parser.parse_args()

labSettingsPath = os.path.join("home","pi", "remoteLabs", "GammaRadiation", args.settings)

with open(labSettingsPath, "r") as f:
    labSettings = json.load(f)

# Raffi make these settings match what is needed in the settings file
outlets         = labSettings["outlets"]
outletMap       = labSettings["outletMap"]

stageBounds     = labSettings["stageBounds"]
stageRefPoints  = labSettings["stageRefPoints"]
stageStepPin, stageDirPin, stageEnPin   = labSettings['stagePins']
stageDelay      = labSettings["stageDelay"]

# magnetTerminal      = labSettings["magnetTerminal"]
magnetPin           = labSettings["magnetPin"]
magnetFrequency     = labSettings["magnetFrequency"]

actuatorPwmPin, actuatorDirPin, actuatorNotEnPin, actuatorStopPin   = labSettings["actuatorPins"]
actuatorTriggerEdge = labSettings["actuatorTriggerEdge"]
actuatorSteadyState = labSettings["actuatorSteadyState"]
actuatorPWMScaler   = labSettings["actuatorPWMScaler"]

initialState        = labeSettings["initialState"]
holderMap           = labSettings["holderMap"]

multiplexerPins     = labSettings["multiplexerPins"]
inhibitorPin        = labSettings["inhibitorPin"]
multiplexerChannels = labSettings["multiplexerChannels"]
multiplexerDelay    = labSettings["multiplexerDelay"]

absorberFullTime = labSettings["absorberFullTime"]
absorberMidTime  = labSettings["absorberMidTime"]
magnetPower      = labSettings["magnetPower"]


if args.admin:
    bounds = (-1e6, 1e6)
    stageBounds=bounds

camera = ArduCamMultiCamera("Camera", 1, i2cbus=1)

socket_path = "/tmp/uv4l.socket"
messenger_socket_path = "/tmp/remla.socket"


## stage = StepperI2C("Stage", stageTerminal, bounds=stageBounds, style="DOUBLE", delay=0.000004, refPoints=stageRefPoints)
stage = PololuStepperMotor("Stage", stageStepPin, stageDirPin, stageEnPin, bounds=stageBounds, delay=stageDelay, refPoints=stageRefPoints)
## actuator = DCMotorI2C("Actuator", actuatorTerminal)
actuator = PololuDCMotor("Actuator", actuatorPwmPin, actuatorDirPin, actuatorNotEnPin, actuatorStopPin, rising=actuatorTriggerEdge, pwmScaler=actuatorPWMScaler, steadyState=actuatorSteadyState)

## magnet = DCMotorI2C("Magnet", magnetTerminal)
magnet = PWMChannel("Magnet", magnetPin, magnetFrequency)

absorberController = AbsorberController("AbsorberController", stage, actuator, magnet, initialState, holderMap, fulltime=absorberFullTime, midtime=absorberMidTime, magnetPower=magnetPower)

buttons = Multiplexer("Buttons", multiplexerPins, inhibitorPin, multiplexerChannels, delay=multiplexerDelay)
# Need to talk to PCS about getting GRpdu Setup
GRpdu = PDUOutlet("GRpdu", "grpdu.inst.physics.ucsb.edu", "admin", "5tgb567ujnb", 60, outlets=outlets, outletMap=outletMap)
GRpdu.login()


#This code is to release the motors at the start. I don't know why the labcontroller version doesn't work.
# stage.device.release()

if args.reset:
    exp = Experiment("GammaRadiation", messenger=True)
elif args.admin:
    exp = Experiment("GammaRadiation", admin=True)
else:
    exp=Experiment("GammaRadiation")
exp.add_device(camera)
exp.add_device(stage)
exp.add_device(actuator)
exp.add_device(magnet)
exp.add_device(absorberController)
exp.add_device(buttons)
exp.add_device(GRpdu)


exp.set_socket_path(socket_path)
if not args.reset and not args.admin:
    exp.recallState()
exp.setup()
