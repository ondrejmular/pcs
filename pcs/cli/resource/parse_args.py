from dataclasses import dataclass
from typing import (
    Any,
    Optional,
)

from pcs.cli.common.errors import (
    SEE_MAN_CHANGES,
    CmdLineInputError,
)
from pcs.cli.common.parse_args import (
    FUTURE_OPTION,
    ArgsByKeywords,
    Argv,
    KeyValueParser,
    group_by_keywords,
)
from pcs.cli.reports.output import deprecation_warning


@dataclass(frozen=True)
class PrimitiveOptions:
    instance_attrs: dict[str, str]
    meta_attrs: dict[str, str]
    operations: list[dict[str, str]]


@dataclass(frozen=True)
class CloneOptions:
    clone_id: Optional[str]
    meta_attrs: dict[str, str]


@dataclass(frozen=True)
class ComplexResourceOptions:
    primitive: PrimitiveOptions
    clone: Optional[CloneOptions]
    promotable: Optional[CloneOptions]
    bundle_id: Optional[str]


@dataclass(frozen=True)
class BundleCreateOptions:
    container_type: str
    container: dict[str, str]
    network: dict[str, str]
    port_map: list[dict[str, str]]
    storage_map: list[dict[str, str]]
    meta_attrs: dict[str, str]


@dataclass(frozen=True)
class BundleUpdateOptions:
    container: dict[str, str]
    network: dict[str, str]
    port_map_add: list[dict[str, str]]
    port_map_remove: list[str]
    storage_map_add: list[dict[str, str]]
    storage_map_remove: list[str]
    meta_attrs: dict[str, str]


@dataclass(frozen=True)
class AddRemoveOptions:
    add: list[dict[str, str]]
    remove: list[str]


def parse_primitive(arg_list: Argv) -> PrimitiveOptions:
    groups = group_by_keywords(
        arg_list, set(["op", "meta"]), implicit_first_keyword="instance"
    )

    parts = PrimitiveOptions(
        instance_attrs=KeyValueParser(
            groups.get_args_flat("instance")
        ).get_unique(),
        meta_attrs=KeyValueParser(groups.get_args_flat("meta")).get_unique(),
        operations=[
            KeyValueParser(op).get_unique()
            for op in build_operations(groups.get_args_groups("op"))
        ],
    )

    return parts


def parse_clone(arg_list: Argv, promotable: bool = False) -> CloneOptions:
    clone_id = None
    allowed_keywords = set(["op", "meta"])
    if (
        arg_list
        and arg_list[0] not in allowed_keywords
        and "=" not in arg_list[0]
    ):
        clone_id = arg_list.pop(0)
    groups = group_by_keywords(
        arg_list, allowed_keywords, implicit_first_keyword="options"
    )

    if groups.has_keyword("op"):
        raise CmdLineInputError(
            "op settings must be changed on base resource, not the clone",
        )
    if groups.has_keyword("options"):
        # deprecated since 0.11.6
        deprecation_warning(
            "configuring meta attributes without specifying the 'meta' keyword "
            "is deprecated and will be removed in a future release"
        )

    meta = KeyValueParser(
        groups.get_args_flat("options") + groups.get_args_flat("meta")
    ).get_unique()
    if promotable:
        if "promotable" in meta:
            raise CmdLineInputError(
                "you cannot specify both promotable option and promotable "
                "keyword"
            )
        meta["promotable"] = "true"
    return CloneOptions(clone_id=clone_id, meta_attrs=meta)


