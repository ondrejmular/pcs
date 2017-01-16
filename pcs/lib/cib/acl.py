from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from functools import partial

from lxml import etree

from pcs.lib import reports
from pcs.lib.errors import LibraryError
from pcs.lib.cib.tools import (
    etree_element_attibutes_to_dict,
    check_new_id_applicable,
    does_id_exist,
    find_unique_id,
    find_element_by_tag_and_id,
)



TAG_GROUP = "acl_group"
TAG_ROLE = "acl_role"
TAG_TARGET = "acl_target"
TAG_PERMISSION = "acl_permission"

TAG_DESCRIPTION_MAP = {
    TAG_GROUP: "group",
    TAG_ROLE: "role",
    TAG_TARGET: "user",
    TAG_PERMISSION: "permission"
}

def validate_permissions(tree, permission_info_list):
    """
    Validate given permission list.
    Raise LibraryError if any of permission is not valid.

    tree -- cib tree
    permission_info_list -- list of tuples like this:
        ("read|write|deny", "xpath|id", <id-or-xpath-string>)
    """
    report_items = []
    allowed_permissions = ["read", "write", "deny"]
    allowed_scopes = ["xpath", "id"]
    for permission, scope_type, scope in permission_info_list:
        if not permission in allowed_permissions:
            report_items.append(reports.invalid_option_value(
                "permission",
                permission,
                allowed_permissions
            ))

        if not scope_type in allowed_scopes:
            report_items.append(reports.invalid_option_value(
                "scope type",
                scope_type,
                allowed_scopes
            ))

        if scope_type == 'id' and not does_id_exist(tree, scope):
            report_items.append(reports.id_not_found(scope, "id"))

    if report_items:
        raise LibraryError(*report_items)


def find(
    tag, acl_section, element_id, none_if_id_unused=False, id_description=None
):
    if tag not in TAG_DESCRIPTION_MAP.keys():
        raise AssertionError("Unknown acl tag '{0}'".format(tag))

    return find_element_by_tag_and_id(
        tag,
        acl_section,
        element_id,
        id_description=id_description if id_description
            else TAG_DESCRIPTION_MAP[tag]
        ,
        none_if_id_unused=none_if_id_unused,
    )

find_group = partial(find, TAG_GROUP)
find_role = partial(find, TAG_ROLE)
find_target = partial(find, TAG_TARGET)

def find_target_or_group(acl_section, target_or_group_id):
    """
    Returns acl_target or acl_group element with id target_or_group_id. Target
    element has bigger pririty so if there are target and group with same id
    only target element will be affected by this function.
    Raises LibraryError if there is no target or group element with
    specified id.

    acl_section -- cib etree node
    target_or_group_id -- id of target/group element which should be returned
    """
    target = find_target(
        acl_section,
        target_or_group_id,
        none_if_id_unused=True
    )

    if target is not None:
        return target

    return find_group(
        acl_section,
        target_or_group_id,
        id_description="user/group"
    )

def create_role(acl_section, role_id, description=None):
    """
    Create new role element and add it to cib.
    Returns newly created role element.

    role_id id of desired role
    description role description
    """
    check_new_id_applicable(acl_section, "ACL role", role_id)
    role = etree.SubElement(acl_section, TAG_ROLE, id=role_id)
    if description:
        role.set("description", description)
    return role


def remove_role(acl_section, role_id, autodelete_users_groups=False):
    """
    Remove role with specified id from CIB and all references to it.

    acl_section -- etree node
    role_id -- id of role to be removed
    autodelete_users_group -- if True remove targets with no role after removing
    """
    acl_role = find_role(acl_section, role_id)
    acl_role.getparent().remove(acl_role)
    for role_el in acl_section.findall(".//role[@id='{0}']".format(role_id)):
        role_parent = role_el.getparent()
        role_parent.remove(role_el)
        if autodelete_users_groups and role_parent.find(".//role") is None:
            role_parent.getparent().remove(role_parent)


def assign_role(acl_section, role_id, target_el):
    """
    Assign role element to specified target/group element.
    Raise LibraryError if role is already assigned to target/group.

    target_el -- etree element of target/group to which role should be assign
    role_el -- etree element of role
    """

    role_el = find_role(acl_section, role_id)
    assigned_role = target_el.find(
        "./role[@id='{0}']".format(role_el.get("id"))
    )
    if assigned_role is not None:
        raise LibraryError(reports.acl_role_is_already_assigned_to_target(
            role_el.get("id"), target_el.get("id")
        ))
    etree.SubElement(target_el, "role", {"id": role_el.get("id")})


def assign_all_roles(acl_section, role_id_list, element):
    """
    Assign roles from role_id_list to element.
    Raises LibraryError on any failure.

    acl_section -- cib etree node
    element -- element to which specified roles should be assigned
    role_id_list -- list of role id
    """
    for role_id in role_id_list:
        assign_role(acl_section, role_id, element)


def unassign_role(target_el, role_id, autodelete_target=False):
    """
    Unassign role with role_id from specified target/user target_el.
    Raise LibraryError if role is not assigned to target/group.

    target_el -- etree element of target/group from which role should be
        unassign
    role_id -- id of role
    autodelete_target -- if True remove target_el if there is no role assigned
    """
    assigned_role = target_el.find("./role[@id='{0}']".format(role_id))
    if assigned_role is None:
        raise LibraryError(reports.acl_role_is_not_assigned_to_target(
            role_id, target_el.get("id")
        ))
    target_el.remove(assigned_role)
    if autodelete_target and target_el.find("./role") is None:
        target_el.getparent().remove(target_el)


