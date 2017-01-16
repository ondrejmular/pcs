from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import re
from lxml import etree

from pcs.lib import reports
from pcs.lib.errors import LibraryError
from pcs.lib.pacemaker.values import validate_id

def get_root(tree):
    # ElementTree has getroot, Elemet has getroottree
    return tree.getroot() if hasattr(tree, "getroot") else tree.getroottree()

def does_id_exist(tree, check_id):
    """
    Checks to see if id exists in the xml dom passed
    tree cib etree node
    check_id id to check
    """

    # do not search in /cib/status, it may contain references to previously
    # existing and deleted resources and thus preventing creating them again
    existing = get_root(tree).xpath(
        (
            '(/cib/*[name()!="status"]|/*[name()!="cib"])'
            '//*[name()!="acl_target" and name()!="role" and @id="{0}"]'
        ).format(check_id)
    )
    return len(existing) > 0

def validate_id_does_not_exist(tree, id):
    """
    tree cib etree node
    """
    if does_id_exist(tree, id):
        raise LibraryError(reports.id_already_exists(id))

def find_unique_id(tree, check_id):
    """
    Returns check_id if it doesn't exist in the dom, otherwise it adds
    an integer to the end of the id and increments it until a unique id is found
    tree cib etree node
    check_id id to check
    """
    counter = 1
    temp_id = check_id
    while does_id_exist(tree, temp_id):
        temp_id = "{0}-{1}".format(check_id, counter)
        counter += 1
    return temp_id

def create_subelement_id(context_element, suffix):
    return find_unique_id(
        context_element,
        "{0}-{1}".format(context_element.get("id"), suffix)
    )

def check_new_id_applicable(tree, description, id):
    validate_id(id, description)
    validate_id_does_not_exist(tree, id)

def _get_mandatory_section(tree, section_name):
    """
    Return required element from tree, raise LibraryError if missing
    tree cib etree node
    """
    section = tree.find(".//{0}".format(section_name))
    if section is not None:
        return section
    raise LibraryError(reports.cib_missing_mandatory_section(section_name))

def get_configuration(tree):
    """
    Return 'configuration' element from tree, raise LibraryError if missing
    tree cib etree node
    """
    return _get_mandatory_section(tree, "configuration")

def get_acls(tree):
    """
    Return 'acls' element from tree, create a new one if missing
    tree cib etree node
    """
    return get_sub_element(get_configuration(tree), "acls")

def get_alerts(tree):
    """
    Return 'alerts' element from tree, create a new one if missing
    tree -- cib etree node
    """
    return get_sub_element(get_configuration(tree), "alerts")

def get_constraints(tree):
    """
    Return 'constraint' element from tree
    tree cib etree node
    """
    return _get_mandatory_section(tree, "configuration/constraints")

def get_fencing_topology(tree):
    """
    Return the 'fencing-topology' element from the tree
    tree -- cib etree node
    """
    return get_sub_element(get_configuration(tree), "fencing-topology")

def get_nodes(tree):
    """
    Return 'nodes' element from the tree
    tree cib etree node
    """
    return _get_mandatory_section(tree, "configuration/nodes")

def get_resources(tree):
    """
    Return the 'resources' element from the tree
    tree -- cib etree node
    """
    return _get_mandatory_section(tree, "configuration/resources")

def find_parent(element, tag_names):
    candidate = element
    while True:
        if candidate is None or candidate.tag in tag_names:
            return candidate
        candidate = candidate.getparent()

def export_attributes(element):
    return  dict((key, value) for key, value in element.attrib.items())

def get_sub_element(element, sub_element_tag, new_id=None, new_index=None):
    """
    Returns the FIRST sub-element sub_element_tag of element. It will create new
    element if such doesn't exist yet. Id of new element will be new_id if
    it's not None. new_index specify where will be new element added, if None
    it will be appended.

    element -- parent element
    sub_element_tag -- tag of wanted element
    new_id -- id of new element
    new_index -- index for new element
    """
    sub_element = element.find("./{0}".format(sub_element_tag))
    if sub_element is None:
        sub_element = etree.Element(sub_element_tag)
        if new_id:
            sub_element.set("id", new_id)
        if new_index is None:
            element.append(sub_element)
        else:
            element.insert(new_index, sub_element)
    return sub_element

def get_pacemaker_version_by_which_cib_was_validated(cib):
    """
    Return version of pacemaker which validated specified cib as tree.
    Version is returned as tuple of integers: (<major>, <minor>, <revision>).
    Raises LibraryError on any failure.

    cib -- cib etree
    """
    version = cib.get("validate-with")
    if version is None:
        raise LibraryError(reports.cib_load_error_invalid_format())

    regexp = re.compile(
        r"pacemaker-(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<rev>\d+))?"
    )
    match = regexp.match(version)
    if not match:
        raise LibraryError(reports.cib_load_error_invalid_format())
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("rev") or 0)
    )

def etree_element_attibutes_to_dict(etree_el, required_key_list):
    """
    Returns all attributes of etree_el from required_key_list in dictionary,
    where keys are attributes and values are values of attributes or None if
    it's not present.

    etree_el -- etree element from which attributes should be extracted
    required_key_list -- list of strings, attributes names which should be
        extracted
    """
    return dict([(key, etree_el.get(key)) for key in required_key_list])
