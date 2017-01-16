# Change Log

## [Unreleased]

### Added
- Fencing levels now may be targeted in CLI by a node name pattern or a node
  attribute in addition to a node name ([rhbz#1261116])

### Changed
- `pcs node [un]standby` and `pcs node [un]maintenance` is now atomic even if
  more than one node is specified ([rhbz#1315992])
- Restarting pcsd initiated from pcs is now a synchronous operation
  ([rhbz#1284404])
- Stopped bundling fonts used in pcsd GUI ([ghissue#125])
- In `pcs resource create` flags `--master` and `--clone` changed to keywords
  `master` and `clone`

### Fixed
- When upgrading CIB to the latest schema version, check for minimal common
  version across the cluster ([rhbz#1389443])
- `pcs booth remove` now works correctly even if the booth resource group is
  disabled ([rhbz#1389941])
- Adding a node in a CMAN cluster does not cause the new node to be fenced
  immediately ([rhbz#1394846])
- Show proper error message when there is an HTTP communication failure
  ([rhbz#1394273])
- Fixed searching for files to remove in the `/var/lib` directory ([ghpull#119],
  [ghpull#120])
- Fixed messages when managing services (start, stop, enable, disable...)
- Fixed disabling services on systemd systems when using instances
  ([rhbz#1389501])
- Fixed parsing commandline options ([rhbz#1404229])
- Pcs does not exit with a false error message anymore when pcsd-cli.rb outputs
  to stderr ([ghissue#124])
- Fixed searching for files to remove in the `/var/lib` directory ([ghpull#119])
- In `pcs resource create` the flag `--clone` no longer steals arguments from
  the keywords `meta` and `op` ([rhbz#1395226])
- `pcs resource create` does not produce invalid cib when group id is already
  occupied with non-resource element ([rhbz#1382004])
- Fixed misbehavior of the flag `--master` in `pcs resource create` command
  ([rhbz#1378107])
- Fixed tacit acceptance of invalid resource operation in `pcs resource create`
  ([rhbz#1398562])
- Fixed misplacing metadata for disabling when running `pcs resource create`
  with flags `--clone` and `--disabled` ([rhbz#1402475])
- Fixed incorrect acceptance of the invalid attribute of resource operation in
  `pcs resource create` ([rhbz#1382597])
- Fixed validation of options of resource operations in `pcs resource create`
  ([rhbz#1390071])
- Fixed silent omission of duplicate options ([rhbz#1390066])

[ghissue#124]: https://github.com/ClusterLabs/pcs/issues/124
[ghissue#125]: https://github.com/ClusterLabs/pcs/issues/125
[ghpull#119]: https://github.com/ClusterLabs/pcs/pull/119
[ghpull#120]: https://github.com/ClusterLabs/pcs/pull/120
[rhbz#1261116]: https://bugzilla.redhat.com/show_bug.cgi?id=1261116
[rhbz#1284404]: https://bugzilla.redhat.com/show_bug.cgi?id=1284404
[rhbz#1315992]: https://bugzilla.redhat.com/show_bug.cgi?id=1315992
[rhbz#1378107]: https://bugzilla.redhat.com/show_bug.cgi?id=1378107
[rhbz#1382004]: https://bugzilla.redhat.com/show_bug.cgi?id=1382004
[rhbz#1382597]: https://bugzilla.redhat.com/show_bug.cgi?id=1382597
[rhbz#1389443]: https://bugzilla.redhat.com/show_bug.cgi?id=1389443
[rhbz#1389501]: https://bugzilla.redhat.com/show_bug.cgi?id=1389501
[rhbz#1389941]: https://bugzilla.redhat.com/show_bug.cgi?id=1389941
[rhbz#1390066]: https://bugzilla.redhat.com/show_bug.cgi?id=1390066
[rhbz#1390071]: https://bugzilla.redhat.com/show_bug.cgi?id=1390071
[rhbz#1394273]: https://bugzilla.redhat.com/show_bug.cgi?id=1394273
[rhbz#1394846]: https://bugzilla.redhat.com/show_bug.cgi?id=1394846
[rhbz#1395226]: https://bugzilla.redhat.com/show_bug.cgi?id=1395226
[rhbz#1398562]: https://bugzilla.redhat.com/show_bug.cgi?id=1398562
[rhbz#1402475]: https://bugzilla.redhat.com/show_bug.cgi?id=1402475
[rhbz#1404229]: https://bugzilla.redhat.com/show_bug.cgi?id=1404229


## [0.9.155] - 2016-11-03

### Added
- Show daemon status in `pcs status` on non-systemd machines
- SBD support for cman clusters ([rhbz#1380352])
- Alerts management in pcsd ([rhbz#1376480])

### Changed
- Get all information about resource and stonith agents from pacemaker. Pcs now
  supports the same set of agents as pacemaker does. ([rhbz#1262001],
  [ghissue#81])
- `pcs resource create` now exits with an error if more than one resource agent
  matches the specified short agent name instead of randomly selecting one of
  the agents
- Allow to remove multiple alerts and alert recipients at once

### Fixed
- When stopping a cluster with some of the nodes unreachable, stop the cluster
  completely on all reachable nodes ([rhbz#1380372])
- Fixed pcsd crash when rpam rubygem is installed ([ghissue#109])
- Fixed occasional crashes / failures when using locale other than en\_US.UTF8
  ([rhbz#1387106])
- Fixed starting and stopping cluster services on systemd machines without
  the `service` executable ([ghissue#115])


[ghissue#81]: https://github.com/ClusterLabs/pcs/issues/81
[ghissue#109]: https://github.com/ClusterLabs/pcs/issues/109
[ghissue#115]: https://github.com/ClusterLabs/pcs/issues/115
[rhbz#1262001]: https://bugzilla.redhat.com/show_bug.cgi?id=1262001
[rhbz#1376480]: https://bugzilla.redhat.com/show_bug.cgi?id=1376480
[rhbz#1380352]: https://bugzilla.redhat.com/show_bug.cgi?id=1380352
[rhbz#1380372]: https://bugzilla.redhat.com/show_bug.cgi?id=1380372
[rhbz#1387106]: https://bugzilla.redhat.com/show_bug.cgi?id=1387106


## [0.9.154] - 2016-09-21
- There is no change log for this and previous releases. We are sorry.
- Take a look at git history if you are interested.
