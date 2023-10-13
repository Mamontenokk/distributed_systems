from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message(_message.Message):
    __slots__ = ["message"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class MessageACK(_message.Message):
    __slots__ = ["ACK"]
    ACK_FIELD_NUMBER: _ClassVar[int]
    ACK: bool
    def __init__(self, ACK: bool = ...) -> None: ...
