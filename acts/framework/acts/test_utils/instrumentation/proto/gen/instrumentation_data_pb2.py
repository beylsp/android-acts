# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: instrumentation_data.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='instrumentation_data.proto',
  package='android.am',
  syntax='proto2',
  serialized_pb=_b('\n\x1ainstrumentation_data.proto\x12\nandroid.am\"\xcf\x01\n\x12ResultsBundleEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x14\n\x0cvalue_string\x18\x02 \x01(\t\x12\x11\n\tvalue_int\x18\x03 \x01(\x11\x12\x13\n\x0bvalue_float\x18\x04 \x01(\x02\x12\x14\n\x0cvalue_double\x18\x05 \x01(\x01\x12\x12\n\nvalue_long\x18\x06 \x01(\x12\x12/\n\x0cvalue_bundle\x18\x07 \x01(\x0b\x32\x19.android.am.ResultsBundle\x12\x13\n\x0bvalue_bytes\x18\x08 \x01(\x0c\"@\n\rResultsBundle\x12/\n\x07\x65ntries\x18\x01 \x03(\x0b\x32\x1e.android.am.ResultsBundleEntry\"M\n\nTestStatus\x12\x13\n\x0bresult_code\x18\x03 \x01(\x11\x12*\n\x07results\x18\x04 \x01(\x0b\x32\x19.android.am.ResultsBundle\"\x98\x01\n\rSessionStatus\x12\x32\n\x0bstatus_code\x18\x01 \x01(\x0e\x32\x1d.android.am.SessionStatusCode\x12\x12\n\nerror_text\x18\x02 \x01(\t\x12\x13\n\x0bresult_code\x18\x03 \x01(\x11\x12*\n\x07results\x18\x04 \x01(\x0b\x32\x19.android.am.ResultsBundle\"i\n\x07Session\x12+\n\x0btest_status\x18\x01 \x03(\x0b\x32\x16.android.am.TestStatus\x12\x31\n\x0esession_status\x18\x02 \x01(\x0b\x32\x19.android.am.SessionStatus*>\n\x11SessionStatusCode\x12\x14\n\x10SESSION_FINISHED\x10\x00\x12\x13\n\x0fSESSION_ABORTED\x10\x01\x42\x19\n\x17\x63om.android.commands.am')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

_SESSIONSTATUSCODE = _descriptor.EnumDescriptor(
  name='SessionStatusCode',
  full_name='android.am.SessionStatusCode',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SESSION_FINISHED', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SESSION_ABORTED', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=659,
  serialized_end=721,
)
_sym_db.RegisterEnumDescriptor(_SESSIONSTATUSCODE)

SessionStatusCode = enum_type_wrapper.EnumTypeWrapper(_SESSIONSTATUSCODE)
SESSION_FINISHED = 0
SESSION_ABORTED = 1



_RESULTSBUNDLEENTRY = _descriptor.Descriptor(
  name='ResultsBundleEntry',
  full_name='android.am.ResultsBundleEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='android.am.ResultsBundleEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_string', full_name='android.am.ResultsBundleEntry.value_string', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_int', full_name='android.am.ResultsBundleEntry.value_int', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_float', full_name='android.am.ResultsBundleEntry.value_float', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_double', full_name='android.am.ResultsBundleEntry.value_double', index=4,
      number=5, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_long', full_name='android.am.ResultsBundleEntry.value_long', index=5,
      number=6, type=18, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_bundle', full_name='android.am.ResultsBundleEntry.value_bundle', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value_bytes', full_name='android.am.ResultsBundleEntry.value_bytes', index=7,
      number=8, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=43,
  serialized_end=250,
)


_RESULTSBUNDLE = _descriptor.Descriptor(
  name='ResultsBundle',
  full_name='android.am.ResultsBundle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entries', full_name='android.am.ResultsBundle.entries', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=252,
  serialized_end=316,
)


_TESTSTATUS = _descriptor.Descriptor(
  name='TestStatus',
  full_name='android.am.TestStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='result_code', full_name='android.am.TestStatus.result_code', index=0,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='results', full_name='android.am.TestStatus.results', index=1,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=318,
  serialized_end=395,
)


