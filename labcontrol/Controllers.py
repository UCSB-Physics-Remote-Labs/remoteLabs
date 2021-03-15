import time
import tplink_smarthome as tp
import dlipower
import RPistepper as stp
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
import RPi.GPIO as gpio
import os
import subprocess
import busio
import board
from adafruit_bus_device.i2c_device import I2CDevice

gpio.setmode(gpio.BCM)

class BaseController(object):

    def cmd_handler(self, cmd, params):
        # Make the parser name, it should follow the naming convention <cmd>_parser. If there is no parser return None.
        parser = getattr(self, cmd+"_parser", None)

        # If parser exists, use it to parse the params.
        if parser is not None:
            params = parser(params)
        # If there is no parser print this statement for user.
        else:
            print("No Parser Found. Will just pass params to command.")

        # No get the command method. If there isn't a method, it should through an AttributeError.
        method = getattr(self, cmd)

        if callable(method):
            response = method(params)

        return response

    def cleanup(self):
        pass

    def reset(self):
        pass

    def getState(self):
        return self.state

    def setState(self, state):
        self.state = state



class PDUOutlet(dlipower.PowerSwitch, BaseController):
    def __init__(self, name, hostname, userid, password, timeout=None, outlets=[1,2,3,4,5,6,7,8], outletMap={}):
        # self, userid=None, password=None, hostname=None, timeout=None, cycletime=None, retries=None, use_https=False
        super().__init__(hostname=hostname, userid=userid, password=password, timeout=timeout)
        self.name = name
        self.device_type = "controller"
        self.experiment = None
        self.state = {1:"Off", 2:"Off", 3:"Off", 4:"Off", 5:"Off", 6:"Off", 7:"Off", 8:"Off" }
        self.outlets = outlets
        self.outletMap = outletMap

    def on(self, outletNumber):
        super().on(outletNumber)
        self.state[outletNumber] = "On"

    def off(self, outletNumber):
        super().off(outletNumber)
        self.state[outletNumber] = "Off"

    def on_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "on")
        try:
            outlet = int(params[0])
        except ValueError:
            outlet_name = params[0]
            if outlet_name not in self.outletMap:
                raise ArgumentError(outlet_name, self.outletMap, self.name, "On")
            outlet = self.outletMap[outlet_name]

        if outlet not in self.outlets:
            raise ArgumentError(self.name, "On", "Outlet "+ params[0], allowed="Outlets " + str(self.outlets))
        return outlet

    def off_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "off")
        try:
            outlet = int(params[0])
        except ValueError:
            outlet_name = params[0]
            if outlet_name not in self.outletMap:
                raise ArgumentError(outlet_name, self.outletMap, self.name, "Off")
            outlet = self.outletMap[outlet_name]

        if outlet not in self.outlets:
            raise ArgumentError(self.name, "Off", "Outlet "+ params[0], allowed="Outlets " + str(self.outlets))
        return outlet

    def reset(self):
        for outlet in self.outlets:
            self.off(outlet)


class Plug(tp.TPLinkSmartDevice, BaseController):
    def __init__(self, name, host, port=9999, timeout=10, connect=True):
        print(host, port, timeout, connect)
        super().__init__(host=host, port=port, connect=connect)
        self.name = name
        self.device_type = "controller"
        self.experiment = None
        self.state = {"relayState": "OFF"}

    def setRelay(self,newRelay):
        print(newRelay)
        if newRelay=="OFF":
            super().send({'system': {'set_relay_state': {'state': 0}}})
        elif newRelay=="ON":
            super().send({'system': {'set_relay_state': {'state': 1}}})
        self.state["relayState"] = newRelay

    def setRelay_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "setRelay")
        return params[0]

    def cleanup(self):
        super().close()

    def reset(self):
        super().send({'system': {'set_relay_state': {'state': 0}}})
        super().close()


class StepperSimple(stp.Motor, BaseController):

    def __init__(self, name, pins, delay=0.02, refPoints={}):
        super().__init__(pins, delay)
        self.name = name
        self.device_type = "controller"
        self.refPoints = refPoints
        self.currentPosition = 0
        self.experiment = None
        self.state = {"position": self.currentPosition}

    def move(self, steps):
        print(steps)
        super().move(steps)
        super().release()
        self.currentPosition+=steps
        self.state["position"] = self.currentPosition
        self.device.release()

    def move_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "move")
        return int(params[0])

    def goto(self, position):
        print(position)
        endPoint=self.refPoints[position]
        self.move(endPoint-self.currentPosition)

    def goto_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "goto")
        return params[0]

    def cleanup(self):
        super().cleanup()

    def reset(self):
        super().reset()


