#! /usr/bin/env python3
from labcontrol import Experiment, StepperI2C, Keithley6514Electrometer, Keithley2000Multimeter, Plug, PDUOutlet, ArduCamMultiCamera, SingleGPIO


camera = ArduCamMultiCamera("Camera", 1)


socket_path = "/tmp/uv4l.socket"

refPointsSingle = {
    "SingleOpen": 0,
    "LineSlit": 660,
    "LittleHole": 2*660,
    "BigHole": 3*660,
    # Blank
    "A02": 3*660 + 975,
    "A04": 4*660 + 975,
    "A08": 5*660 + 975,
    "A16": 6*660 + 975,
    # Blank
    "VaryWidth": 6*660 + 2*975,
    # Blank
    "Square": 6*660 + 3*975 + 1050,
    "Hex": 7*660 + 3*975 + 1050,
    "Dots": 8*660 + 3*975 + 1050,
    "Holes": 9*660 + 3*975 + 1050,

refPointsMulti = {
    "TwoOne": 0,
    "FarClose": 0,
    "WideThin": 0,
    "ThreeTwo": 0,
    # Blank
    "A04D25": 0,
    "A04D50": 0,
    "A08D25": 0,
    "A08D50": 0,
    # Blank
    "VarySpacing": 0,
    # Blank
    "TwoSlit": 0,
    "ThreeSlit": 0,
    "FourSlit": 0,
    "FiveSlit": 0,
}

#this uses the broadcom pin numbering system
screen = SingleGPIO("Screen", 26)
ambient = SingleGPIO("Ambient", 5)

multiSlits = StepperI2C("MultiSlits", 1, bounds=(-20000,20000), style="DOUBLE", refPoints=refPointsMulti)  #Multiple Slits
singleSlits = StepperI2C("SingleSlits", 2,bounds=(-20000,20000), style="DOUBLE", refPoints=refPointsSingle) #Single Slits
stage = StepperI2C("Stage", 4, bounds=(-20000, 200000), style="DOUBLE") #Screen



ASDIpdu = PDUOutlet("ASDIpdu", "asdipdu.inst.physics.ucsb.edu", "admin", "5tgb567ujnb", 60, outlets=[1])
ASDIpdu.login()



exp = Experiment("DiffractionInterference")
exp.add_device(camera)
exp.add_device(ASDIpdu)
exp.add_device(multiSlits)
exp.add_device(singleSlits)
exp.add_device(stage)
exp.add_device(ambient)
exp.add_device(screen)
exp.set_socket_path(socket_path)
exp.recallState()
exp.setup()
        
    