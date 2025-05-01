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
    for import_dict in imports:
        for lib, fields in (
            import_dict if isinstance(import_dict, tuple) else import_dict.items()
        ):
            # If the lib is an absolute path, we need to prefix it with a $
            lib = (
                "$" + lib
                if lib.startswith(("/utils/", "/components/", "/styles/", "/public/"))
                else lib
            )
            if isinstance(fields, (list, tuple, set)):
                all_imports[lib].extend(
                    ImportVar(field) if isinstance(field, str) else field
                    for field in fields
                )
            else:
                all_imports[lib].append(
                    ImportVar(fields) if isinstance(fields, str) else fields
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
    str_type = str
    ImportVar_type = ImportVar
    isinstance_ = isinstance

    # Alias to minimize attribute lookups in the loop
    import_items = imports.items

    result = {}
    for package, maybe_tags in import_items():
        # Fast path: if single string or ImportVar, make list on the fly
        if isinstance_(maybe_tags, str_type):
            tags = [ImportVar_type(tag=maybe_tags)]
        elif isinstance_(maybe_tags, ImportVar_type):
            tags = [maybe_tags]
        else:
            # List/Sequence case; predefine methods/vars in local scope for speed
            list_tags = []
            append = list_tags.append
            for tag in maybe_tags:
                if isinstance_(tag, str_type):
                    append(ImportVar_type(tag=tag))
                else:
                    append(tag)
            tags = list_tags
        result[package] = tags

    return result


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