class DCMotorI2C(MotorKit, BaseController):

    def __init__(self, name, terminal):
        if terminal > 4:
            self.address=0x61
        else:
            self.address=0x60
        super().__init__(address=self.address)
        self.name = name
        self.device_type = "controller"
        self.experiment = None

        self.terminal_options = {1: super().motor1, 2: super().motor2, 3:super().motor3, 4:super().motor4,
            5: super().motor1, 6:super().motor2, 7:super().motor3, 8:super().motor4}
        self.device = self.terminal_options[terminal]
        self.currentPosition = 0
        self.state = {"position": self.currentPosition}

    def setup(self, style):
        pass

    def reset(self):
        pass

    def throttle(self, speed):
        self.device.throttle = speed

    def throttle_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "move")
        print("Throttle is set to: {0}".format(params[0]))
        return float(params[0])

# Initialise the first hat on the default address
# lowerBoard = MotorKit()
# Initialise the second hat on a different address
# upperBoard = MotorKit(address=0x61)

class StepperI2C(MotorKit, BaseController):

    def __init__(self, name, terminal, bounds, delay=0.02, refPoints={}, style="SINGLE", microsteps=8, limitSwitches=[], homeSwitch=None, degPerStep=1.8, gearRatio=1):
        if terminal > 2:
            self.address=0x61
        else:
            self.address=0x60
        super().__init__(address=self.address, steppers_microsteps=microsteps)
        self.name = name
        self.device_type = "controller"
        self.experiment = None

        self.terminal_options = {1: super().stepper1, 2: super().stepper2, 3:super().stepper1, 4:super().stepper2}
        self.refPoints = refPoints
        self.currentPosition = 0
        self.device = self.terminal_options[terminal]
        self.delay = delay
        self.lowerBound = bounds[0]
        self.upperBound = bounds[1]
        self.styles = {
            "SINGLE": stepper.SINGLE,
            "DOUBLE": stepper.DOUBLE,
            "MICROSTEP": stepper.MICROSTEP,
            "INTERLEAVE": stepper.INTERLEAVE
        }
        self.style = self.styles[style]

        self.state = {"position": self.currentPosition}
        self.limitSwitches = limitSwitches
        self.homeSwitch = homeSwitch
        self.homing = False
        self.degPerStep = degPerStep
        self.gearRatio = gearRatio
        self.device.release()

    def setup(self, style):
        pass

    def move(self, steps):
        print(steps)
        if steps >= 0:
            direction = stepper.BACKWARD
        else:
            direction = stepper.FORWARD
        if self.currentPosition+steps <self.lowerBound and steps < 0:
            steps = self.lowerBound-self.currentPosition
        elif self.currentPosition+steps >self.upperBound and steps > 0:
            steps = self.upperBound-self.currentPosition

        for i in range(abs(steps)):

            if len(self.limitSwitches) != 0:
                for switch in self.limitSwitches:
                    status = switch.getStatus(1)
                    if status == gpio.HIGH:
                        response = switch.switchAction(self, steps-i)
                        if response is None:
                            return "{0}/{1}/{2}".format(self.name, "position", "limit")
                        else:
                            return response

            if self.homing:
                homeStatus = self.homeSwitch.getStatus(1)
                if homeStatus == gpio.HIGH:
                    return True

            self.device.onestep(style=self.style, direction=direction)
            time.sleep(self.delay)

        self.currentPosition+=steps
        self.state["position"] = self.currentPosition
        self.device.release()
        if self.currentPosition == self.upperBound or self.currentPosition == self.lowerBound:
            return "{0}/{1}/{2}".format(self.name, "position", "limit")
        else:
            return "{0}/{1}/{2}".format(self.name, "position", self.currentPosition)

    def move_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "move")
        return int(params[0])

    def adminMove(self, steps):
        if steps >= 0:
            direction = stepper.BACKWARD
        else:
            direction = stepper.FORWARD
        if self.currentPosition+steps <self.lowerBound and steps < 0:
            steps = self.lowerBound-self.currentPosition
        elif self.currentPosition+steps >self.upperBound and steps > 0:
            steps = self.upperBound-self.currentPosition
        for i in range(abs(steps)):
            self.device.onestep(style=self.style, direction=direction)
            time.sleep(self.delay)
        self.currentPosition+=steps
        self.state["position"] = self.currentPosition
        self.device.release()

    def goto(self, position):
        print(position)
        endPoint=self.refPoints[position]
        self.move(endPoint-self.currentPosition)

    def goto_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "goto")
        return params[0]

    def degMove_parser(self, params):
        try:
            steps = float(params[0])
        except ValueError:
            raise ArgumentError(self.name, "degMove", params)
        return steps


    def degMove(self, deg):
        print("{0} degrees".format(deg))
        step = deg / self.degPerStep
        step = int(step * self.gearRatio)
        step = round(step)
        response = self.move(step)
        return response


    def homeMove(self, stepLimit=5000, additionalSteps=10):
        if self.currentPosition > 0:
            direction = -1
        elif self.currentPosition < 0:
            direction = 1
        else:
            return

        self.move(direction*stepLimit)
        self.move(direction*additionalSteps)


    def reset(self):
        if self.homeSwitch is not None:
            self.home(1)
        else:
            self.move(-self.currentPosition)
        # pass

    def home(self, params):
        if self.homeSwitch is not None:
            self.homing = True
            self.customHome(self)
            self.homing = False
        else:
            print("No homing switch is attached to this motor")

    def customHome(self, motor):
        pass

