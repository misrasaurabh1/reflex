"""Import operations."""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from collections.abc import Mapping, Sequence


def merge_imports(
    *imports: ImportDict | ParsedImportDict | ParsedImportTuple,
) -> ParsedImportDict:
    """Merge multiple import dicts together.

    Args:
        *imports: The list of import dicts to merge.

    Returns:
        The merged import dicts.
    """
    all_imports: defaultdict[str, list[ImportVar]] = defaultdict(list)

    prefix_paths = ("/utils/", "/components/", "/styles/", "/public/")
    prefix_marker = "$"

    def prefix_lib(lib: str) -> str:
        return prefix_marker + lib if lib.startswith(prefix_paths) else lib

    # Fast local
    list_types = (list, tuple, set)
    ImportVar_ = ImportVar

    for import_dict in imports:
        # Pull keys/values for all input forms just once
        if isinstance(import_dict, tuple):
            items = import_dict
        else:
            items = import_dict.items()
        for lib, fields in items:
            lib = prefix_lib(lib)
            # Fast path for usual type
            if isinstance(fields, str):
                all_imports[lib].append(ImportVar_(fields))
            # For a batch of fields
            elif isinstance(fields, list_types):
                vals = all_imports[lib]
                vals_extend = vals.extend
                # Micro-opt: avoid using generator for small collections
                to_add = []
                for field in fields:
                    if isinstance(field, str):
                        to_add.append(ImportVar_(field))
                    else:
                        to_add.append(field)
                vals_extend(to_add)
            else:
                all_imports[lib].append(
                    fields if not isinstance(fields, str) else ImportVar_(fields)
                )
    return all_imports


def parse_imports(
    imports: ImmutableImportDict | ImmutableParsedImportDict,
) -> ParsedImportDict:
    """Parse the import dict into a standard format.

    Args:
        imports: The import dict to parse.

    Returns:
        The parsed import dict.
    """

    def _make_list(
        value: ImmutableImportTypes,
    ) -> list[str | ImportVar] | list[ImportVar]:
        if isinstance(value, (str, ImportVar)):
            return [value]
        return list(value)

    return {
        package: [
            ImportVar(tag=tag) if isinstance(tag, str) else tag
            for tag in _make_list(maybe_tags)
        ]
        for package, maybe_tags in imports.items()
    }


def collapse_imports(
    imports: ParsedImportDict | ParsedImportTuple,
) -> ParsedImportDict:
    """Remove all duplicate ImportVar within an ImportDict.

    Args:
        imports: The import dict to collapse.

    Returns:
        The collapsed import dict.
    """
    return {
        lib: (
            list(set(import_vars))
            if isinstance(import_vars, list)
            else list(import_vars)
        )
        for lib, import_vars in (
            imports if isinstance(imports, tuple) else imports.items()
        )
    }


@dataclasses.dataclass(frozen=True)
class ImportVar:
    """An import var."""

    # The name of the import tag.
    tag: str | None

    # whether the import is default or named.
    is_default: bool | None = False

    # The tag alias.
    alias: str | None = None

    # Whether this import need to install the associated lib
    install: bool | None = True

    # whether this import should be rendered or not
    render: bool | None = True

    # The path of the package to import from.
    package_path: str = "/"

    # whether this import package should be added to transpilePackages in next.config.js
    # https://nextjs.org/docs/app/api-reference/next-config-js/transpilePackages
    transpile: bool | None = False

    @property
    def name(self) -> str:
        """The name of the import.

        Returns:
            The name(tag name with alias) of tag.
        """
        if self.alias:
            return (
                self.alias if self.is_default else " as ".join([self.tag, self.alias])  # pyright: ignore [reportCallIssue,reportArgumentType]
            )
        else:
            return self.tag or ""


ImportTypes = str | ImportVar | list[str | ImportVar] | list[ImportVar]
ImmutableImportTypes = str | ImportVar | Sequence[str | ImportVar]
ImportDict = dict[str, ImportTypes]
ImmutableImportDict = Mapping[str, ImmutableImportTypes]
ParsedImportDict = dict[str, list[ImportVar]]
ImmutableParsedImportDict = Mapping[str, Sequence[ImportVar]]
ParsedImportTuple = tuple[tuple[str, tuple[ImportVar, ...]], ...]
