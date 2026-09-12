"""SDD v3.1 Extension Framework - Core Components (re-export module).

Allows users to create custom mandates and guidelines for domain-specific specializations.

Example:
    >>> from extensions.framework import CustomExtension, ExtensionRegistry
    >>>
    >>> @CustomExtension.register("my-domain")
    >>> class MyDomainExtension:
    ...     mandates = [...]
    ...     guidelines = [...]
    >>>
    >>> registry = ExtensionRegistry()
    >>> extensions = registry.load_all()
"""

from providence_cli.extensions.framework.lifecycle import (  # noqa: F401
    BaseExtension,
    ExtensionMetadata,
)
from providence_cli.extensions.framework.loader import (  # noqa: F401
    Category,
    CustomGuideline,
    CustomMandate,
    ItemType,
)
from providence_cli.extensions.framework.registry import (  # noqa: F401
    ExtensionRegistry,
    get_extension,
    get_registry,
    register_extension,
)

__all__ = [
    "BaseExtension",
    "ExtensionMetadata",
    "Category",
    "CustomGuideline",
    "CustomMandate",
    "ItemType",
    "ExtensionRegistry",
    "get_extension",
    "get_registry",
    "register_extension",
]
