#! /usr/bin/env python3
from labcontrol import Experiment, StepperI2C, Plug, PDUOutlet, ArduCamMultiCamera, ElectronicScreen


camera = ArduCamMultiCamera("Camera", 1)

socket_path = "/tmp/uv4l.socket"

refPoints = {
    "h2":0,
    "a":6572,
    "b": int(2*6572),
    }

bound = int(1e6)
slit = StepperI2C("Slit", 1,bounds=(-bound,bound), style="DOUBLE", delay=0.1)  
grating = StepperI2C("Grating", 2, bounds=(-bound, bound), style="DOUBLE")
arm = StepperI2C("Arm", 3,bounds=(-bound, bound), style="DOUBLE")
carousel = StepperI2C("Carousel", 4,bounds=(-bound, bound), style="MICROSTEP", delay=0.00002, refPoints=refPoints)

ambient = SingleGPIO("Ambient", 29)


ASDIpdu = PDUOutlet("ASDIpdu", "asdipdu.inst.physics.ucsb.edu", "admin", "5tgb567ujnb", 60, outlets=[6])
ASDIpdu.login()


exp = Experiment("AtomicSpectra", admin=True)
exp.add_device(camera)
exp.add_device(ASDIpdu)
exp.add_device(grating)
exp.add_device(slit)
exp.add_device(arm)
exp.add_device(carousel)
exp.add_device(ambient)
exp.set_socket_path(socket_path)
exp.recallState()
exp.setup()
        
    