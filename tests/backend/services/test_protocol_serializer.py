from praxis.backend.utils.protocol_serialization import serialize_protocol_function


def sample_protocol(layout, **kwargs):
  return "success"


def test_serialize_protocol_function():
  # Helper to simulate a Praxis-decorated function if needed
  sample_protocol._protocol_definition = {}

  serialized = serialize_protocol_function(sample_protocol)
  assert isinstance(serialized, bytes)
  assert len(serialized) > 0
