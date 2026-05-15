from datetime import datetime, timezone

# from string import ascii_letters as letters, digits
# from os import environ as env
# from os.path import join, dirname, expanduser
# from itertools import product
import json
import logging
import re

_LOGGER = logging.getLogger(__name__)


def json_loads(s):
    return json.loads(s, object_hook=obj_parser)


def obj_parser(obj):
    """Parse datetime."""
    for key, val in obj.items():
        try:
            if isinstance(val, str):
                if val in ("false", "False", "FALSE"):
                    obj[key] = False
                elif val in ("true", "True", "TRUE"):
                    obj[key] = True
                else:
                    obj[key] = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S%z")
            # dtVal  = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S%z")
            # if dtVal.tzinfo is None:
            #    dtVal  = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
            # obj[key] = dtVal
        except (TypeError, ValueError):
            pass
    return obj


def find_path(src, path):
    """Simple navigation of a hierarchical dict structure using XPATH-like syntax.

    >>> find_path(dict(a=1), 'a')
    1

    >>> find_path(dict(a=1), '')
    {'a': 1}

    >>> find_path(dict(a=None), 'a')


    >>> find_path(dict(a=1), 'b')
    Traceback (most recent call last):
    ...
    KeyError: 'b'

    >>> find_path(dict(a=dict(b=1)), 'a.b')
    1

    >>> find_path(dict(a=dict(b=1)), 'a')
    {'b': 1}

    >>> find_path(dict(a=dict(b=1)), 'a.c')
    Traceback (most recent call last):
    ...
    KeyError: 'c'

    """
    try:
        if not path:
            return src
        if isinstance(path, str):
            path = path.split(".")
        return find_path(src[path[0]], path[1:])
    except Exception as e:
        _LOGGER.error(
            f"Error {e} in find_path for path={path}. Function returns '' and continues."
        )
    return ""


def is_valid_path(src, path) -> bool:
    """
    >>> is_valid_path(dict(a=1), 'a')
    True

    >>> is_valid_path(dict(a=1), '')
    True

    >>> is_valid_path(dict(a=1), None)
    True

    >>> is_valid_path(dict(a=1), 'b')
    False
    """
    try:
        find_path(src, path)
        return True
    except KeyError:
        return False


def camel2slug(s) -> str:
    """Convert camelCase to camel_case.

    >>> camel2slug('fooBar')
    'foo_bar'
    """
    return re.sub("([A-Z])", "_\\1", s).lower().lstrip("_")


def datetime2string(data, withTimezone=False):
    if isinstance(data, dict):
        return {
            key: datetime2string(value, withTimezone) for key, value in data.items()
        }
    elif isinstance(data, list):
        return [datetime2string(item, withTimezone) for item in data]
    elif isinstance(data, datetime):
        if withTimezone:
            return data.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return data.isoformat()
    else:
        return data


def convertTimerUtcToLocal(timer):
    if isinstance(timer, dict):
        newValue = {}
        for key, value in timer.items():
            if key == "startTime":
                n = datetime.strptime(
                    "2025-01-01" + "T" + value + ":00", "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                newValue[key] = n.astimezone(None).strftime("%H:%M")
            else:
                newValue[key] = convertTimerUtcToLocal(value)
        return newValue
    elif isinstance(timer, list):
        return [convertTimerUtcToLocal(item) for item in timer]
    elif isinstance(timer, datetime):
        return timer.astimezone(None).strftime("%Y-%m-%dT%H:%M:%S")
    else:
        return timer
