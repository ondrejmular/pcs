from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from contextlib import contextmanager
from functools import partial

from pcs.lib.cib import resource
from pcs.lib.cib.resource.common import (
    disable_meta,
    are_meta_disabled,
    are_clone_meta_disabled
)
from pcs.lib.cib.tools import get_resources
from pcs.lib.pacemaker.values import validate_id
from pcs.lib.pacemaker.state import ensure_resource_state

@contextmanager
def cib_resources_section(env, resource_id, wait, disabled_after_wait):
    env.ensure_wait_satisfiable(wait)
    cib = env.get_cib()
    yield get_resources(cib)
    env.push_cib(cib, wait)
    if wait is not False:
        ensure_resource_state(
            not disabled_after_wait,
            env.report_processor,
            env.get_cluster_state(),
            resource_id
        )

def create(
    env, resource_id, resource_agent_name,
    operations, meta_attributes, instance_attributes,
    allow_absent_agent=False,
    allow_invalid_operation=False,
    allow_invalid_instance_attributes=False,
    use_default_operations=True,
    ensure_disabled=False,
    wait=False,
):
    with cib_resources_section(
        env, resource_id, wait,
        ensure_disabled or are_meta_disabled(meta_attributes)
    ) as resources_section:
        resource.primitive.create(
            env.report_processor, env.cmd_runner(), resources_section,
            resource_id, resource_agent_name,
            operations, meta_attributes, instance_attributes,
            allow_absent_agent,
            allow_invalid_operation,
            allow_invalid_instance_attributes,
            use_default_operations,
            ensure_disabled,
        )

def _create_as_clone_common(
    tag, env, resource_id, resource_agent_name,
    operations, meta_attributes, instance_attributes, clone_meta_options,
    allow_absent_agent=False,
    allow_invalid_operation=False,
    allow_invalid_instance_attributes=False,
    use_default_operations=True,
    ensure_disabled=False,
    wait=False,
):
    """
    Create resource in some kind of clone (clone or master).
    Currently the only difference between commands "create_as_clone" and
    "create_as_master" is in tag. So the commands create_as_clone and
    create_as_master are created by passing tag with partial.

    """
    with cib_resources_section(env, resource_id, wait, (
            ensure_disabled
            or
            are_meta_disabled(meta_attributes)
            or
            are_clone_meta_disabled(clone_meta_options)
    )) as resources_section:
        primitive_element = resource.primitive.create(
            env.report_processor, env.cmd_runner(), resources_section,
            resource_id, resource_agent_name,
            operations, meta_attributes, instance_attributes,
            allow_absent_agent,
            allow_invalid_operation,
            allow_invalid_instance_attributes,
            use_default_operations,
        )

        if ensure_disabled:
            clone_meta_options = disable_meta(clone_meta_options)

        resource.clone.append_new(
            tag,
            resources_section,
            primitive_element,
            clone_meta_options,
        )

def create_in_group(
    env, resource_id, resource_agent_name, group_id,
    operations, meta_attributes, instance_attributes,
    allow_absent_agent=False,
    allow_invalid_operation=False,
    allow_invalid_instance_attributes=False,
    use_default_operations=True,
    ensure_disabled=False,
    adjacent_resource_id=None,
    put_after_adjacent=False,
    wait=False,
):
    with cib_resources_section(
        env, resource_id, wait,
        ensure_disabled or are_meta_disabled(meta_attributes)
    ) as resources_section:
        primitive_element = resource.primitive.create(
            env.report_processor, env.cmd_runner(), resources_section,
            resource_id, resource_agent_name,
            operations, meta_attributes, instance_attributes,
            allow_absent_agent,
            allow_invalid_operation,
            allow_invalid_instance_attributes,
            use_default_operations,
            ensure_disabled,
        )
        validate_id(group_id, "group name")
        resource.group.place_resource(
            resource.group.provide_group(resources_section, group_id),
            primitive_element,
            adjacent_resource_id,
            put_after_adjacent,
        )

create_as_clone = partial(_create_as_clone_common, resource.clone.TAG_CLONE)
create_as_master = partial(_create_as_clone_common, resource.clone.TAG_MASTER)