_SESSIONSTATUS = _descriptor.Descriptor(
  name='SessionStatus',
  full_name='android.am.SessionStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status_code', full_name='android.am.SessionStatus.status_code', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='error_text', full_name='android.am.SessionStatus.error_text', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='result_code', full_name='android.am.SessionStatus.result_code', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='results', full_name='android.am.SessionStatus.results', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=398,
  serialized_end=550,
)


_SESSION = _descriptor.Descriptor(
  name='Session',
  full_name='android.am.Session',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='test_status', full_name='android.am.Session.test_status', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='session_status', full_name='android.am.Session.session_status', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=552,
  serialized_end=657,
)

_RESULTSBUNDLEENTRY.fields_by_name['value_bundle'].message_type = _RESULTSBUNDLE
_RESULTSBUNDLE.fields_by_name['entries'].message_type = _RESULTSBUNDLEENTRY
_TESTSTATUS.fields_by_name['results'].message_type = _RESULTSBUNDLE
_SESSIONSTATUS.fields_by_name['status_code'].enum_type = _SESSIONSTATUSCODE
_SESSIONSTATUS.fields_by_name['results'].message_type = _RESULTSBUNDLE
_SESSION.fields_by_name['test_status'].message_type = _TESTSTATUS
_SESSION.fields_by_name['session_status'].message_type = _SESSIONSTATUS
DESCRIPTOR.message_types_by_name['ResultsBundleEntry'] = _RESULTSBUNDLEENTRY
DESCRIPTOR.message_types_by_name['ResultsBundle'] = _RESULTSBUNDLE
DESCRIPTOR.message_types_by_name['TestStatus'] = _TESTSTATUS
DESCRIPTOR.message_types_by_name['SessionStatus'] = _SESSIONSTATUS
DESCRIPTOR.message_types_by_name['Session'] = _SESSION
DESCRIPTOR.enum_types_by_name['SessionStatusCode'] = _SESSIONSTATUSCODE

ResultsBundleEntry = _reflection.GeneratedProtocolMessageType('ResultsBundleEntry', (_message.Message,), dict(
  DESCRIPTOR = _RESULTSBUNDLEENTRY,
  __module__ = 'instrumentation_data_pb2'
  # @@protoc_insertion_point(class_scope:android.am.ResultsBundleEntry)
  ))
_sym_db.RegisterMessage(ResultsBundleEntry)

ResultsBundle = _reflection.GeneratedProtocolMessageType('ResultsBundle', (_message.Message,), dict(
  DESCRIPTOR = _RESULTSBUNDLE,
  __module__ = 'instrumentation_data_pb2'
  # @@protoc_insertion_point(class_scope:android.am.ResultsBundle)
  ))
_sym_db.RegisterMessage(ResultsBundle)

TestStatus = _reflection.GeneratedProtocolMessageType('TestStatus', (_message.Message,), dict(
  DESCRIPTOR = _TESTSTATUS,
  __module__ = 'instrumentation_data_pb2'
  # @@protoc_insertion_point(class_scope:android.am.TestStatus)
  ))
_sym_db.RegisterMessage(TestStatus)

SessionStatus = _reflection.GeneratedProtocolMessageType('SessionStatus', (_message.Message,), dict(
  DESCRIPTOR = _SESSIONSTATUS,
  __module__ = 'instrumentation_data_pb2'
  # @@protoc_insertion_point(class_scope:android.am.SessionStatus)
  ))
_sym_db.RegisterMessage(SessionStatus)

Session = _reflection.GeneratedProtocolMessageType('Session', (_message.Message,), dict(
  DESCRIPTOR = _SESSION,
  __module__ = 'instrumentation_data_pb2'
  # @@protoc_insertion_point(class_scope:android.am.Session)
  ))
_sym_db.RegisterMessage(Session)


DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('\n\027com.android.commands.am'))
# @@protoc_insertion_point(module_scope)
