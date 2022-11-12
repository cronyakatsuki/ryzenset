#!/usr/bin/env python3

import argparse
import configparser
import os
import sys
import argparse
from ctypes import *

VERSION = "0.1"
CONFIG_FILE = f"/home/{os.getlogin()}/.local/share/ryzen-set/profiles.ini"

lib_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(lib_path)

lib = cdll.LoadLibrary('/usr/lib64/libryzenadj.so')

# define ctype mappings for types which can not be mapped automatically
# ryzenadj tables
lib.init_ryzenadj.restype = c_void_p
lib.refresh_table.argtypes = [c_void_p]
# Stapm value and limit
lib.get_stapm_limit.restype = c_float
lib.get_stapm_limit.argtypes = [c_void_p]
# Slow limit and value
lib.get_slow_limit.restype = c_float
lib.get_slow_limit.argtypes = [c_void_p]
# Fast limit and value
lib.get_fast_limit.restype = c_float
lib.get_fast_limit.argtypes = [c_void_p]
# Slow time and value
lib.get_slow_time.restype = c_float
lib.get_slow_time.argtypes = [c_void_p]
# stapm time and value
lib.get_stapm_time.restype = c_float
lib.get_stapm_time.argtypes = [c_void_p]
# Vrm Max Current and value
lib.get_vrmmax_current.restype = c_float
lib.get_vrmmax_current.argtypes = [c_void_p]
# Tctl cpu temp
lib.get_tctl_temp.restype = c_float
lib.get_tctl_temp.argtypes = [c_void_p]

ry = lib.init_ryzenadj()

if not ry:
    sys.exit("RyzenAdj could not get initialized")

error_messages = {
    -1: "{:s} is not supported on this family\n",
    -3: "{:s} is not supported on this SMU\n",
    -4: "{:s} is rejected by SMU\n"
}


def adjust(field, value):
    function_name = "set_" + field
    adjust_func = lib.__getattr__(function_name)
    adjust_func.argtypes = [c_void_p, c_ulong]
    res = adjust_func(ry, value)
    if res:
        error = error_messages.get(res, "{:s} did fail with {:d}\n")
        sys.stderr.write(error.format(function_name, res))
    else:
        print(f"Sucessfully set {field} to {value}")


def enable(field):
    function_name = "set_" + field
    adjust_func = lib.__getattr__(function_name)
    adjust_func.argtypes = [c_void_p]
    res = adjust_func(ry)
    if res:
        error = error_messages.get(res, "{:s} did fail with {:d}\n")
        sys.stderr.write(error.format(function_name, res))
    else:
        print(f"Sucessfully enable {field}")


def list_categories(config):
    categories = []
    for profile in config.sections():
        if config.has_option(profile, "category"):
            category = config.get(profile, "category")
            if category not in categories:
                categories.append(category)

    for category in categories:
        print(category)


def list_by_category(list, config):
    if list == "categories":
        list_categories(config)
    else:
        for profile in config.sections():
            if config.has_option(profile, "category"):
                if config.get(profile, "category") == list:
                    print(profile)
    sys.exit(0)


def set_from_config(config, profile):
    adjust("stapm_limit", config.getint(profile, 'stapm-limit'))
    adjust("fast_limit", config.getint(profile, 'fast-limit'))
    adjust("slow_limit", config.getint(profile, 'slow-limit'))
    adjust("slow_time", config.getint(profile, 'slow-time'))
    adjust("stapm_time", config.getint(profile, 'stapm-time'))
    adjust("tctl_temp", config.getint(profile, 'tctl-temp'))
    adjust("vrmmax_current", config.getint(profile, 'vrmmax-current'))

    if config.getboolean(profile, 'max-performance'):
        enable("max_performance")
    else:
        enable("power_saving")


def get_current_profile(config):
    profiles = config.sections()
    lib.refresh_table(ry)
    current = {
               'stapm-limit' : f'{round(lib.get_stapm_limit(ry) * 1000)}',
               'fast-limit' : f'{round(lib.get_fast_limit(ry) * 1000)}',
               'slow-limit' : f'{round(lib.get_slow_limit(ry) * 1000)}',
               'slow-time' : f'{round(lib.get_slow_time(ry))}',
               'stapm-time' : f'{round(lib.get_stapm_time(ry))}',
               'tctl-temp' : f'{round(lib.get_tctl_temp(ry))}',
               'vrmmax-current' : f'{round(lib.get_vrmmax_current(ry) * 1000)}',
               }

    for profile in profiles:
        options = dict(config.items(profile))
        options.pop('category')
        options.pop('max-performance')
        if current == options:
            print(profile)
            sys.exit(0)

    print("system-default")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true',
                        help='Print program version')

    subparser = parser.add_subparsers(dest='command')

    list = subparser.add_parser(
        'list', help="List profile category's or profiles from a category")
    list.add_argument('category', type=str, metavar='CATEGORY', action='store', nargs='?',
                      help="Category to print profiles from")

    set = subparser.add_parser('set', help="Set specified profile")
    set.add_argument('profile', type=str, metavar='PROFILE', action='store', nargs='?',
                     help="Profile name from the config")

    subparser.add_parser('get', help="Get current profile")

    config = configparser.ConfigParser()

    if os.path.isfile((CONFIG_FILE)):
        configExists = True
        config.read(os.path.expanduser(
            CONFIG_FILE))
    else:
        configExists = False

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.version:
        print(f'Version: {VERSION}')
        sys.exit(0)

    if not configExists:
        print("No config existing, add profiles first")
        sys.exit(1)

    if args.command == 'list':
        if args.category:
            list_by_category(args.category, config)
        else:
            list_categories(config)
        sys.exit(0)

    if args.command == 'set':
        if args.profile:
            set_from_config(config, args.profile)
        else:
            print('Profile must be provided')
            sys.exit(1)

    if args.command == 'get':
        get_current_profile(config)

if __name__ == "__main__":
    main()
