#!/usr/bin/python3

import os, sys
import argparse
import json

rl_path = os.path.expanduser(os.path.join("home", "pi", "remoteLabs"))
setup_path = os.path.join(rl_path, "setup")
settings_path = os.path.join(setup_path, ".settings.json"))
settings = {}
config_name = "uv4l_raspicam.conf"
uv4l_path = os.path.join("etc", "uv4l", config_name)

def read_json():
    with open(settings_path, "r") as f:
    settings = json.load(f)

def update_json(setting, value):
    settings[settings] = value
    with open(settings_path "w") as f:
        json.dump(settings, f)

def status(args):
    if settings["status"] == "None":
        print('No lab has been setup yet. Run "remla setup <lab>"')
    print("Current Lab is Setup to Run {0}".format(settings["status"]))

def setup(args):
    if (! os.path.isdir(os.path.join(rl_path, args.lab))):
        print("ERROR: " + arg.lab + " does not exist in the remoteLabs directory.")
        return
    with open(os.path.join(setup_path, args.configfile), "r") as f:
        config_contents = f.read()
    
    config_contents.replace("<rootPath>", os.path.join(rl_path, args.lab))
    config_contents.replace("<port>", args.port)

    with open(os.path.join("etc", "uv4l", args.configfile), "w") as f:
        f.write(config_contents)
    
    update_json("status", args.lab)
    update_json("status", args.configfile)
    

def run(args):
    if settings["status"] != "None":
        lab = settings["status"]
        configfile = settings["configfile"]
        if args.reset:
            controllerFile = lab + "ControllerReset.py"
        else:
            controllerFile = lab + "Controller.py"

        os.system("sudo killall uv4l")
        uv4l_cmd = "sudo uv4l --config-file=/etc/uv4l/" +configfile + " -d raspicam --driver-config-file=/etc/uv4l/" + configfile + " --enable-server yes"
        os.system(uv4l_cmd)

        if args.foreground:
            os.system("python3 " + controllerFile)
        else:
            os.system("nohup ./" + controllerFile)
    
    else:
        print('No lab has been setup yet. Run "remla setup <lab>"')


parser = argparse.ArgumentParser(description="Tool to manage remote labs", prog="remla")

subparsers = parser.add_subparsers(title="commands")

parser_status = subparsers.add_parser("status")
parser_status.set_defaults(func=status)

parser_setup = subparsers.add_parser("setup")
parser_setup.set_defaults(func=setup)
parser_setup.add_argument('lab')
parser_setup.add_argument('-p', '--port', default="80")
parser_setup.add_argument("-c", '--configfile', default=config_name)

parser_run = subparsers.add_parser("run")
parser_run.set_defaults(func=run)
parser_run.add_argument('-f', "--foreground", action="store_true")
parser_run.add_argument('-r, "--reset', action="store_true")

