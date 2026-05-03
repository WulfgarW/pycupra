from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DeviceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DEVICE_ANDROID_OS: _ClassVar[DeviceType]
    DEVICE_IOS_OS: _ClassVar[DeviceType]
    DEVICE_CHROME_BROWSER: _ClassVar[DeviceType]
    DEVICE_CHROME_OS: _ClassVar[DeviceType]
DEVICE_ANDROID_OS: DeviceType
DEVICE_IOS_OS: DeviceType
DEVICE_CHROME_BROWSER: DeviceType
DEVICE_CHROME_OS: DeviceType

class ChromeBuildProto(_message.Message):
    __slots__ = ("platform", "chrome_version", "channel")
    class Platform(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        PLATFORM_WIN: _ClassVar[ChromeBuildProto.Platform]
        PLATFORM_MAC: _ClassVar[ChromeBuildProto.Platform]
        PLATFORM_LINUX: _ClassVar[ChromeBuildProto.Platform]
        PLATFORM_CROS: _ClassVar[ChromeBuildProto.Platform]
        PLATFORM_IOS: _ClassVar[ChromeBuildProto.Platform]
        PLATFORM_ANDROID: _ClassVar[ChromeBuildProto.Platform]
    PLATFORM_WIN: ChromeBuildProto.Platform
    PLATFORM_MAC: ChromeBuildProto.Platform
    PLATFORM_LINUX: ChromeBuildProto.Platform
    PLATFORM_CROS: ChromeBuildProto.Platform
    PLATFORM_IOS: ChromeBuildProto.Platform
    PLATFORM_ANDROID: ChromeBuildProto.Platform
    class Channel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CHANNEL_STABLE: _ClassVar[ChromeBuildProto.Channel]
        CHANNEL_BETA: _ClassVar[ChromeBuildProto.Channel]
        CHANNEL_DEV: _ClassVar[ChromeBuildProto.Channel]
        CHANNEL_CANARY: _ClassVar[ChromeBuildProto.Channel]
        CHANNEL_UNKNOWN: _ClassVar[ChromeBuildProto.Channel]
    CHANNEL_STABLE: ChromeBuildProto.Channel
    CHANNEL_BETA: ChromeBuildProto.Channel
    CHANNEL_DEV: ChromeBuildProto.Channel
    CHANNEL_CANARY: ChromeBuildProto.Channel
    CHANNEL_UNKNOWN: ChromeBuildProto.Channel
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    CHROME_VERSION_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    platform: ChromeBuildProto.Platform
    chrome_version: str
    channel: ChromeBuildProto.Channel
    def __init__(self, platform: _Optional[_Union[ChromeBuildProto.Platform, str]] = ..., chrome_version: _Optional[str] = ..., channel: _Optional[_Union[ChromeBuildProto.Channel, str]] = ...) -> None: ...

class AndroidCheckinProto(_message.Message):
    __slots__ = ("last_checkin_msec", "cell_operator", "sim_operator", "roaming", "user_number", "type", "chrome_build")
    LAST_CHECKIN_MSEC_FIELD_NUMBER: _ClassVar[int]
    CELL_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    SIM_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    ROAMING_FIELD_NUMBER: _ClassVar[int]
    USER_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CHROME_BUILD_FIELD_NUMBER: _ClassVar[int]
    last_checkin_msec: int
    cell_operator: str
    sim_operator: str
    roaming: str
    user_number: int
    type: DeviceType
    chrome_build: ChromeBuildProto
    def __init__(self, last_checkin_msec: _Optional[int] = ..., cell_operator: _Optional[str] = ..., sim_operator: _Optional[str] = ..., roaming: _Optional[str] = ..., user_number: _Optional[int] = ..., type: _Optional[_Union[DeviceType, str]] = ..., chrome_build: _Optional[_Union[ChromeBuildProto, _Mapping]] = ...) -> None: ...
