from . import android_checkin_pb2 as _android_checkin_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GservicesSetting(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: bytes
    value: bytes
    def __init__(self, name: _Optional[bytes] = ..., value: _Optional[bytes] = ...) -> None: ...

class AndroidCheckinRequest(_message.Message):
    __slots__ = ("imei", "meid", "mac_addr", "mac_addr_type", "serial_number", "esn", "id", "logging_id", "digest", "locale", "checkin", "desired_build", "market_checkin", "account_cookie", "time_zone", "security_token", "version", "ota_cert", "fragment", "user_name", "user_serial_number")
    IMEI_FIELD_NUMBER: _ClassVar[int]
    MEID_FIELD_NUMBER: _ClassVar[int]
    MAC_ADDR_FIELD_NUMBER: _ClassVar[int]
    MAC_ADDR_TYPE_FIELD_NUMBER: _ClassVar[int]
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ESN_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LOGGING_ID_FIELD_NUMBER: _ClassVar[int]
    DIGEST_FIELD_NUMBER: _ClassVar[int]
    LOCALE_FIELD_NUMBER: _ClassVar[int]
    CHECKIN_FIELD_NUMBER: _ClassVar[int]
    DESIRED_BUILD_FIELD_NUMBER: _ClassVar[int]
    MARKET_CHECKIN_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_COOKIE_FIELD_NUMBER: _ClassVar[int]
    TIME_ZONE_FIELD_NUMBER: _ClassVar[int]
    SECURITY_TOKEN_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    OTA_CERT_FIELD_NUMBER: _ClassVar[int]
    FRAGMENT_FIELD_NUMBER: _ClassVar[int]
    USER_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    imei: str
    meid: str
    mac_addr: _containers.RepeatedScalarFieldContainer[str]
    mac_addr_type: _containers.RepeatedScalarFieldContainer[str]
    serial_number: str
    esn: str
    id: int
    logging_id: int
    digest: str
    locale: str
    checkin: _android_checkin_pb2.AndroidCheckinProto
    desired_build: str
    market_checkin: str
    account_cookie: _containers.RepeatedScalarFieldContainer[str]
    time_zone: str
    security_token: int
    version: int
    ota_cert: _containers.RepeatedScalarFieldContainer[str]
    fragment: int
    user_name: str
    user_serial_number: int
    def __init__(self, imei: _Optional[str] = ..., meid: _Optional[str] = ..., mac_addr: _Optional[_Iterable[str]] = ..., mac_addr_type: _Optional[_Iterable[str]] = ..., serial_number: _Optional[str] = ..., esn: _Optional[str] = ..., id: _Optional[int] = ..., logging_id: _Optional[int] = ..., digest: _Optional[str] = ..., locale: _Optional[str] = ..., checkin: _Optional[_Union[_android_checkin_pb2.AndroidCheckinProto, _Mapping]] = ..., desired_build: _Optional[str] = ..., market_checkin: _Optional[str] = ..., account_cookie: _Optional[_Iterable[str]] = ..., time_zone: _Optional[str] = ..., security_token: _Optional[int] = ..., version: _Optional[int] = ..., ota_cert: _Optional[_Iterable[str]] = ..., fragment: _Optional[int] = ..., user_name: _Optional[str] = ..., user_serial_number: _Optional[int] = ...) -> None: ...

class AndroidCheckinResponse(_message.Message):
    __slots__ = ("stats_ok", "time_msec", "digest", "settings_diff", "delete_setting", "setting", "market_ok", "android_id", "security_token", "version_info")
    STATS_OK_FIELD_NUMBER: _ClassVar[int]
    TIME_MSEC_FIELD_NUMBER: _ClassVar[int]
    DIGEST_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_DIFF_FIELD_NUMBER: _ClassVar[int]
    DELETE_SETTING_FIELD_NUMBER: _ClassVar[int]
    SETTING_FIELD_NUMBER: _ClassVar[int]
    MARKET_OK_FIELD_NUMBER: _ClassVar[int]
    ANDROID_ID_FIELD_NUMBER: _ClassVar[int]
    SECURITY_TOKEN_FIELD_NUMBER: _ClassVar[int]
    VERSION_INFO_FIELD_NUMBER: _ClassVar[int]
    stats_ok: bool
    time_msec: int
    digest: str
    settings_diff: bool
    delete_setting: _containers.RepeatedScalarFieldContainer[str]
    setting: _containers.RepeatedCompositeFieldContainer[GservicesSetting]
    market_ok: bool
    android_id: int
    security_token: int
    version_info: str
    def __init__(self, stats_ok: bool = ..., time_msec: _Optional[int] = ..., digest: _Optional[str] = ..., settings_diff: bool = ..., delete_setting: _Optional[_Iterable[str]] = ..., setting: _Optional[_Iterable[_Union[GservicesSetting, _Mapping]]] = ..., market_ok: bool = ..., android_id: _Optional[int] = ..., security_token: _Optional[int] = ..., version_info: _Optional[str] = ...) -> None: ...