def parse_create(
    arg_list: Argv, new_parser: bool = False
) -> ComplexResourceOptions:
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    groups: dict[str, Any] = {}
    top_groups = group_by_keywords(
        arg_list,
        set(["clone", "promotable", "bundle"]),
        implicit_first_keyword="primitive",
    )

    primitive_groups = group_by_keywords(
        top_groups.get_args_flat("primitive"),
        set(["op", "meta"]),
        implicit_first_keyword="instance",
    )
    groups["instance"] = primitive_groups.get_args_flat("instance")
    groups["meta"] = primitive_groups.get_args_flat("meta")
    groups["op"] = primitive_groups.get_args_groups("op")

    for clone_type in ("clone", "promotable"):
        if top_groups.has_keyword(clone_type):
            clone_groups = group_by_keywords(
                top_groups.get_args_flat(clone_type),
                set(["op", "meta"]),
                implicit_first_keyword="options",
            )
            groups[clone_type] = clone_groups.get_args_flat("options")
            if groups[clone_type]:
                clone_meta = (
                    groups[clone_type][1:]
                    if "=" not in groups[clone_type][0]
                    else groups[clone_type]
                )
                if clone_meta:
                    if new_parser:
                        raise CmdLineInputError(
                            f"Specifying instance attributes for a {clone_type} "
                            f"is not supported. Use 'meta' after '{clone_type}' "
                            "if you want to specify meta attributes."
                        )
                    deprecation_warning(
                        f"Configuring {clone_type} meta attributes without specifying "
                        f"the 'meta' keyword after the '{clone_type}' keyword "
                        "is deprecated and will be removed in a future release. "
                        f"Specify {FUTURE_OPTION} to switch to the future behavior."
                    )
            if clone_groups.has_keyword("op"):
                if new_parser:
                    raise CmdLineInputError(
                        "op settings must be defined on the base resource, "
                        f"not the {clone_type}"
                    )
                deprecation_warning(
                    f"Specifying 'op' after '{clone_type}' now defines "
                    "operations for the base resource. In future, this "
                    f"will be removed and operations will have to be specified "
                    f"before '{clone_type}'. "
                    f"Specify {FUTURE_OPTION} to switch to the future behavior."
                )
                groups["op"] += clone_groups.get_args_groups("op")
            if clone_groups.has_keyword("meta"):
                if new_parser:
                    groups[clone_type] += clone_groups.get_args_flat("meta")
                else:
                    deprecation_warning(
                        f"Specifying 'meta' after '{clone_type}' now defines "
                        "meta attributes for the base resource. In future, this "
                        f"will define meta attributes for the {clone_type}. "
                        f"Specify {FUTURE_OPTION} to switch to the future behavior."
                    )
                    groups["meta"] += clone_groups.get_args_flat("meta")

    if top_groups.has_keyword("bundle"):
        bundle_groups = group_by_keywords(
            top_groups.get_args_flat("bundle"),
            set(["op", "meta"]),
            implicit_first_keyword="options",
        )
        groups["bundle"] = bundle_groups.get_args_flat("options")
        if bundle_groups.has_keyword("meta"):
            if new_parser:
                raise CmdLineInputError(
                    "meta options must be defined on the base resource, "
                    "not the bundle"
                )
            deprecation_warning(
                "Specifying 'meta' after 'bundle' now defines meta options for "
                "the base resource. In future, this will be removed and meta "
                "options will have to be specified before 'bundle'. "
                f"Specify {FUTURE_OPTION} to switch to the future behavior."
            )
            groups["meta"] += bundle_groups.get_args_flat("meta")
        if bundle_groups.has_keyword("op"):
            if new_parser:
                raise CmdLineInputError(
                    "op settings must be defined on the base resource, "
                    "not the bundle"
                )
            deprecation_warning(
                "Specifying 'op' after 'bundle' now defines operations for the "
                "base resource. In future, this will be removed and operations "
                "will have to be specified before 'bundle'. "
                f"Specify {FUTURE_OPTION} to switch to the future behavior."
            )
            groups["op"] += bundle_groups.get_args_groups("op")

    def get_clone_options(options: Argv) -> CloneOptions:
        clone_id = None
        if options and "=" not in options[0]:
            clone_id = options.pop(0)
        return CloneOptions(
            clone_id=clone_id, meta_attrs=KeyValueParser(options).get_unique()
        )

    if "bundle" in groups and len(groups["bundle"]) != 1:
        raise CmdLineInputError("you have to specify exactly one bundle")

    try:
        return ComplexResourceOptions(
            primitive=PrimitiveOptions(
                instance_attrs=KeyValueParser(groups["instance"]).get_unique(),
                meta_attrs=KeyValueParser(groups["meta"]).get_unique(),
                operations=[
                    KeyValueParser(op).get_unique()
                    for op in build_operations(groups["op"])
                ],
            ),
            clone=(
                get_clone_options(groups["clone"])
                if "clone" in groups
                else None
            ),
            promotable=(
                get_clone_options(groups["promotable"])
                if "promotable" in groups
                else None
            ),
            bundle_id=groups["bundle"][0] if "bundle" in groups else None,
        )
    except CmdLineInputError as e:
        # Print error messages which point users to the changes section in pcs
        # manpage.
        # To be removed in the next significant version.
        if e.message == "missing value of 'master' option":
            raise CmdLineInputError(
                message=e.message,
                hint=(
                    "Master/Slave resources have been renamed to promotable "
                    "clones, please use the 'promotable' keyword instead of "
                    "'master'. " + SEE_MAN_CHANGES.format("0.10")
                ),
            ) from e
        raise


def _parse_bundle_groups(arg_list: Argv) -> ArgsByKeywords:
    """
    Commandline options: no options
    """
    repeatable_keyword_list = ["port-map", "storage-map"]
    keyword_list = ["meta", "container", "network"] + repeatable_keyword_list
    groups = group_by_keywords(arg_list, set(keyword_list))
    for keyword in keyword_list:
        if not groups.has_keyword(keyword):
            continue
        if keyword in repeatable_keyword_list:
            for repeated_section in groups.get_args_groups(keyword):
                if not repeated_section:
                    raise CmdLineInputError(f"No {keyword} options specified")
        else:
            if not groups.get_args_flat(keyword):
                raise CmdLineInputError(f"No {keyword} options specified")
    return groups


