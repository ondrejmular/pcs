from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from lxml import etree

from pcs.common import report_codes
from pcs.lib.errors import LibraryError, ReportItem
from pcs.lib.cib.tools import (
    does_id_exist,
    find_unique_id,
    get_acls,
    check_new_id_applicable,
)

class AclRoleNotFound(LibraryError):
    pass

def __validate_permissions(tree, permission_info_list):
    report = []
    allowed_permissions = ["read", "write", "deny"]
    allowed_scopes = ["xpath", "id"]
    for permission, scope_type, scope in permission_info_list:
        if not permission in allowed_permissions:
            report.append(ReportItem.error(
                report_codes.BAD_ACL_PERMISSION,
                'bad permission "{permission}, expected {allowed_values}',
                info={
                    'permission': permission,
                    'allowed_values_raw': allowed_permissions,
                    'allowed_values': ' or '.join(allowed_permissions)
                },
            ))

        if not scope_type in allowed_scopes:
            report.append(ReportItem.error(
                report_codes.BAD_ACL_SCOPE_TYPE,
                'bad scope type "{scope_type}, expected {allowed_values}',
                info={
                    'scope_type': scope_type,
                    'allowed_values_raw': allowed_scopes,
                    'allowed_values': ' or '.join(allowed_scopes)
                },
            ))

        if scope_type == 'id' and not does_id_exist(tree, scope):
            report.append(ReportItem.error(
                report_codes.ID_NOT_FOUND,
                'id "{id}" does not exist.',
                info={'id': scope },
            ))

    if report:
        raise LibraryError(*report)

def __find_role(tree, role_id):
    role = tree.find('.//acl_role[@id="{0}"]'.format(role_id))
    if role is not None:
        return role
    raise AclRoleNotFound(ReportItem.error(
        report_codes.ACL_ROLE_NOT_FOUND,
        'role id "{role_id}" does not exist.',
        info={'role_id': role_id},
    ))

def create_role(tree, role_id, description=""):
    """
    role_id id of desired role
    description role description
    """
    check_new_id_applicable(tree, "ACL role", role_id)
    role = etree.SubElement(get_acls(tree), "acl_role", id=role_id)
    if description:
        role.set("description", description)

def provide_role(tree, role_id):
    """
    role_id id of desired role
    description role description
    """
    try:
        __find_role(tree, role_id)
    except AclRoleNotFound:
        create_role(tree, role_id)

def add_permissions_to_role(tree, role_id, permission_info_list):
    """
    tree etree node
    role_id value of atribute id, which exists in dom
    permission_info_list list of tuples,
        each contains (permission, scope_type, scope)
    """
    __validate_permissions(tree, permission_info_list)

    area_type_attribute_map = {
        'xpath': 'xpath',
        'id': 'reference',
    }
    for permission, scope_type, scope in permission_info_list:
        perm = etree.SubElement(__find_role(tree, role_id), "acl_permission")
        perm.set(
            "id",
            find_unique_id(tree, "{0}-{1}".format(role_id, permission))
        )
        perm.set("kind", permission)
        perm.set(area_type_attribute_map[scope_type], scope)

def remove_permissions_referencing(tree, reference):
    xpath = './/acl_permission[@reference="{0}"]'.format(reference)
    for permission in tree.findall(xpath):
        permission.getparent().remove(permission)

def dom_remove_permissions_referencing(dom, reference):
    # TODO: remove once we go fully lxml
    for permission in dom.getElementsByTagName("acl_permission"):
        if permission.getAttribute("reference") == reference:
            permission.parentNode.removeChild(permission)
