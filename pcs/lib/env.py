from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from lxml import etree
import os.path
import tempfile

from pcs import settings
from pcs.lib import reports
from pcs.lib.booth.env import BoothEnv
from pcs.lib.cluster_conf_facade import ClusterConfFacade
from pcs.lib.corosync.config_facade import ConfigFacade as CorosyncConfigFacade
from pcs.lib.corosync.live import (
    exists_local_corosync_conf,
    get_local_corosync_conf,
    get_local_cluster_conf,
    reload_config as reload_corosync_config,
)
from pcs.lib.external import (
    is_cman_cluster,
    is_service_running,
    CommandRunner,
    NodeCommunicator,
)
from pcs.lib.errors import LibraryError
from pcs.lib.nodes_task import (
    distribute_corosync_conf,
    check_corosync_offline_on_nodes,
    qdevice_reload_on_nodes,
)
from pcs.lib.pacemaker.live import (
    ensure_wait_for_idle_support,
    ensure_cib_version,
    get_cib,
    get_cib_xml,
    replace_cib_configuration_xml,
    wait_for_idle,
    get_cluster_status_xml,
)
from pcs.lib.pacemaker.state import get_cluster_state_dom
from pcs.lib.pacemaker.values import get_valid_timeout_seconds


class LibraryEnvironment(object):
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        logger,
        report_processor,
        user_login=None,
        user_groups=None,
        cib_data=None,
        corosync_conf_data=None,
        booth=None,
        auth_tokens_getter=None,
        cluster_conf_data=None,
    ):
        self._logger = logger
        self._report_processor = report_processor
        self._user_login = user_login
        self._user_groups = [] if user_groups is None else user_groups
        self._cib_data = cib_data
        self._corosync_conf_data = corosync_conf_data
        self._cluster_conf_data = cluster_conf_data
        self._booth = (
            BoothEnv(report_processor, booth) if booth is not None else None
        )
        self._is_cman_cluster = None
        # TODO tokens probably should not be inserted from outside, but we're
        # postponing dealing with them, because it's not that easy to move
        # related code currently - it's in pcsd
        self._auth_tokens_getter = auth_tokens_getter
        self._auth_tokens = None
        self._cib_upgraded = False
        self._cib_data_tmp_file = None

        self.__timeout_cache = {}

    @property
    def logger(self):
        return self._logger

    @property
    def report_processor(self):
        return self._report_processor

    @property
    def user_login(self):
        return self._user_login

    @property
    def user_groups(self):
        return self._user_groups

    @property
    def is_cman_cluster(self):
        if self._is_cman_cluster is None:
            self._is_cman_cluster = is_cman_cluster(self.cmd_runner())
        return self._is_cman_cluster

    @property
    def cib_upgraded(self):
        return self._cib_upgraded

    def _get_cib_xml(self):
        if self.is_cib_live:
            return get_cib_xml(self.cmd_runner())
        else:
            return self._cib_data

    def get_cib(self, minimal_version=None):
        cib = get_cib(self._get_cib_xml())
        if minimal_version is not None:
            upgraded_cib = ensure_cib_version(
                self.cmd_runner(),
                cib,
                minimal_version
            )
            if upgraded_cib is not None:
                cib = upgraded_cib
                if self.is_cib_live and not self._cib_upgraded:
                    self.report_processor.process(
                        reports.cib_upgrade_successful()
                    )
                self._cib_upgraded = True
        return cib

    def get_cluster_state(self):
        return get_cluster_state_dom(get_cluster_status_xml(self.cmd_runner()))

    def _push_cib_xml(self, cib_data):
        if self.is_cib_live:
            replace_cib_configuration_xml(self.cmd_runner(), cib_data)
            self._cib_upgraded = False
        else:
            self._cib_data = cib_data

    def _get_wait_timeout(self, wait):
        if wait is False:
            return False

        if wait not in self.__timeout_cache:
            if not self.is_cib_live:
                raise LibraryError(reports.wait_for_idle_not_live_cluster())
            ensure_wait_for_idle_support(self.cmd_runner())
            self.__timeout_cache[wait] = get_valid_timeout_seconds(wait)
        return self.__timeout_cache[wait]


    def ensure_wait_satisfiable(self, wait):
        """
        Raise when wait is not supported or when wait is not valid wait value.

        mixed wait can be False when waiting is not required or valid timeout
        """
        self._get_wait_timeout(wait)

    def push_cib(self, cib, wait=False):
        timeout = self._get_wait_timeout(wait)
        #etree returns bytes: b'xml'
        #python 3 removed .encode() from bytes
        #run(...) calls subprocess.Popen.communicate which calls encode...
        #so here is bytes to str conversion
        self._push_cib_xml(etree.tostring(cib).decode())

        if timeout is not False:
            wait_for_idle(self.cmd_runner(), timeout)

    @property
    def is_cib_live(self):
        return self._cib_data is None

    def get_corosync_conf_data(self):
        if self._corosync_conf_data is None:
            return get_local_corosync_conf()
        else:
            return self._corosync_conf_data

    def get_corosync_conf(self):
        return CorosyncConfigFacade.from_string(self.get_corosync_conf_data())

    def push_corosync_conf(
        self, corosync_conf_facade, skip_offline_nodes=False
    ):
        corosync_conf_data = corosync_conf_facade.config.export()
        if self.is_corosync_conf_live:
            node_list = corosync_conf_facade.get_nodes()
            if corosync_conf_facade.need_stopped_cluster:
                check_corosync_offline_on_nodes(
                    self.node_communicator(),
                    self.report_processor,
                    node_list,
                    skip_offline_nodes
                )
            distribute_corosync_conf(
                self.node_communicator(),
                self.report_processor,
                node_list,
                corosync_conf_data,
                skip_offline_nodes
            )
            if is_service_running(self.cmd_runner(), "corosync"):
                reload_corosync_config(self.cmd_runner())
                self.report_processor.process(
                    reports.corosync_config_reloaded()
                )
            if corosync_conf_facade.need_qdevice_reload:
                qdevice_reload_on_nodes(
                    self.node_communicator(),
                    self.report_processor,
                    node_list,
                    skip_offline_nodes
                )
        else:
            self._corosync_conf_data = corosync_conf_data


    def get_cluster_conf_data(self):
        if self.is_cluster_conf_live:
            return get_local_cluster_conf()
        else:
            return self._cluster_conf_data


    def get_cluster_conf(self):
        return ClusterConfFacade.from_string(self.get_cluster_conf_data())


    @property
    def is_cluster_conf_live(self):
        return self._cluster_conf_data is None


    def is_node_in_cluster(self):
        if self.is_cman_cluster:
            #TODO --cluster_conf is not propagated here. So no live check not
            #needed here. But this should not be permanently
            return os.path.exists(settings.corosync_conf_file)

        if not self.is_corosync_conf_live:
            raise AssertionError(
                "Cannot check if node is in cluster with mocked corosync_conf."
            )
        return exists_local_corosync_conf()

    def command_expect_live_corosync_env(self):
        # TODO get rid of cli knowledge
        if not self.is_corosync_conf_live:
            raise LibraryError(reports.live_environment_required([
                "--corosync_conf"
            ]))

    @property
    def is_corosync_conf_live(self):
        return self._corosync_conf_data is None

    def cmd_runner(self):
        runner_env = {
            # make sure to get output of external processes in English and ASCII
            "LC_ALL": "C",
        }

        if self.user_login:
            runner_env["CIB_user"] = self.user_login

        if not self.is_cib_live:
            # Dump CIB data to a temporary file and set it up in the runner.
            # This way every called pacemaker tool can access the CIB and we
            # don't need to take care of it every time the runner is called.
            if not self._cib_data_tmp_file:
                try:
                    self._cib_data_tmp_file = tempfile.NamedTemporaryFile(
                        "w+",
                        suffix=".pcs"
                    )
                    self._cib_data_tmp_file.write(self._get_cib_xml())
                    self._cib_data_tmp_file.flush()
                except EnvironmentError as e:
                    raise LibraryError(reports.cib_save_tmp_error(str(e)))
            runner_env["CIB_file"] = self._cib_data_tmp_file.name

        return CommandRunner(self.logger, self.report_processor, runner_env)

    def node_communicator(self):
        return NodeCommunicator(
            self.logger,
            self.report_processor,
            self.__get_auth_tokens(),
            self.user_login,
            self.user_groups
        )

    def __get_auth_tokens(self):
        if self._auth_tokens is None:
            if self._auth_tokens_getter:
                self._auth_tokens = self._auth_tokens_getter()
            else:
                self._auth_tokens = {}
        return self._auth_tokens

    @property
    def booth(self):
        return self._booth