class AbsorberController(MotorKit, BaseController):

    def __init__(self, name, stepper, actuator, magnet, fulltime=10, midtime=1):
        self.name = name
        self.device_type = "controller"
        self.experiment = None
        self.fulltime = fulltime
        self.midtime = midtime
        self.stepper = stepper
        self.actuator = actuator
        self.magnet = magnet
        self.state = {
            "loaded": {
                "s0":False,
                "s1":False,
                "s2":False,
                "s3":False,
                "s4":False,
                "s5":False
            },

            "total": {
                "s0":'',
                "s1":'',
                "s2":'',
                "s3":'',
                "s4":'',
                "s5":'',
                "h0":'A1',
                "h1":'A2',
                "h2":'A3',
                "h3":'A4',
                "h4":'A5',
                "h5":'A6',
                "h6":'A7',
                "h7":'A8',
                "h8":'A9',
                "h9":'A10',
                "h10":'A11',
                "h11":'Source',
            }
        }

        self.holderMap = {
                "A1": "h0",
                "A2": "h1",
                "A3": "h2",
                "A4": "h3",
                "A5": "h4",
                "A6": "h5",
                "A7": "h6",
                "A8": "h7",
                "A9": "h8",
                "A10": "h9",
                "A11": "h10",
                "Source": "h11",
            }


    def setup(self, style):
        pass

    def reset(self):
        pass

    def __transfer(self, slot1, slot2):

        absorber = self.state["total"][slot1]
        # print(f"Transfer {absorber} from {slot1} --> {slot2}")
        if self.state['total'][slot2] != '':
            print(f'!!!!!!!!!!!WARNING:  Slot {slot2} already full with {self.state["total"][slot2]}')
            raise
        # global x
        # x += 1
        self.stepper.goto(slot1)
        self.actuator.throttle(-1.0)
        time.sleep(self.midtime)
        self.actuator.throttle(0)
        self.magnet.throttle(1.0)
        self.actuator.throttle(1.0)
        time.sleep(self.fulltime)
        self.actuator.throttle(0)
        self.stepper.goto(slot2)
        self.actuator.throttle(-1.0)
        time.sleep(self.fulltime)
        self.actuator.throttle(0)
        self.magnet.throttle(0)
        self.actuator.throttle(1.0)
        time.sleep(self.midtime)
        self.actuator.throttle(0)


        self.state["total"][slot1] = ''
        self.state["total"][slot2] = absorber
        if slot1 in self.state["loaded"]:
            self.state["loaded"][slot1] = False
        if slot2 in self.state["loaded"]:
            self.state["loaded"][slot2] = True

    def __getSlot(self, absorber):
        # print(f"GET SLOT: {absorber}")
        if absorber == '':
            return -1
        for holderSlot, ab in self.state["total"].items():
            if ab == absorber:
                return holderSlot

    def __getAbsorber(self, slot):
        return self.state["total"][slot]

    def __makeMovesList(self, newPositions):
        moveList = {
            "load": [],
            "unload": [],
            "internal": [],
            "chains": []
        }

        absorbers = [item[1] for item in newPositions if item[1] != '']
        for slot, ab in newPositions:
            # slot is one of the counter slots. We will loop through all slots in the coutner.
            # ab is the absorber we want to end up in slot.

            # Get the absorber that is currently in the slot
            currentAbsInSlot = self.__getAbsorber(slot)
            # Get the location of the current absorber
            currentAbsLocation = self.__getSlot(ab)
            # print(f"Absorber: {ab}  Location: {currentAbsLocation}")

            # Determine if the absorber is used later down the line
            absorberUsed = currentAbsInSlot in absorbers
            if ab == currentAbsInSlot:
                ## If the absorber is already in the correct slot there is nothing todo.
                continue

            elif ab == '' and self.state["loaded"][slot]:
                # If we want the slot to be empty, it is current loaded and the
                # loaded absorber is not used later, then unload it.
                if not absorberUsed:
                    moveList["unload"].append( (slot, self.holderMap[currentAbsInSlot]) )

            elif ab != '' and self.state["loaded"][slot]:
                # If we want the slot to be full and it is already full with a
                # different absorber.
                if not absorberUsed:
                    # If the currently loaded absorber is not needed, unload it.
                    # If it is used later, we will handle that one later in the loop
                    moveList["unload"].append( (slot, self.holderMap[currentAbsInSlot]) )
                if currentAbsLocation[0] == "s":
                    # If the absorbr we want is already in the counter
                    # add it to an internal movement
                    moveList["internal"].append( (currentAbsLocation, slot) )
                else:
                    # If it isn't already in the counter it must be in the holder
                    # so add it to the load movement list.
                    moveList["load"].append( (currentAbsLocation, slot) )

            elif ab != '' and not self.state["loaded"][slot]:
                # If we want to fill the slot and nothing is there already just move
                # if following the same rules above without an unload first.
                if currentAbsLocation[0] == "s":
                    moveList["internal"].append( (currentAbsLocation, slot) )
                else:
                    moveList["load"].append( (currentAbsLocation, slot) )

        ## Now we should identify chains.
        chains = self.__chainDetect(moveList["internal"])
        internalStarts = [ item[0] for item in moveList["internal"] ]
        for chain in chains:
            for move in chain:
                moveList["internal"].remove(move)

        moveList["chains"] = chains

        return moveList

    def __chainDetect(self, movements):
        chains = []
        checked = []
        internalStarts = [ item[0] for item in movements ]
        internalFinish = [ item[1] for item in movements ]
        intersection = [slot for slot in internalStarts if slot in internalFinish]

        for move in movements:
            temp = []
            if move[0] in checked:
                continue
            # checked.append(move[0])
            if move[0] in intersection and move[1] in intersection:
                start = move[0]
                checked.append(start)
                nextSlot = move[1]
                temp.append(move)
                while nextSlot != start:
                    i=0
                    for nextMove in movements:
                        if nextMove[0] == nextSlot:
                            checked.append(nextMove[0])
                            nextSlot = nextMove[1]
                            temp.append(nextMove)
                            i -= 1
                            break
                        # print(f"{nextMove} and {nextSlot}")
                    i += 1
                    if i > 0:
                        break
                if i <= 0:
                    chains.append(temp)
        # print(f"CHAINS: {chains}")
        return chains

    def __chaseInternal(self, internals, startingMove):
        moves = [startingMove]
        internalStarts = [item[0] for item in internals]
        # internalStartsTemp = internalStarts.copy()
        nextSlot = startingMove[1]
        while nextSlot in internalStarts:
            index = internalStarts.index(nextSlot)
            iMove = internals.pop(index)
            internalStarts.pop(index)
            moves.insert(0, iMove)
            nextSlot = iMove[1]
        return moves

    def __handleChains(self, chains, currentMoves):
        currentFinish = [item[1] for item in currentMoves]
        slots = ['s0', 's1', 's2', 's3', 's4', 's5']
        for chain in chains:
            move1 = chain.pop(0)
            ab = self.__getAbsorber(move1[0])
            home = self.holderMap[ab]
            # for slot in slots:
            #     if slot not in currentFinish:
            #         home = slot
            #         break
            # print(f"CHAIN HOME: ({move1[0]}, {home})")
            currentMoves.append( (move1[0], home) )
            chain.reverse()
            for move in chain:
                currentMoves.append(move)
                # print(f"CHAIN MOVE REVERSE: {move}")
            currentMoves.append( (home, move1[1]) )
            # print(f"CHAIN BACK: ({home}, {move1[1]})")
            currentFinish = [item[1] for item in currentMoves]
        return currentMoves

    def __handleInternal(self, internals):
        moves = []
        if len(internals) == 0:
            return moves

        internalGroups = []
        while len(internals) != 0:
            start = internals.pop(0)
            temp = self.__chaseInternal(internals, start)
            internalGroups.append(temp)

        for group in internalGroups:
            moves += group

        return moves

    def __buildGroups(self, moveList):
        unloads = moveList["unload"]
        loads = moveList["load"]
        internals = moveList["internal"]
        unloadStarts = [item[0] for item in unloads]
        UILGroups = []
        ILGroups = []
        LGroups = []
        UIGroups = []
        IGroups = []
        moves = []

        for load in loads:
            temp = self.__chaseInternal(internals, load)
            internalStarts = [item[0] for item in internals]

            if len(temp) == 1:
                LGroups.append(temp)

            else:
                nextSlot = temp[0][1]
                # print(f"Checking for conflict with unload. Slot {nextSlot}")
                if nextSlot in unloadStarts:
                    # print("Internal Movement Conflict with Following Unload")
                    index = unloadStarts.index(nextSlot)
                    uMove = unloads.pop(index)
                    unloadStarts.remove(uMove[0])
                    temp.insert(0, uMove)
                    UILGroups.append(temp)
                else:
                    ILGroups.append(temp)

        if len(internals) > 0:

            internalStarts = [item[0] for item in internals]
            internalFinish = [item[1] for item in internals]
            intersection = [item for item in internalFinish if item in internalStarts]
            starts = [internal for internal in internals if internal[1] in intersection]
            for start in starts:
                internals.remove(start)

            for startingI in starts:
                temp = self.__chaseInternal(internals, startingI)
                internalStarts = [item[0] for item in internals]
                nextSlot = temp[0][1]
                # print(f"Checking for conflict with unload. Slot {nextSlot}")
                if nextSlot in unloadStarts:
                    # print("Internal Movement Conflict with Following Unload")
                    index = unloadStarts.index(nextSlot)
                    uMove = unloads.pop(index)
                    unloadStarts.remove(uMove[0])
                    temp.insert(0, uMove)
                    UIGroups.append(temp)
                else:
                    IGroups.append(temp)


        for uil in UILGroups:
            uMove = [uil.pop(0)]
            lMove = [uil.pop(-1)]
            igroup = uil

            if len(unloads) > 0:
                uTemp = unloads.pop(0)
                igroup.append(uTemp)

            elif len(UIGroups) > 0:
                uiTemp = UIGroups.pop(0)
                uTempMove = uiTemp.pop(0)
                igroup.append(uTempMove)
                lMove = lMove + uiTemp

            if len(LGroups) > 0:
                lTemp = LGroups.pop(0)
                igroup.insert(0, lTemp[0])

            elif len(ILGroups) > 0:
                ilTemp = ILGroups.pop(0)
                lTempMove = ilTemp.pop(-1)
                igroup.insert(0,lTempMove)
                uMove = ilTemp + uMove

            # moves.append(uMove + igroup + lMove)
            moves += uMove + igroup + lMove

        for il in ILGroups:
            uMove = []
            lMove = [il.pop(-1)]
            igroup = il

            if len(unloads) > 0:
                uTemp = unloads.pop(0)
                igroup.append(uTemp)

            elif len(UIGroups) > 0:
                uiTemp = UIGroups.pop(0)
                uTempMove = uiTemp.pop(0)
                igroup.append(uTempMove)
                lMove = lMove + uiTemp

            # moves.append(igroup + lMove)
            moves += igroup + lMove

        for l in LGroups:
            uMove = []
            lMove = l
            igroup = []

            if len(unloads) > 0:
                uTemp = unloads.pop(0)
                igroup.append(uTemp)

            elif len(UIGroups) > 0:
                uiTemp = UIGroups.pop(0)
                uTempMove = uiTemp.pop(0)
                igroup.append(uTempMove)
                lMove = lMove + uiTemp

            # moves.append(igroup + lMove)
            moves += igroup + lMove

        while len(unloads) > 0 or len(UIGroups) > 0:

            if len(UIGroups) > 0:
                moves = UIGroups.pop(0) + moves
            elif len(unloads) > 0:
                print(unloads)
                moves.insert(0, unloads.pop(0))

        return moves

    def place(self, moveList):

        moves = []
        internalStarts = [ item[0] for item in moveList["internal"]]
        internalFinish = [ item[1] for item in moveList["internal"]]
        unloadStarts = [ item[0] for item in moveList["unload"]]

        # print("\r\n ### Pairing Checks")
        uMovesTemp = moveList["unload"].copy()
        lMovesTemp = moveList["load"].copy()
        for uMove in moveList["unload"]:
            # print(f"PAIRING CHECK: {uMove}, {moveList['unload']}, {moveList['load']},")
            for lMove in moveList["load"]:
                # print(f"PARING CHECK2: {lMove}")
                if uMove[0] == lMove[1]:
                    moves.append(uMove)
                    moves.append(lMove)
                    uMovesTemp.remove(uMove)
                    lMovesTemp.remove(lMove)
                    # print(f"PARING: {uMove} with {lMove}")

        moveList["unload"] = uMovesTemp
        moveList["load"] = lMovesTemp
        unloadStarts = [ item[0] for item in moveList["unload"]]

        # print("## Pairings Complete")
        pp.pprint(moveList)

        # print("## ORGANIZING EVERYTING BUT CHAINS")
        moves += self.__buildUILGroups(moveList)

        if len(moveList["chains"]) > 0:
            # print("## Handling Chains")
            moves = self. __handleChains(moveList["chains"], moves)

        pp.pprint(moveList)
        # print(moves)
        for move in moves:
            self.__transfer(move[0], move[1])

    # def place(self, absorberList):
    #     for slot, absorber in absorberList:
    #         # If the slot is not already load with the correct absorber & and it's empty
    #         if self.state["loaded"][slot] != absorber and self.state["loaded"][slot] == -1:
    #             # Get absorber from its current location
    #             # Move it to new location
    #             pass
    #         if self.state["loaded"][slot] != absorber and self.state["loaded"][slot] != -1:
    #             pass

    def place_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "place")
        # print("Throttle is set to: {0}".format(params[0]))
        temp = [item.replace("(","").replace(")","") for item in params]
        absorberList = []
        i = 0
        while i < len(temp):
            absorberList.append((temp[i], temp[i+1]))
            i += 2

        moveList = self.__makeMovesList(absorberList)

        return moveList

