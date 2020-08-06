#!/usr/bin/env python3
from labcontrol import Experiment, StepperI2C, Keithley6514Electrometer, Keithley2000Multimeter, Plug, PDUOutlet
import visa
import pickle

#REPLACE-outlets
#REPLACE-outletMap
#REPLACE-electrometer_address
#REPLACE-multimeter_address
#REPLACE-refPoints
#REPLACE-potBounds
#REPLACE-filterBounds

#ADMIN-bounds = (-1e6, 1e6)
#ADMIN-potBounds=bounds
#ADMIN-filterBounds=bounds


resource_manager = visa.ResourceManager("@py")
visa_electrometer = resource_manager.open_resource('ASRL/dev/ttyUSB'+ str(electrometer_address) +'::INSTR', baud_rate=19200)
visa_electrometer.read_termination = "\r\n"
visa_electrometer.write_termination = "\r\n"

visa_multimeter = resource_manager.open_resource('ASRL/dev/ttyUSB'+ str(multimeter_address) + '::INSTR', baud_rate=19200) #not sure if USB# is unique 2004234
visa_multimeter.read_termination = "\r\n"
visa_multimeter.write_termination = "\r\n"

socket_path = "/tmp/uv4l.socket"

potentiometer = StepperI2C("Pot", 2, bounds=potBounds)
filterWheel = StepperI2C("Wheel", 1, bounds=filterBounds, refPoints=refPoints)

PEpdu = PDUOutlet("PEpdu", "128.111.18.80", "admin", "5tgb567ujnb", 60, outlets=outlets, outletMap=outletMap)
PEpdu.login()

electrometer = Keithley6514Electrometer("Electrometer", visa_electrometer)

multimeter = Keithley2000Multimeter("Multimeter", visa_multimeter)


#RECALL-exp = Experiment("PhotoElectricEffect")
#RESET-exp = Experiment("PhotoElectricEffect")
#ADMIN-exp = Experiment("PhotoElectricEffect", admin=True)
exp.add_device(PEpdu)
exp.add_device(potentiometer)
exp.add_device(filterWheel)
exp.add_device(electrometer)
exp.add_device(multimeter)
exp.set_socket_path(socket_path)
#RECALL-exp.recallState()
exp.setup()