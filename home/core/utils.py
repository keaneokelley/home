"""
utils.py
~~~~~~~~

This module contains various utilities.
"""
import hashlib
import importlib
import os
import re
import secrets
import subprocess
from typing import Any, List

from home.core.tasks import scheduler


def to_int(*args: List[Any]) -> List[int]:
    """
    Given a list of strings, attempt to convert each to int. Otherwise, return 0.
    :param n: A string containing an int.
    :return: An integer representation of the provided value.
    """
    result = []
    for n in args:
        try:
            n = int(n)
        except (ValueError, TypeError):
            n = 0
        result.append(n)
    return result if len(result) > 1 else result[0]


def to_float(*args: List[Any]) -> List[int]:
    """
    Given a list of strings, attempt to convert each to float. Otherwise, return 0.
    :param n: A string containing a float.
    :return: A float representation of the provided value.
    """
    result = []
    for n in args:
        try:
            n = float(n)
        except (ValueError, TypeError):
            n = 0
        result.append(n)
    return result if len(result) > 1 else result[0]


def RGBfromhex(color_hex: str) -> (int, int, int):
    """
    Given a string in the format '#xxxxxx', where '#' is optional and
    'xxxxxx' represents 3 hexadecimal bytes, convert to RGB integer
    values between 0 and 255. Return all zeros if input is invalid.
    :param color_hex: A color represented by hex values.
    :return: 3 integer values for RGB values.
    """
    red = 0
    green = 0
    blue = 0
    if re.match('^#?[A-Fa-f0-9]{6}$', color_hex):
        color_hex = color_hex.replace('#', '')
        red = int(color_hex[0:2], 16)
        green = int(color_hex[2:4], 16)
        blue = int(color_hex[4:6], 16)
    return red, green, blue


def class_from_name(module_name: str, class_name: str):
    """
    Given a module name and class name, return a class.
    :param module_name: Module name to import.
    :param class_name: Class name to find in the module.
    :return: The class object.
    """
    try:
        return getattr(importlib.import_module(
            'home.iot.' + module_name),
            class_name
        )
    except ImportError as e:
        print(f"No such module exists: {module_name}.{class_name}")
        raise e


def method_from_name(klass, method_name: str):
    """
    Given an imported class, return the given method pointer.
    :param klass: An imported class containing the method.
    :param method_name: The method name to find.
    :return: The method pointer
    """
    try:
        return getattr(klass, method_name)
    except AttributeError:
        raise NotImplementedError()


def random_string(length: int = 32) -> str:
    return secrets.token_hex(length)


def reload():
    """
    Restart the application.
    """
    subprocess.call(['sudo', 'systemctl', 'restart', 'home'])


def update():
    """
    Perform an update from git.
    """
    subprocess.call(['git', 'stash'])
    subprocess.call(['git', 'pull', 'origin', 'master'])
    subprocess.call(['git', 'stash', 'apply'])
    # subprocess.call(['/srv/www/home/env/bin/pip', 'install', '.', '--upgrade'])
    subprocess.call(['/srv/www/home/env/bin/pip', 'install', '-r', 'requirements.txt', '--no-deps', '--upgrade'])
    reload()


def clear_scheduled_jobs():
    for job in scheduler.get_jobs():
        job.remove()


def get_groups(it):
    groups = {}
    for t in it:
        if not groups.get(t.group):
            groups[t.group] = [t]
        else:
            groups[t.group].append(t)
    return groups
