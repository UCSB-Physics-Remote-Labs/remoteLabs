import socket
import sys
import os
import time
from signal import signal, SIGINT
import json
import logging
import threading
import asyncio
import websockets


class NoDeviceError(Exception):

    def __init__(self, device_name):
        self.device_name = device_name
    
    def __str__(self):
        return "NoDeviceError: This experiment doesn't have a device, '{0}'".format(self.device_name)

class Experiment(object):

    def __init__(self, name, root_directory="remoteLabs", admin=False, messenger=False):
        self.devices = {}
        self.allStates = {}
        if messenger:
            self.messenger = Messenger(self)
        else:
            self.messenger = None
        self.messenger_thread = None
        self.messenger_socket = None
        self.socket_path = ''
        self.socket = None
        self.connection = None
        self.client_address = None
        self.name = name
        self.initializedStates = False
        self.admin = admin
        self.directory = os.path.join("/home", "pi", root_directory, name)
        self.log_name = os.path.join(self.directory, self.name+".log")
        self.json_file = os.path.join(self.directory, self.name+".json")
        logging.basicConfig(filename=self.log_name, level=logging.INFO, format="%(levelname)s - %(asctime)s - %(filename)s - %(funcName)s \r\n %(message)s \r\n")
        logging.info("""
        ##############################################################
        ####                Starting New Log                      ####
        ##############################################################    
        """)

    def add_device(self, device):
        device.experiment = self
        logging.info("Adding Device - " + device.name)
        self.devices[device.name] = device

    def recallState(self):
        logging.info("Recalling State")
        with open(self.json_file, "r") as f:
            self.allStates = json.load(f)
        for name, device in self.devices.items():
            device.setState(self.allStates[name])
        self.initializedStates = True
    
    def getControllerStates(self):
        logging.info("Getting Controller States")
        for name, device in self.devices.items():
            self.allStates[name] = device.getState()
        with open(self.json_file, "w") as f:
            json.dump(self.allStates, f)
        self.initializedStates = True
        
    def set_socket_path(self, path):
        logging.info("Setting Socket Path to " + str(path) )
        self.socket_path = path
    
    def __wait_to_connect(self):

        print("Experiment running... connect when ready")
        logging.info("Awaiting connection...")
        while True:
            try:
                self.connection, self.client_address = self.socket.accept()
                # print("Client Address is {0}".format(self.client_address))
                logging.info("Client Connected")
                self.__data_connection(self.connection)
                time.sleep(0.01)
            except socket.timeout:
                logging.debug("Socket Timeout")
                continue
            except socket.error as err:
                # print("Socket Error: {0}".format(err))
                logging.error("Socket Error!", exc_info=True)
                break

    def __data_connection(self, connection):
        while True:
            try:
                while True:
                    data = self.connection.recv(1024)
                    if data:
                        self.command_handler(data)
                    else:
                        break
                    time.sleep(0.01)
            except socket.error as err:
                logging.error("Connected Socket Error!", exc_info=True)
                # print("Connected Socket Error: {0}".format(err))
                return
            finally:
                self.close_handler()
    
    def device_names(self):
        names = []
        for device_name in self.devices:
            names.append(device_name)
        return names


    def command_handler(self, data):
        print("Data", data)
        data = data.decode('utf-8')
        #logging.info("Handling Command - " + data)
        device_name, command, params = data.strip().split("/")
        params = params.split(",")
        print(device_name, command, params)
        if device_name not in self.devices:
            raise NoDeviceError(device_name)
        response = self.devices[device_name].cmd_handler(command, params)
        
        self.allStates[device_name] = self.devices[device_name].getState()
        with open(self.json_file, "w") as f:
            json.dump(self.allStates, f) 
        return response       

    def exit_handler(self, signal_received, frame):
        # print("\r\nAttempting to exit")
        logging.info("Attempting to exit")
        if self.socket is not None:
            self.socket.close()
            logging.info("Socket is closed")
        
        if self.messenger_socket is not None:
            self.messenger_socket.close()
            logging.info("Messenger socket closed")
        
        logging.info("Looping through devices shutting them down.")
        if not self.admin:
            for device_name, device in self.devices.items():
                logging.info("Running reset and cleanup on device " + device_name)
                device.reset()
                device.cleanup()
        # print("Everything shutdown properly. Exiting.")
        logging.info("Everything shutdown properly. Exiting")
        exit(0)
    
    def close_handler(self):
        logging.info("Client Disconnected. Handling Close.")
        if self.connection is not None:
            self.connection.close()
            logging.info("Connection to client closed.")
        if not self.admin:
            for device_name, device in self.devices.items():
                logging.info("Running reset on device " + device_name)
                device.reset()


    def setup(self):
        try:
            if not self.initializedStates:   #if no historical state is being loaded
                self.getControllerStates()   #read states of controllers and write to json file
            if not os.path.exists(self.socket_path):
                f = open(self.socket_path, 'w')
                f.close()
            
            # if self.messenger is not None:
            #     self.messenger_thread = threading.Thread(target=self.messenger.setup, daemon=True)
            #     self.messenger_thread.start()
            os.unlink(self.socket_path)
            # self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            signal(SIGINT, self.exit_handler)
            # self.socket.bind(self.socket_path)
            # self.socket.listen(1)
            # self.socket.settimeout(1)
            asyncio.run(self.runWebsocketServer())
        except OSError:
            if os.path.exists(self.socket_path):
                print("Error accessing {0}\nTry running 'sudo chown pi: {0}'".format(self.socket_path))
                os._exit(0)
                return
            else:
                print("Socket file not found. Did you configure uv4l-uvc.conf to use {0}?".format(self.socket_path))
                raise
        except socket.error as err:
            logging.error("Socket Error!", exc_info=True)
            print("socket error: {0}".format(err))


    async def websocketCommandServer(self, websocket):
        print("Waiting data")
        async for message in websocket:
            print("Running command", message)
            response = self.command_handler(message)
            print("RESPONSE", response)
            if response is not None:
                print("Sending data")
                await websocket.send(response)


    async def runWebsocketServer(self):
        async with websockets.serve(self.websocketCommandServer, "0.0.0.0", 6048):
            print("Running Carlos's Websocket server")
            await asyncio.Future()
            print("Working")