def provide_role(acl_section, role_id):
    """
    Returns role with id role_id. If doesn't exist, it will be created.
    role_id id of desired role
    """
    role = find_role(acl_section, role_id, none_if_id_unused=True)
    return role if role is not None else create_role(acl_section, role_id)


def create_target(acl_section, target_id):
    """
    Creates new acl_target element with id target_id.
    Raises LibraryError if target with wpecified id aleready exists.

    acl_section -- etree node
    target_id -- id of new target
    """
    # id of element acl_target is not type ID in CIB ACL schema so we don't need
    # to check if it is unique ID in whole CIB
    if(
        acl_section.find("./{0}[@id='{1}']".format(TAG_TARGET, target_id))
        is not None
    ):
        raise LibraryError(reports.acl_target_already_exists(target_id))
    return etree.SubElement(acl_section, TAG_TARGET, id=target_id)


def create_group(acl_section, group_id):
    """
    Creates new acl_group element with specified id.
    Raises LibraryError if tree contains element with id group_id.

    acl_section -- etree node
    group_id -- id of new group
    """
    check_new_id_applicable(acl_section, "ACL group", group_id)
    return etree.SubElement(acl_section, TAG_GROUP, id=group_id)


def remove_target(acl_section, target_id):
    """
    Removes acl_target element from acl_section with specified id.
    Raises LibraryError if target with id target_id doesn't exist.

    acl_section -- etree node
    target_id -- id of target element to remove
    """
    target = find_target(acl_section, target_id)
    target.getparent().remove(target)


def remove_group(acl_section, group_id):
    """
    Removes acl_group element from tree with specified id.
    Raises LibraryError if group with id group_id doesn't exist.

    acl_section -- etree node
    group_id -- id of group element to remove
    """
    group = find_group(acl_section, group_id)
    group.getparent().remove(group)


def add_permissions_to_role(role_el, permission_info_list):
    """
    Add permissions from permission_info_list to role_el.

    role_el -- acl_role element to which permissions should be added
    permission_info_list -- list of tuples,
        each contains (permission, scope_type, scope)
    """
    area_type_attribute_map = {
        'xpath': 'xpath',
        'id': 'reference',
    }
    for permission, scope_type, scope in permission_info_list:
        perm = etree.SubElement(role_el, "acl_permission")
        perm.set(
            "id",
            find_unique_id(
                role_el,
                "{0}-{1}".format(role_el.get("id", "role"), permission)
            )
        )
        perm.set("kind", permission)
        perm.set(area_type_attribute_map[scope_type], scope)


def remove_permission(acl_section, permission_id):
    """
    Remove permission with id permission_id from acl_section.

    acl_section -- etree node
    permission_id -- id of permission element to be removed
    """
    permission = find(TAG_PERMISSION, acl_section, permission_id)
    permission.getparent().remove(permission)


def get_role_list(acl_section):
    """
    Returns list of all acl_role elements from acl_section.
    Format of items of output list:
        {
            "id": <role-id>,
            "description": <role-description>,
            "permission_list": [<see function _get_all_permission_list>, ...]
        }

    acl_section -- etree node
    """
    output_list = []
    for role_el in acl_section.findall("./{0}".format(TAG_ROLE)):
        role = etree_element_attibutes_to_dict(
            role_el, ["id", "description"]
        )
        role["permission_list"] = _get_permission_list(role_el)
        output_list.append(role)
    return output_list


def _get_permission_list(role_el):
    """
    Return list of all permissions of role element role_el.
    Format of item of output list (if attribute is misssing in element under its
    key there is None):
        {
            "id": <id of permission element>,
            "description": <permission description>,
            "kind": <read|write|deny>,
            "xpath": <xpath string>,
            "reference": <cib element id>,
            "object-type": <>,
            "attribute": <>,
        }

    role_el -- acl_role etree element of which permissions whould be returned
    """
    output_list = []
    for permission in role_el.findall("./acl_permission"):
        output_list.append(etree_element_attibutes_to_dict(
            permission,
            [
                "id", "description", "kind", "xpath", "reference",
                "object-type", "attribute"
            ]
        ))
    return output_list


def get_target_list(acl_section):
    """
    Returns list of acl_target elements in format:
        {
            "id": <target id>,
            "role_list": [<assign role_id as string>, ...]
        }

    acl_section -- etree node
    """
    return get_target_like_list(acl_section, TAG_TARGET)


def get_group_list(acl_section):
    """
    Returns list of acl_group elements in format:
        {
            "id": <group id>,
            "role_list": [<assign role_id as string>, ...]
        }

    acl_section -- etree node
    """
    return get_target_like_list(acl_section, TAG_GROUP)


def get_target_like_list(acl_section, tag):
    output_list = []
    for target_el in acl_section.findall("./{0}".format(tag)):
        output_list.append({
            "id": target_el.get("id"),
            "role_list": _get_role_list_of_target(target_el),
        })
    return output_list


def _get_role_list_of_target(target):
    """
    Returns all roles assigned to target element as list of strings.

    target -- etree acl_target/acl_group element of which roles should be
        returned
    """
    return [
        role.get("id") for role in target.findall("./role") if role.get("id")
    ]


def remove_permissions_referencing(tree, reference):
    """
    Removes all permission with specified reference.

    tree -- etree node
    reference -- reference identifier
    """
    xpath = './/acl_permission[@reference="{0}"]'.format(reference)
    for permission in tree.findall(xpath):
        permission.getparent().remove(permission)


def dom_remove_permissions_referencing(dom, reference):
    # TODO: remove once we go fully lxml
    for permission in dom.getElementsByTagName("acl_permission"):
        if permission.getAttribute("reference") == reference:
            permission.parentNode.removeChild(permission)
