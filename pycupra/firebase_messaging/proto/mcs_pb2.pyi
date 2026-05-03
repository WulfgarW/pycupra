from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HeartbeatPing(_message.Message):
    __slots__ = ("stream_id", "last_stream_id_received", "status")
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_STREAM_ID_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    stream_id: int
    last_stream_id_received: int
    status: int
    def __init__(self, stream_id: _Optional[int] = ..., last_stream_id_received: _Optional[int] = ..., status: _Optional[int] = ...) -> None: ...

class HeartbeatAck(_message.Message):
    __slots__ = ("stream_id", "last_stream_id_received", "status")
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_STREAM_ID_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    stream_id: int
    last_stream_id_received: int
    status: int
    def __init__(self, stream_id: _Optional[int] = ..., last_stream_id_received: _Optional[int] = ..., status: _Optional[int] = ...) -> None: ...

class ErrorInfo(_message.Message):
    __slots__ = ("code", "message", "type", "extension")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    EXTENSION_FIELD_NUMBER: _ClassVar[int]
    code: int
    message: str
    type: str
    extension: Extension
    def __init__(self, code: _Optional[int] = ..., message: _Optional[str] = ..., type: _Optional[str] = ..., extension: _Optional[_Union[Extension, _Mapping]] = ...) -> None: ...

