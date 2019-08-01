# Stubs for kubernetes.client.models.policy_v1beta1_allowed_host_path (Python 2)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Optional

class PolicyV1beta1AllowedHostPath:
    swagger_types: Any = ...
    attribute_map: Any = ...
    discriminator: Any = ...
    path_prefix: Any = ...
    read_only: Any = ...
    def __init__(self, path_prefix: Optional[Any] = ..., read_only: Optional[Any] = ...) -> None: ...
    @property
    def path_prefix(self): ...
    @path_prefix.setter
    def path_prefix(self, path_prefix: Any) -> None: ...
    @property
    def read_only(self): ...
    @read_only.setter
    def read_only(self, read_only: Any) -> None: ...
    def to_dict(self): ...
    def to_str(self): ...
    def __eq__(self, other: Any): ...
    def __ne__(self, other: Any): ...