class Messenger:

    def __init__(self, experiment):
        self.experiment = experiment
        self.socket_path = "/tmp/remla.socket"
        self.socket = None
    
    def __wait_to_connect(self):

        print("Messenger running... waiting for messages")
        while True:
            try:
                self.connection, self.client_address = self.socket.accept()
                # print("Client Address is {0}".format(self.client_address))
                # logging.info("Client Connected")
                self.__data_connection(self.connection)
                time.sleep(0.01)
            except socket.timeout:
                logging.debug("Socket Timeout")
                continue
            except socket.error as err:
                # print("Socket Error: {0}".format(err))
                logging.error("Socket Error!", exc_info=True)
                break

    def __data_connection(self, connection):
        while True:
            try:
                while True:
                    data = self.connection.recv(1024)
                    if data:
                        self.experiment.connection.send(data)
                    else:
                        break
                    time.sleep(0.1)
            except socket.error as err:
                # logging.error("Connected Socket Error!", exc_info=True)
                print("Connected Socket Error: {0}".format(err))
                return
            finally:
                self.close_handler()
    
    def setup(self):
        try:
            if not os.path.exists(self.socket_path):
                f = open(self.socket_path, 'w')
                f.close()
            os.unlink(self.socket_path)
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            self.socket.bind(self.socket_path)
            self.socket.listen(1)
            self.socket.settimeout(1)
            self.experiment.messenger_socket = self.socket
            self.__wait_to_connect()
        except OSError:
            if os.path.exists(self.socket_path):
                print("Error accessing {0}\nTry running 'sudo chown pi: {0}'".format(self.socket_path))
                os._exit(0)
                return
            else:
                print("Socket file not found. Did you configure uv4l-uvc.conf to use {0}?".format(self.socket_path))
                raise
        except socket.error as err:
            # logging.error("Socket Error!", exc_info=True)
            print("socket error: {0}".format(err))
    
    
    def close_handler(self):
        # logging.info("Client Disconnected. Handling Close.")
        if self.connection is not None:
            self.connection.close()
            # logging.info("Connection to client closed.")
    



    
    