class Multiplexer(BaseController):

    def __init__(self, name, pins, inhibitorPin, channels=[0,1,2,3,4,5,6,7], defaultChannel=None, defaultState=gpio.HIGH, delay=0.1):
        self.state = {}
        self.name = name
        self.experiment = None
        self.device_type = "controller"
        self.delay = delay
        self.pins = pins
        self.channels = channels
        self.defaultState = defaultState
        self.defaultChannel = defaultChannel
        self.inhibitorPin = inhibitorPin

        gpio.setup(self.pins, gpio.OUT)
        gpio.setup(self.inhibitorPin, gpio.OUT)

        if self.defaultChannel is not None:
            self.__setChannel(self.defaultChannel)
            gpio.output(self.inhibitorPin, self.defaultState)
        else:
            gpio.output(self.inhibitorPin, gpio.HIGH)


    def __setChannel(self, channel):
        binary = "{0:0{1}b}".format(channel, len(self.pins))
        gpio.output(self.inhibitorPin, gpio.HIGH)
        for i in range(len(self.pins)):
            pin = self.pins[i]
            state = bool(int(binary[i]))
            pinstate = gpio.LOW
            if state:
                pinstate = gpio.HIGH

            gpio.output(pin, pinstate)

    def press(self, channel):
        self.__setChannel(channel)
        gpio.output(self.inhibitorPin, gpio.LOW)
        time.sleep(self.delay)
        gpio.output(self.inhibitorPin, gpio.HIGH)

    def press_parser(self, params):
        channel = int(params[0])
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "press")
        if channel not in self.channels:
            raise ArgumentError(self.name, "press", channel, self.channels)
        return channel


    def reset(self):
        if self.defaultChannel is not None:
            self.__setChannel(self.defaultChannel)
        gpio.output(self.inhibitorPin, self.defaultState)

