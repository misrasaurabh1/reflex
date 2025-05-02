"""Module to implement lazy loading in reflex.

BSD 3-Clause License

Copyright (c) 2022--2023, Scientific Python project All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

    Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import annotations

import importlib
import os
import sys


def attach(
    package_name: str,
    submodules: set[str] | None = None,
    submod_attrs: dict[str, list[str]] | None = None,
):
    """Replaces a package's __getattr__, __dir__, and __all__ attributes using lazy.attach.
    The lazy loader __getattr__ doesn't support tuples as list values. We needed to add
    this functionality (tuples) in Reflex to support 'import as _' statements. This function
    reformats the submod_attrs dictionary to flatten the module list before passing it to
    lazy_loader.

    Args:
        package_name: name of the package.
        submodules : List of submodules to attach.
        submod_attrs : Dictionary of submodule -> list of attributes / functions.
                    These attributes are imported as they are used.

    Returns:
        __getattr__, __dir__, __all__
    """
    # Minor fast-path: setattrs = () if None
    if submod_attrs:
        # Try to avoid 'any(isinstance...)' cost and the following costly flatten if not needed
        needs_flatten = False
        # Only scan until first tuple found
        for v in submod_attrs.values():
            for mod in v:
                if isinstance(mod, tuple):
                    needs_flatten = True
                    break
            if needs_flatten:
                break
        if needs_flatten:
            # Flatten with generator for better cache and lower temporary overhead
            submod_attrs = {
                k: [(mod if not isinstance(mod, tuple) else mod[1]) for mod in v]
                for k, v in submod_attrs.items()
            }
        else:
            # Even this shallow copy is often unnecessary;
            # but to guarantee no mutation of input, keep it
            submod_attrs = dict(submod_attrs)
    else:
        submod_attrs = {}

    submodules = set(submodules) if submodules is not None else set()

    # Optimize: use dict comprehension directly for attr_to_modules
    attr_to_modules = {
        attr: mod for mod, attrs in submod_attrs.items() for attr in attrs
    }

    # __all__ will contain everything from submodules and attribute keys
    # Avoid intermediate memory use: use generator and sort in-place
    __all__ = list(submodules)
    __all__.extend(attr_to_modules.keys())
    if len(__all__) > 1:
        __all__.sort()

    def __getattr__(name: str):  # noqa: N807
        if name in submodules:
            return importlib.import_module(f"{package_name}.{name}")
        elif name in attr_to_modules:
            submod_path = f"{package_name}.{attr_to_modules[name]}"
            submod = importlib.import_module(submod_path)
            attr = getattr(submod, name)

            # If the attribute lives in a file (module) with the same
            # name as the attribute, ensure that the attribute and *not*
            # the module is accessible on the package.
            if name == attr_to_modules[name]:
                pkg = sys.modules[package_name]
                pkg.__dict__[name] = attr

            return attr
        else:
            raise AttributeError(f"No {package_name} attribute {name}")

    def __dir__():  # noqa: N807
        return __all__

    # EAGER_IMPORT optimization: avoid allocating extra sets for union
    if os.environ.get("EAGER_IMPORT", ""):
        for attr in submodules:
            __getattr__(attr)
        for attr in attr_to_modules:
            # Avoid double-import for names that are both a submodule and attr_to_modules key
            if attr not in submodules:
                __getattr__(attr)

    return __getattr__, __dir__, __all__
