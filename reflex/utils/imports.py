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
    prefix_set = ("/utils/", "/components/", "/styles/", "/public/")

    for import_dict in imports:
        # Support both dict (including defaultdict) and tuple inputs
        if isinstance(import_dict, tuple):
            items = import_dict
        else:
            items = import_dict.items()

        for lib, fields in items:
            # Only prefix if lib starts with any of the designated strings
            if lib.startswith(prefix_set):
                lib_key = "$" + lib
            else:
                lib_key = lib

            # Fast-path: most likely formats first, to minimize isinstance overhead
            # Only support str and ImportVar for elements in `fields`
            if isinstance(fields, str):
                # Convert str field to ImportVar, else assume already ImportVar
                all_imports[lib_key].append(ImportVar(fields))
            elif isinstance(fields, ImportVar):
                all_imports[lib_key].append(fields)
            elif isinstance(fields, (list, tuple, set)):
                # Preprocess to append, avoids calling type field N times
                vals = all_imports[lib_key]
                # Inline: only convert str to ImportVar, else passthrough
                for field in fields:
                    if isinstance(field, str):
                        vals.append(ImportVar(field))
                    else:
                        vals.append(field)
            else:
                # fields is neither str, ImportVar, nor a container: treat as single ImportVar
                all_imports[lib_key].append(fields)

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