class Keithley6514Electrometer(BaseController):

    def __init__(self, name, visa_resource):
        self.name = name
        self.device_type = "measurement"
        self.experiment = None
        self.state = {"setting": ""}

        self.inst = visa_resource

    def press(self, params):
        self.inst.write("SYST:REM")
        self.inst.write(params)
        if params != "SYST:KEY 1":
            self.inst.write("SYST:LOC")

    def press_parser(self, params):
        print(">>", params)
        return params[0]



class Keithley2000Multimeter(BaseController): #copied unaltered from Electrometer on 200423

    def __init__(self, name, visa_resource):
        self.name = name
        self.device_type = "measurement"
        self.experiment = None
        self.state = {"setting": ""}

        self.inst = visa_resource


    def press(self, params):
        self.inst.write("SYST:REM")
        self.inst.write(params)

    def press_parser(self, params):
        print(">>", params)
        return params[0]


class ArduCamMultiCamera(BaseController):

    def __init__(self, name, videoNumber=0, defaultSettings=None):
        self.name = name
        self.videoNumber = videoNumber
        self.device_type = "measurement"
        self.experiment = None
        self.state = {}
        self.defaultSettings = defaultSettings

        # Define Pins
        # Board Pin 7 = BCM Pin 4 = Selection
        # Board Pin 11 = BCM Pin 17 = Enable 1
        # Board Pin 12 = BCM Pin 18 = Enable 2
        # See Arducam User Guide https://www.uctronics.com/download/Amazon/B0120.pdf
        self.selection = 4
        self.enable1 = 17
        self.enable2 = 18
        self.channels = [self.selection, self.enable1, self.enable2]
        gpio.setup(self.channels, gpio.OUT)



        self.cameraDict = {
            "a": (gpio.LOW, gpio.LOW, gpio.HIGH),
            "b": (gpio.HIGH, gpio.LOW, gpio.HIGH),
            "c": (gpio.LOW, gpio.HIGH, gpio.LOW),
            "d": (gpio.HIGH, gpio.HIGH, gpio.LOW),
            "off":(gpio.LOW, gpio.HIGH, gpio.HIGH)
        }

        self.camerai2c = {
            'a': "i2cset -y 11 0x70 0x00 0x04",
            'b': "i2cset -y 11 0x70 0x00 0x05",
            'c': "i2cset -y 11 0x70 0x00 0x06",
            'd': "i2cset -y 11 0x70 0x00 0x07",
        }

        # Set camera for A
        self.camera("a")

    def camera(self, param):
        #Param should be a, b, c, d, or off
        print("Switching to camera "+param)
        os.system(self.camerai2c[param])
        gpio.output(self.channels, self.cameraDict[param])

    def camera_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "camera")
        param = params[0].lower()
        if param not in self.cameraDict:
            raise ArgumentError(self.name, "camera", param, ["a", 'b', 'c', 'd', 'off'])
        return params[0].lower()

    def imageMod(self, params):
        imageControl = params[0]
        controlValue = params[1]
        subprocess.run('v4l2-ctl -d /dev/video{0} -c {1}={2}'.format(self.videoNumber, imageControl, controlValue),
                    shell=True)

    def imageMod_parser(self, params):
        if len(params) != 2:
            raise ArgumentNumberError(len(params), 2, "imageMod")
        return params

    def reset(self):
        if self.defaultSettings is not None:
            for setting, value in self.defaultSettings.items():
                self.imageMod([setting,value])
                time.sleep(0.1)

