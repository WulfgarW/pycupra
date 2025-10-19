from datetime import date, datetime
from base64 import b64encode
from string import ascii_letters as letters, digits
from sys import argv
from os import environ as env
from os.path import join, dirname, expanduser
from itertools import product
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
            obj[key] = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S%z")
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
    if not path:
        return src
    if isinstance(path, str):
        path = path.split(".")
    return find_path(src[path[0]], path[1:])


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


def datetime2string(data):
    if isinstance(data, dict):
        return {key: datetime2string(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [datetime2string(item) for item in data]
    elif isinstance(data, datetime):
        return data.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        return data