class Setting(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class HeartbeatStat(_message.Message):
    __slots__ = ("ip", "timeout", "interval_ms")
    IP_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    ip: str
    timeout: bool
    interval_ms: int
    def __init__(self, ip: _Optional[str] = ..., timeout: bool = ..., interval_ms: _Optional[int] = ...) -> None: ...

class HeartbeatConfig(_message.Message):
    __slots__ = ("upload_stat", "ip", "interval_ms")
    UPLOAD_STAT_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    upload_stat: bool
    ip: str
    interval_ms: int
    def __init__(self, upload_stat: bool = ..., ip: _Optional[str] = ..., interval_ms: _Optional[int] = ...) -> None: ...

class ClientEvent(_message.Message):
    __slots__ = ("type", "number_discarded_events", "network_type", "time_connection_started_ms", "time_connection_ended_ms", "error_code", "time_connection_established_ms")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[ClientEvent.Type]
        DISCARDED_EVENTS: _ClassVar[ClientEvent.Type]
        FAILED_CONNECTION: _ClassVar[ClientEvent.Type]
        SUCCESSFUL_CONNECTION: _ClassVar[ClientEvent.Type]
    UNKNOWN: ClientEvent.Type
    DISCARDED_EVENTS: ClientEvent.Type
    FAILED_CONNECTION: ClientEvent.Type
    SUCCESSFUL_CONNECTION: ClientEvent.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    NUMBER_DISCARDED_EVENTS_FIELD_NUMBER: _ClassVar[int]
    NETWORK_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIME_CONNECTION_STARTED_MS_FIELD_NUMBER: _ClassVar[int]
    TIME_CONNECTION_ENDED_MS_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    TIME_CONNECTION_ESTABLISHED_MS_FIELD_NUMBER: _ClassVar[int]
    type: ClientEvent.Type
    number_discarded_events: int
    network_type: int
    time_connection_started_ms: int
    time_connection_ended_ms: int
    error_code: int
    time_connection_established_ms: int
    def __init__(self, type: _Optional[_Union[ClientEvent.Type, str]] = ..., number_discarded_events: _Optional[int] = ..., network_type: _Optional[int] = ..., time_connection_started_ms: _Optional[int] = ..., time_connection_ended_ms: _Optional[int] = ..., error_code: _Optional[int] = ..., time_connection_established_ms: _Optional[int] = ...) -> None: ...

class LoginRequest(_message.Message):
    __slots__ = ("id", "domain", "user", "resource", "auth_token", "device_id", "last_rmq_id", "setting", "received_persistent_id", "adaptive_heartbeat", "heartbeat_stat", "use_rmq2", "account_id", "auth_service", "network_type", "status", "client_event")
    class AuthService(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ANDROID_ID: _ClassVar[LoginRequest.AuthService]
    ANDROID_ID: LoginRequest.AuthService
    ID_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    AUTH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_RMQ_ID_FIELD_NUMBER: _ClassVar[int]
    SETTING_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_PERSISTENT_ID_FIELD_NUMBER: _ClassVar[int]
    ADAPTIVE_HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_STAT_FIELD_NUMBER: _ClassVar[int]
    USE_RMQ2_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    AUTH_SERVICE_FIELD_NUMBER: _ClassVar[int]
    NETWORK_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_EVENT_FIELD_NUMBER: _ClassVar[int]
    id: str
    domain: str
    user: str
    resource: str
    auth_token: str
    device_id: str
    last_rmq_id: int
    setting: _containers.RepeatedCompositeFieldContainer[Setting]
    received_persistent_id: _containers.RepeatedScalarFieldContainer[str]
    adaptive_heartbeat: bool
    heartbeat_stat: HeartbeatStat
    use_rmq2: bool
    account_id: int
    auth_service: LoginRequest.AuthService
    network_type: int
    status: int
    client_event: _containers.RepeatedCompositeFieldContainer[ClientEvent]
    def __init__(self, id: _Optional[str] = ..., domain: _Optional[str] = ..., user: _Optional[str] = ..., resource: _Optional[str] = ..., auth_token: _Optional[str] = ..., device_id: _Optional[str] = ..., last_rmq_id: _Optional[int] = ..., setting: _Optional[_Iterable[_Union[Setting, _Mapping]]] = ..., received_persistent_id: _Optional[_Iterable[str]] = ..., adaptive_heartbeat: bool = ..., heartbeat_stat: _Optional[_Union[HeartbeatStat, _Mapping]] = ..., use_rmq2: bool = ..., account_id: _Optional[int] = ..., auth_service: _Optional[_Union[LoginRequest.AuthService, str]] = ..., network_type: _Optional[int] = ..., status: _Optional[int] = ..., client_event: _Optional[_Iterable[_Union[ClientEvent, _Mapping]]] = ...) -> None: ...

class LoginResponse(_message.Message):
    __slots__ = ("id", "jid", "error", "setting", "stream_id", "last_stream_id_received", "heartbeat_config", "server_timestamp")
    ID_FIELD_NUMBER: _ClassVar[int]
    JID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    SETTING_FIELD_NUMBER: _ClassVar[int]
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_STREAM_ID_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    id: str
    jid: str
    error: ErrorInfo
    setting: _containers.RepeatedCompositeFieldContainer[Setting]
    stream_id: int
    last_stream_id_received: int
    heartbeat_config: HeartbeatConfig
    server_timestamp: int
    def __init__(self, id: _Optional[str] = ..., jid: _Optional[str] = ..., error: _Optional[_Union[ErrorInfo, _Mapping]] = ..., setting: _Optional[_Iterable[_Union[Setting, _Mapping]]] = ..., stream_id: _Optional[int] = ..., last_stream_id_received: _Optional[int] = ..., heartbeat_config: _Optional[_Union[HeartbeatConfig, _Mapping]] = ..., server_timestamp: _Optional[int] = ...) -> None: ...

class StreamErrorStanza(_message.Message):
    __slots__ = ("type", "text")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    type: str
    text: str
    def __init__(self, type: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class Close(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Extension(_message.Message):
    __slots__ = ("id", "data")
    ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    id: int
    data: bytes
    def __init__(self, id: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class IqStanza(_message.Message):
    __slots__ = ("rmq_id", "type", "id", "to", "error", "extension", "persistent_id", "stream_id", "last_stream_id_received", "account_id", "status")
    class IqType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        GET: _ClassVar[IqStanza.IqType]
        SET: _ClassVar[IqStanza.IqType]
        RESULT: _ClassVar[IqStanza.IqType]
        IQ_ERROR: _ClassVar[IqStanza.IqType]
    GET: IqStanza.IqType
    SET: IqStanza.IqType
    RESULT: IqStanza.IqType
    IQ_ERROR: IqStanza.IqType
    RMQ_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    EXTENSION_FIELD_NUMBER: _ClassVar[int]
    PERSISTENT_ID_FIELD_NUMBER: _ClassVar[int]
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_STREAM_ID_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    rmq_id: int
    type: IqStanza.IqType
    id: str
    to: str
    error: ErrorInfo
    extension: Extension
    persistent_id: str
    stream_id: int
    last_stream_id_received: int
    account_id: int
    status: int
    def __init__(self, rmq_id: _Optional[int] = ..., type: _Optional[_Union[IqStanza.IqType, str]] = ..., id: _Optional[str] = ..., to: _Optional[str] = ..., error: _Optional[_Union[ErrorInfo, _Mapping]] = ..., extension: _Optional[_Union[Extension, _Mapping]] = ..., persistent_id: _Optional[str] = ..., stream_id: _Optional[int] = ..., last_stream_id_received: _Optional[int] = ..., account_id: _Optional[int] = ..., status: _Optional[int] = ..., **kwargs) -> None: ...

class AppData(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class DataMessageStanza(_message.Message):
    __slots__ = ("id", "to", "category", "token", "app_data", "from_trusted_server", "persistent_id", "stream_id", "last_stream_id_received", "reg_id", "device_user_id", "ttl", "sent", "queued", "status", "raw_data", "immediate_ack")
    ID_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    APP_DATA_FIELD_NUMBER: _ClassVar[int]
    FROM_TRUSTED_SERVER_FIELD_NUMBER: _ClassVar[int]
    PERSISTENT_ID_FIELD_NUMBER: _ClassVar[int]
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_STREAM_ID_RECEIVED_FIELD_NUMBER: _ClassVar[int]
    REG_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_USER_ID_FIELD_NUMBER: _ClassVar[int]
    TTL_FIELD_NUMBER: _ClassVar[int]
    SENT_FIELD_NUMBER: _ClassVar[int]
    QUEUED_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RAW_DATA_FIELD_NUMBER: _ClassVar[int]
    IMMEDIATE_ACK_FIELD_NUMBER: _ClassVar[int]
    id: str
    to: str
    category: str
    token: str
    app_data: _containers.RepeatedCompositeFieldContainer[AppData]
    from_trusted_server: bool
    persistent_id: str
    stream_id: int
    last_stream_id_received: int
    reg_id: str
    device_user_id: int
    ttl: int
    sent: int
    queued: int
    status: int
    raw_data: bytes
    immediate_ack: bool
    def __init__(self, id: _Optional[str] = ..., to: _Optional[str] = ..., category: _Optional[str] = ..., token: _Optional[str] = ..., app_data: _Optional[_Iterable[_Union[AppData, _Mapping]]] = ..., from_trusted_server: bool = ..., persistent_id: _Optional[str] = ..., stream_id: _Optional[int] = ..., last_stream_id_received: _Optional[int] = ..., reg_id: _Optional[str] = ..., device_user_id: _Optional[int] = ..., ttl: _Optional[int] = ..., sent: _Optional[int] = ..., queued: _Optional[int] = ..., status: _Optional[int] = ..., raw_data: _Optional[bytes] = ..., immediate_ack: bool = ..., **kwargs) -> None: ...

class StreamAck(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SelectiveAck(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[_Iterable[str]] = ...) -> None: ...