class ElectronicScreen(BaseController):

    def __init__(self, name, pin):
        self.pin = pin
        self.name = name
        self.state = "off"
        gpio.setup(self.pin, gpio.OUT)

    def on(self, params):
        gpio.output(self.pin, gpio.HIGH)

    def off(self, params):
        gpio.output(self.pin, gpio.LOW)

    def reset(self):
        gpio.output(self.pin, gpio.LOW)



class LimitSwitch(BaseController):
    def __init__(self, name, pin, state=False):
        self.name = name
        self.pin = pin
        self.state = state
        gpio.setup(self.pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

    def getStatus(self, params):
        state = gpio.input(self.pin)
        self.state = state
        return state

    def switchAction(self, motor, steps):
        pass

class HomeSwitch(BaseController):
    def __init__(self, name, pin, state=False):
        self.name = name
        self.pin = pin
        self.state = state
        gpio.setup(self.pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

    def getStatus(self, params):
        state = gpio.input(self.pin)
        self.state = state
        return state


class SingleGPIO(BaseController):

    def __init__(self, name, pin, initialState=False):
        self.pin = pin
        self.name = name
        gpio.setup(self.pin, gpio.OUT)
        if initialState:
            self.state = "off"
            gpio.output(self.pin, gpio.HIGH)
        else:
            self.state = "off"
            gpio.output(self.pin, gpio.LOW)

    def on(self, params):
        gpio.output(self.pin, gpio.HIGH)

    def off(self, params):
        gpio.output(self.pin, gpio.LOW)

    def reset(self):
        gpio.output(self.pin, gpio.LOW)

class PushButton(BaseController):

    def __init__(self, name, pin, initialState=False, delay=0.1):
        self.pin = pin
        self.name = name
        self.delay = delay
        self.initialState = initialState
        gpio.setup(self.pin, gpio.OUT)
        if initialState:
            self.state = "on"
            gpio.output(self.pin, gpio.HIGH)
        else:
            self.state = "off"
            gpio.output(self.pin, gpio.LOW)

    def press(self, params):
        if self.initialState:
            gpio.output(self.pin, gpio.LOW)
            time.sleep(self.delay)
            gpio.output(self.pin, gpio.HIGH)
        else:
            gpio.output(self.pin, gpio.HIGH)
            time.sleep(self.delay)
            gpio.output(self.pin, gpio.LOW)


    def reset(self):
        gpio.output(self.pin, gpio.LOW)

class PWMChannel(BaseController):

    def __init__(self, name, pin, frequency, defaultDutyCycle=0 ):
        self.name = name
        self.device_type = "controller"
        self.pin = pin
        self.frequency = frequency
        self.defaultDutyCycle = defaultDutyCycle
        self.dutyCycle = defaultDutyCycle
        gpio.setup(self.pin, gpio.OUT)
        self.pwm = gpio.PWM(self.pin, self.frequency)
        self.pwm.start(self.dutyCycle)
        self.state = {}

    def power(self, dutyCycle):
        self.pwm.ChangeDutyCycle(dutyCycle)

    def power_parser(self, params):
        if len(params) != 1:
            raise ArgumentNumberError(len(params), 1, "power")
        dutyCycle = float(params[0])
        if dutyCycle < 0 or dutyCycle > 1:
            raise ArgumentError(self.name, "power", dutyCycle, allowed="0 <= dutyCycle <= 1")
        return dutyCycle

    def reset(self):
        self.pwm.ChangeDutyCycle(self.defaultDutyCycle)


class CommandError(Exception):

    def __init__(self, command, *args):
        self.command = command
        if args:
            self.message = args[0]
        else:
            self.message = "No command named '{0}' found".format(self.command)

    def __str__(self):
        return "CommandError, {0}".format(self.message)

class ArgumentNumberError(Exception):
    def __init__(self, total_args, allowed, command=None):
        self.total_args = total_args
        self.allowed = allowed
        self.command = command

    def __str__(self):
        if self.command is None:
            return "ArgumentNumberError, received {0} when {1} was expected.".format(self.total_args, self.allowed)
        else:
            return "ArgumentNumberError, command '{0}' received {1} when {2} was expected.".format(self.command,
             self.total_args, self.allowed)

class ArgumentError(Exception):
    def __init__(self, device_name, command, received, allowed=None):
        self.device_name = device_name
        self.command = command
        self.allowed = allowed
        self.received = received

    def __str__(self):
        if self.allowed is None:
            return "ArgumentError, Device, {0}, can't process command argument {1} by command {2}.".format(self.device_name, self.received, self.command)
        else:
            return "ArgumentError, Argument {0}, is not one of the allowed commands, {1}, for device, {2}, running command {3}.".format(self.received, self.allowed, self.device_name, self.command)
