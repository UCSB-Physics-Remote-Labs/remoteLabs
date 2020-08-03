#! /usr/bin/env python3
from labcontrol import Experiment, StepperI2C, Keithley6514Electrometer, Keithley2000Multimeter, Plug, PDUOutlet, ArduCamMultiCamera, SingleGPIO


camera = ArduCamMultiCamera("Camera", 1)


socket_path = "/tmp/uv4l.socket"

SSstep = 670
Mstep = 975
Lstep = 1050
VariableLength=1725

refPointsSingle = {
    "SingleOpen": 0,
    "LineSlit": Sstep,
    "LittleHole": 2*Sstep+50,
    "BigHole": 3*Sstep+50,
    # Blank
    "A02": 3*Sstep + Mstep,
    "A04": 4*Sstep + Mstep,
    "A08": 5*Sstep + Mstep,
    "A16": 6*Sstep + Mstep,
    # Blank
    "VaryWidth": 6*Sstep + 2*Mstep,
    # Blank
    "Square": 6*Sstep + 2*Mstep + Lstep + VariableLength,
    "Hex": 7*Sstep + 2*Mstep + Lstep + VariableLength,
    "Dots": 8*Sstep + 2*Mstep + Lstep + VariableLength,
    "Holes": 9*Sstep + 2*Mstep + Lstep + VariableLength,
}

mSstep = Sstep - 50
refPointsMulti = {
    "MultiOpen": 0,
    "FarClose": mSstep,
    "WideThin": 2*mSstep,
    "ThreeTwo": 3*mSstep,
    # Blank
    "TwoSlit": 3*mSstep + Mstep,
    "ThreeSlit": 4*mSstep + Mstep,
    "FourSlit": 5*mSstep + Mstep,
    "FiveSlit": 6*mSstep + Mstep,
    # Blank
    "A04D25": 6*mSstep + 2*Mstep,
    "A04D50": 7*mSstep + 2*Mstep,
    "A08D25": 8*mSstep + 2*Mstep,
    "A08D50": 9*mSstep + 2*Mstep,
    # Blank
    "VarySpacing": 10*mSstep + 3*Mstep
}

#this uses the broadcom pin numbering system
screen = SingleGPIO("Screen", 26)
ambient = SingleGPIO("Ambient", 5)

multiSlits = StepperI2C("MultiSlits", 1, bounds=(-12000,12000), style="DOUBLE", delay=0.00004, refPoints=refPointsMulti)  #Multiple Slits
singleSlits = StepperI2C("SingleSlits", 2,bounds=(-12000,12000), style="DOUBLE", delay=0.00004, refPoints=refPointsSingle) #Single Slits
stage = StepperI2C("Stage", 4, bounds=(-(39*250), 0), style="DOUBLE", delay=0.004) #Screen



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
        
    