def _parse_bundle_create_or_reset(
    arg_list: Argv, reset: bool
) -> BundleCreateOptions:
    """
    Commandline options: no options
    """
    groups = _parse_bundle_groups(arg_list)
    container_options = groups.get_args_flat("container")
    container_type = ""
    if not reset and container_options and "=" not in container_options[0]:
        container_type = container_options.pop(0)
    return BundleCreateOptions(
        container_type=container_type,
        container=KeyValueParser(container_options).get_unique(),
        network=KeyValueParser(groups.get_args_flat("network")).get_unique(),
        port_map=[
            KeyValueParser(port_map).get_unique()
            for port_map in groups.get_args_groups("port-map")
        ],
        storage_map=[
            KeyValueParser(storage_map).get_unique()
            for storage_map in groups.get_args_groups("storage-map")
        ],
        meta_attrs=KeyValueParser(groups.get_args_flat("meta")).get_unique(),
    )


def parse_bundle_create_options(arg_list: Argv) -> BundleCreateOptions:
    """
    Commandline options: no options
    """
    return _parse_bundle_create_or_reset(arg_list, reset=False)


def parse_bundle_reset_options(arg_list: Argv) -> BundleCreateOptions:
    """
    Commandline options: no options
    """
    return _parse_bundle_create_or_reset(arg_list, reset=True)


def _split_bundle_map_update_op_and_options(
    map_arg_list: Argv, result_parts: AddRemoveOptions, map_name: str
) -> None:
    if len(map_arg_list) < 2:
        raise _bundle_map_update_not_valid(map_name)
    op, options = map_arg_list[0], map_arg_list[1:]
    if op == "add":
        result_parts.add.append(KeyValueParser(options).get_unique())
    elif op in {"delete", "remove"}:
        result_parts.remove.extend(options)
    else:
        raise _bundle_map_update_not_valid(map_name)


def _bundle_map_update_not_valid(map_name: str) -> CmdLineInputError:
    return CmdLineInputError(
        (
            "When using '{map}' you must specify either 'add' and options or "
            "either of 'delete' or 'remove' and id(s)"
        ).format(map=map_name)
    )


def parse_bundle_update_options(arg_list: Argv) -> BundleUpdateOptions:
    """
    Commandline options: no options
    """
    groups = _parse_bundle_groups(arg_list)
    port_map = AddRemoveOptions(add=[], remove=[])
    for map_group in groups.get_args_groups("port-map"):
        _split_bundle_map_update_op_and_options(map_group, port_map, "port-map")
    storage_map = AddRemoveOptions(add=[], remove=[])
    for map_group in groups.get_args_groups("storage-map"):
        _split_bundle_map_update_op_and_options(
            map_group, storage_map, "storage-map"
        )
    return BundleUpdateOptions(
        container=KeyValueParser(
            groups.get_args_flat("container")
        ).get_unique(),
        network=KeyValueParser(groups.get_args_flat("network")).get_unique(),
        port_map_add=port_map.add,
        port_map_remove=port_map.remove,
        storage_map_add=storage_map.add,
        storage_map_remove=storage_map.remove,
        meta_attrs=KeyValueParser(groups.get_args_flat("meta")).get_unique(),
    )


def build_operations(op_group_list: list[Argv]) -> list[Argv]:
    """
    Return a list of dicts. Each dict represents one operation.

    op_group_list -- contains items that have parameters after "op"
        (so item can contain multiple operations) for example: [
            [monitor timeout=1 start timeout=2],
            [monitor timeout=3 interval=10],
        ]
    """
    operation_list = []
    for op_group in op_group_list:
        # empty operation is not allowed
        if not op_group:
            raise __not_enough_parts_in_operation()

        # every operation group needs to start with operation name
        if "=" in op_group[0]:
            raise __every_operation_needs_name()

        for arg in op_group:
            if "=" not in arg:
                operation_list.append(["name={0}".format(arg)])
            else:
                operation_list[-1].append(arg)

    # every operation needs at least name and one option
    # there can be more than one operation in op_group: check is after
    # processing
    if any(len(operation) < 2 for operation in operation_list):
        raise __not_enough_parts_in_operation()

    return operation_list


def __not_enough_parts_in_operation() -> CmdLineInputError:
    return CmdLineInputError(
        "When using 'op' you must specify an operation name"
        " and at least one option"
    )


def __every_operation_needs_name() -> CmdLineInputError:
    return CmdLineInputError(
        "When using 'op' you must specify an operation name after 'op'"
    )
