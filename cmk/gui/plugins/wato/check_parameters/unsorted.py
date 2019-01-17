#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import re
import cmk.utils.defines as defines

from cmk.gui.plugins.wato.active_checks import check_icmp_params

import cmk.gui.mkeventd as mkeventd
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Tuple,
    Integer,
    Float,
    TextAscii,
    Age,
    DropdownChoice,
    Checkbox,
    RegExp,
    Filesize,
    Alternative,
    Percentage,
    ListChoice,
    Transform,
    ListOf,
    ListOfStrings,
    CascadingDropdown,
    FixedValue,
    Optional,
    MonitoringState,
    DualListChoice,
    RadioChoice,
    TextUnicode,
    RegExpUnicode,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    RulespecGroupCheckParametersHardware,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersOperatingSystem,
    RulespecGroupCheckParametersStorage,
    RulespecGroupCheckParametersVirtualization,
    register_rule,
    register_check_parameters,
    UserIconOrAction,
    Levels,
)
from cmk.gui.plugins.wato.check_parameters.ps import process_level_elements
from cmk.gui.plugins.wato.check_parameters.utils import (
    match_dual_level_type,
    get_free_used_dynamic_valuespec,
    transform_filesystem_free,
)

# TODO: Sort all rules and check parameters into the figlet header sections.
# Beware: there are dependencies, so sometimes the order matters.  All rules
# that are not yet handles are in the last section: in "Unsorted".  Move rules
# from there into their appropriate sections until "Unsorted" is empty.
# Create new rules directly in the correct secions.

#   .--Networking----------------------------------------------------------.
#   |        _   _      _                      _    _                      |
#   |       | \ | | ___| |___      _____  _ __| | _(_)_ __   __ _          |
#   |       |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / | '_ \ / _` |         |
#   |       | |\  |  __/ |_ \ V  V / (_) | |  |   <| | | | | (_| |         |
#   |       |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\_|_| |_|\__, |         |
#   |                                                       |___/          |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersNetworking,
    "ping_levels",
    Dictionary(
        title=_("PING and host check parameters"),
        help=_("This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
               "and also for PING checks on ping-only-hosts. For the host checks only the "
               "critical state is relevant, the warning levels are ignored."),
        elements=check_icmp_params,
    ),
    match="dict")

#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'


def transform_ipmi_inventory_rules(p):
    if not isinstance(p, dict):
        return p
    if p.get("summarize", True):
        return 'summarize'
    if p.get('ignored_sensors', []):
        return ('single', {'ignored_sensors': p["ignored_sensors"]})
    return ('single', {})


register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_ipmi_rules",
    title=_("Discovery of IPMI sensors"),
    valuespec=Transform(
        CascadingDropdown(
            orientation="vertical",
            choices=
            [("summarize", _("Summary")),
             ("single", _("Single"),
              Dictionary(
                  show_titles=True,
                  elements=[
                      ("ignored_sensors",
                       ListOfStrings(
                           title=_("Ignore the following IPMI sensors"),
                           help=_("Names of IPMI sensors that should be ignored during inventory "
                                  "and when summarizing."
                                  "The pattern specified here must match exactly the beginning of "
                                  "the actual sensor name (case sensitive)."),
                           orientation="horizontal")),
                      ("ignored_sensorstates",
                       ListOfStrings(
                           title=_("Ignore the following IPMI sensor states"),
                           help=_(
                               "IPMI sensors with these states that should be ignored during inventory "
                               "and when summarizing."
                               "The pattern specified here must match exactly the beginning of "
                               "the actual sensor name (case sensitive)."),
                           orientation="horizontal",
                       )),
                  ]))]),
        forth=transform_ipmi_inventory_rules),
    match='first')

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="ewon_discovery_rules",
    title=_("eWON Discovery"),
    help=_("The ewon vpn routers can rely data from a secondary device via snmp. "
           "It doesn't however allow discovery of the device type relayed this way. "
           "To allow interpretation of the data you need to pick the device manually."),
    valuespec=DropdownChoice(
        title=_("Device Type"),
        label=_("Select device type"),
        choices=[
            (None, _("None selected")),
            ("oxyreduct", _("Wagner OxyReduct")),
        ],
        default_value=None,
    ),
    match='first')

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="mssql_transactionlogs_discovery",
    title=_("MSSQL Datafile and Transactionlog Discovery"),
    valuespec=Dictionary(
        elements=[
            ("summarize_datafiles",
             Checkbox(
                 title=_("Display only a summary of all Datafiles"),
                 label=_("Summarize Datafiles"),
             )),
            ("summarize_transactionlogs",
             Checkbox(
                 title=_("Display only a summary of all Transactionlogs"),
                 label=_("Summarize Transactionlogs"),
             )),
        ],
        optional_keys=[]),
    match="first")

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_services_rules",
    title=_("Windows Service Discovery"),
    valuespec=Dictionary(
        elements=[
            ('services',
             ListOfStrings(
                 title=_("Services (Regular Expressions)"),
                 help=_('Regular expressions matching the begining of the internal name '
                        'or the description of the service. '
                        'If no name is given then this rule will match all services. The '
                        'match is done on the <i>beginning</i> of the service name. It '
                        'is done <i>case sensitive</i>. You can do a case insensitive match '
                        'by prefixing the regular expression with <tt>(?i)</tt>. Example: '
                        '<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> '
                        'or <tt>MsSQL</tt> or <tt>mssql</tt> or...'),
                 orientation="horizontal",
             )),
            ('state',
             DropdownChoice(
                 choices=[
                     ('running', _('Running')),
                     ('stopped', _('Stopped')),
                 ],
                 title=_("Create check if service is in state"),
             )),
            ('start_mode',
             DropdownChoice(
                 choices=[
                     ('auto', _('Automatic')),
                     ('demand', _('Manual')),
                     ('disabled', _('Disabled')),
                 ],
                 title=_("Create check if service is in start mode"),
             )),
        ],
        help=_(
            'This rule can be used to configure the inventory of the windows services check. '
            'You can configure specific windows services to be monitored by the windows check by '
            'selecting them by name, current state during the inventory, or start mode.'),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_solaris_services_rules",
    title=_("Solaris Service Discovery"),
    valuespec=Dictionary(
        elements=[
            ('descriptions', ListOfStrings(title=_("Descriptions"))),
            ('categories', ListOfStrings(title=_("Categories"))),
            ('names', ListOfStrings(title=_("Names"))),
            ('instances', ListOfStrings(title=_("Instances"))),
            ('states',
             ListOf(
                 DropdownChoice(
                     choices=[
                         ("online", _("online")),
                         ("disabled", _("disabled")),
                         ("maintenance", _("maintenance")),
                         ("legacy_run", _("legacy run")),
                     ],),
                 title=_("States"),
             )),
            ('outcome',
             Alternative(
                 title=_("Service name"),
                 style="dropdown",
                 elements=[
                     FixedValue("full_descr", title=_("Full Description"), totext=""),
                     FixedValue(
                         "descr_without_prefix",
                         title=_("Description without type prefix"),
                         totext=""),
                 ],
             )),
        ],
        help=_(
            'This rule can be used to configure the discovery of the Solaris services check. '
            'You can configure specific Solaris services to be monitored by the Solaris check by '
            'selecting them by description, category, name, or current state during the discovery.'
        ),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="discovery_systemd_units_services_rules",
    title=_("Systemd Service Discovery"),
    valuespec=Dictionary(
        elements=[
            ('descriptions', ListOfStrings(title=_("Descriptions"))),
            ('names', ListOfStrings(title=_("Service unit names"))),
            ('states',
             ListOf(
                 DropdownChoice(
                     choices=[
                         ("active", "active"),
                         ("inactive", "inactive"),
                         ("failed", "failed"),
                     ],),
                 title=_("States"),
             )),
        ],
        help=_('This rule can be used to configure the discovery of the Linux services check. '
               'You can configure specific Linux services to be monitored by the Linux check by '
               'selecting them by description, unit name, or current state during the discovery.'),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="discovery_win_dhcp_pools",
    title=_("Discovery of Windows DHCP Pools"),
    valuespec=Dictionary(elements=[
        ("empty_pools",
         Checkbox(
             title=_("Discovery of empty DHCP pools"),
             label=_("Include empty pools into the monitoring"),
             help=_("You can activate the creation of services for "
                    "DHCP pools, which contain no IP addresses."),
         )),
    ]),
    match='dict',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_if_rules",
    title=_("Network Interface and Switch Port Discovery"),
    valuespec=Dictionary(
        elements=[
            ("use_desc",
             DropdownChoice(
                 choices=[
                     (True, _('Use description')),
                     (False, _('Do not use description')),
                 ],
                 title=_("Description as service name for network interface checks"),
                 help=_(
                     "This option lets Check_MK use the interface description as item instead "
                     "of the port number. If no description is available then the port number is "
                     "used anyway."))),
            ("use_alias",
             DropdownChoice(
                 choices=[
                     (True, _('Use alias')),
                     (False, _('Do not use alias')),
                 ],
                 title=_("Alias as service name for network interface checks"),
                 help=_(
                     "This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                     "of the port number. If no alias is available then the port number is used "
                     "anyway."))),
            ("pad_portnumbers",
             DropdownChoice(
                 choices=[
                     (True, _('Pad port numbers with zeros')),
                     (False, _('Do not pad')),
                 ],
                 title=_("Port numbers"),
                 help=_("If this option is activated then Check_MK will pad port numbers of "
                        "network interfaces with zeroes so that all port descriptions from "
                        "all ports of a host or switch have the same length and thus sort "
                        "currectly in the GUI. In versions prior to 1.1.13i3 there was no "
                        "padding. You can switch back to the old behaviour by disabling this "
                        "option. This will retain the old service descriptions and the old "
                        "performance data."),
             )),
            ("match_alias",
             ListOfStrings(
                 title=_("Match interface alias (regex)"),
                 help=_("Only discover interfaces whose alias matches one of the configured "
                        "regular expressions. The match is done on the beginning of the alias. "
                        "This allows you to select interfaces based on the alias without having "
                        "the alias be part of the service description."),
                 orientation="horizontal",
                 valuespec=RegExp(
                     size=32,
                     mode=RegExp.prefix,
                 ),
             )),
            ("match_desc",
             ListOfStrings(
                 title=_("Match interface description (regex)"),
                 help=_(
                     "Only discover interfaces whose the description matches one of the configured "
                     "regular expressions. The match is done on the beginning of the description. "
                     "This allows you to select interfaces based on the description without having "
                     "the alias be part of the service description."),
                 orientation="horizontal",
                 valuespec=RegExp(
                     size=32,
                     mode=RegExp.prefix,
                 ),
             )),
            ("portstates",
             ListChoice(
                 title=_("Network interface port states to discover"),
                 help=
                 _("When doing discovery on switches or other devices with network interfaces "
                   "then only ports found in one of the configured port states will be added to the monitoring. "
                   "Note: the state <i>admin down</i> is in fact not an <tt>ifOperStatus</tt> but represents the "
                   "<tt>ifAdminStatus</tt> of <tt>down</tt> - a port administratively switched off. If you check this option "
                   "then an alternate version of the check is being used that fetches the <tt>ifAdminState</tt> in addition. "
                   "This will add about 5% of additional SNMP traffic."),
                 choices=defines.interface_oper_states(),
                 toggle_all=True,
                 default_value=['1'],
             )),
            ("porttypes",
             DualListChoice(
                 title=_("Network interface port types to discover"),
                 help=_("When doing discovery on switches or other devices with network interfaces "
                        "then only ports of the specified types will be created services for."),
                 choices=defines.interface_port_types(),
                 custom_order=True,
                 rows=40,
                 toggle_all=True,
                 default_value=[
                     '6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205', '229'
                 ],
             )),
            ("rmon",
             DropdownChoice(
                 choices=[
                     (True,
                      _("Create extra service with RMON statistics data (if available for the device)"
                       )),
                     (False, _('Do not create extra services')),
                 ],
                 title=_("Collect RMON statistics data"),
                 help=
                 _("If you enable this option, for every RMON capable switch port an additional service will "
                   "be created which is always OK and collects RMON data. This will give you detailed information "
                   "about the distribution of packet sizes transferred over the port. Note: currently "
                   "this extra RMON check does not honor the inventory settings for switch ports. In a future "
                   "version of Check_MK RMON data may be added to the normal interface service and not add "
                   "an additional service."),
             )),
        ],
        help=_('This rule can be used to control the inventory for network ports. '
               'You can configure the port types and port states for inventory'
               'and the use of alias or description as service name.'),
    ),
    match='list',
)

_brocade_fcport_adm_choices = [
    (1, 'online(1)'),
    (2, 'offline(2)'),
    (3, 'testing(3)'),
    (4, 'faulty(4)'),
]

_brocade_fcport_op_choices = [
    (0, 'unkown(0)'),
    (1, 'online(1)'),
    (2, 'offline(2)'),
    (3, 'testing(3)'),
    (4, 'faulty(4)'),
]

_brocade_fcport_phy_choices = [
    (1, 'noCard(1)'),
    (2, 'noTransceiver(2)'),
    (3, 'laserFault(3)'),
    (4, 'noLight(4)'),
    (5, 'noSync(5)'),
    (6, 'inSync(6)'),
    (7, 'portFault(7)'),
    (8, 'diagFault(8)'),
    (9, 'lockRef(9)'),
    (10, 'validating(10)'),
    (11, 'invalidModule(11)'),
    (14, 'noSigDet(14)'),
    (255, 'unkown(255)'),
]

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="brocade_fcport_inventory",
    title=_("Brocade Port Discovery"),
    valuespec=Dictionary(
        elements=[
            ("use_portname",
             Checkbox(
                 title=_("Use port name as service name"),
                 label=_("use port name"),
                 default_value=True,
                 help=_("This option lets Check_MK use the port name as item instead of the "
                        "port number. If no description is available then the port number is "
                        "used anyway."))),
            ("show_isl",
             Checkbox(
                 title=_("add \"ISL\" to service description for interswitch links"),
                 label=_("add ISL"),
                 default_value=True,
                 help=_("This option lets Check_MK add the string \"ISL\" to the service "
                        "description for interswitch links."))),
            ("admstates",
             ListChoice(
                 title=_("Administrative port states to discover"),
                 help=_(
                     "When doing service discovery on brocade switches only ports with the given administrative "
                     "states will be added to the monitoring system."),
                 choices=_brocade_fcport_adm_choices,
                 columns=1,
                 toggle_all=True,
                 default_value=['1', '3', '4'],
             )),
            ("phystates",
             ListChoice(
                 title=_("Physical port states to discover"),
                 help=_(
                     "When doing service discovery on brocade switches only ports with the given physical "
                     "states will be added to the monitoring system."),
                 choices=_brocade_fcport_phy_choices,
                 columns=1,
                 toggle_all=True,
                 default_value=[3, 4, 5, 6, 7, 8, 9, 10])),
            ("opstates",
             ListChoice(
                 title=_("Operational port states to discover"),
                 help=_(
                     "When doing service discovery on brocade switches only ports with the given operational "
                     "states will be added to the monitoring system."),
                 choices=_brocade_fcport_op_choices,
                 columns=1,
                 toggle_all=True,
                 default_value=[1, 2, 3, 4])),
        ],
        help=_('This rule can be used to control the service discovery for brocade ports. '
               'You can configure the port states for inventory '
               'and the use of the description as service name.'),
    ),
    match='dict',
)


# In version 1.2.4 the check parameters for the resulting ps check
# where defined in the dicovery rule. We moved that to an own rule
# in the classical check parameter style. In order to support old
# configuration we allow reading old discovery rules and ship these
# settings in an optional sub-dictionary.
def convert_inventory_processes(old_dict):
    new_dict = {"default_params": {}}
    for key, value in old_dict.items():
        if key in [
                'levels',
                'handle_count',
                'cpulevels',
                'cpu_average',
                'virtual_levels',
                'resident_levels',
        ]:
            new_dict["default_params"][key] = value
        elif key != "perfdata":
            new_dict[key] = value

    # New cpu rescaling load rule
    if old_dict.get('cpu_rescale_max') is None:
        new_dict['cpu_rescale_max'] = True

    return new_dict


def forbid_re_delimiters_inside_groups(pattern, varprefix):
    # Used as input validation in PS check wato config
    group_re = r'\(.*?\)'
    for match in re.findall(group_re, pattern):
        for char in ['\\b', '$', '^']:
            if char in match:
                raise MKUserError(
                    varprefix,
                    _('"%s" is not allowed inside the regular expression group %s. '
                      'Bounding characters inside groups will vanish after discovery, '
                      'because processes are instanced for every matching group. '
                      'Thus enforce delimiters outside the group.') % (char, match))


register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_processes_rules",
    title=_('Process Discovery'),
    help=_(
        "This ruleset defines criteria for automatically creating checks for running processes "
        "based upon what is running when the service discovery is done. These services will be "
        "created with default parameters. They will get critical when no process is running and "
        "OK otherwise. You can parameterize the check with the ruleset <i>State and count of processes</i>."
    ),
    valuespec=Transform(
        Dictionary(
            elements=[
                ('descr',
                 TextAscii(
                     title=_('Process Name'),
                     style="dropdown",
                     allow_empty=False,
                     help=
                     _('<p>The process name may contain one or more occurances of <tt>%s</tt>. If you do this, then the pattern must be a regular '
                       'expression and be prefixed with ~. For each <tt>%s</tt> in the description, the expression has to contain one "group". A group '
                       'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or <tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a process '
                       'matching the pattern, it will substitute all such groups with the actual values when creating the check. That way one '
                       'rule can create several checks on a host.</p>'
                       '<p>If the pattern contains more groups then occurrances of <tt>%s</tt> in the service description then only the first matching '
                       'subexpressions  are used for the  service descriptions. The matched substrings corresponding to the remaining groups '
                       'are copied into the regular expression, nevertheless.</p>'
                       '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                       'These will be replaced by the first, second, ... matching group. This allows you to reorder things.</p>'
                      ),
                 )),
                (
                    'match',
                    Alternative(
                        title=_("Process Matching"),
                        style="dropdown",
                        elements=[
                            TextAscii(
                                title=_("Exact name of the process without argments"),
                                label=_("Executable:"),
                                size=50,
                            ),
                            Transform(
                                RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                    validate=forbid_re_delimiters_inside_groups,
                                ),
                                title=_("Regular expression matching command line"),
                                label=_("Command line:"),
                                help=
                                _("This regex must match the <i>beginning</i> of the complete "
                                  "command line of the process including arguments.<br>"
                                  "When using groups, matches will be instantiated "
                                  "during process discovery. e.g. (py.*) will match python, python_dev "
                                  "and python_test and discover 3 services. At check time, because "
                                  "python is a substring of python_test and python_dev it will aggregate"
                                  "all process that start with python. If that is not the intended behavior "
                                  "please use a delimiter like '$' or '\\b' around the group, e.g. (py.*)$"
                                 ),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                None,
                                totext="",
                                title=_("Match all processes"),
                            )
                        ],
                        match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                        default_value='/usr/sbin/foo')),
                ('user',
                 Alternative(
                     title=_('Name of the User'),
                     style="dropdown",
                     elements=[
                         FixedValue(
                             None,
                             totext="",
                             title=_("Match all users"),
                         ),
                         TextAscii(
                             title=_('Exact name of the user'),
                             label=_("User:"),
                         ),
                         FixedValue(
                             False,
                             title=_('Grab user from found processess'),
                             totext='',
                         ),
                     ],
                     help=
                     _('<p>The user specification can either be a user name (string). The inventory will then trigger only if that user matches '
                       'the user the process is running as and the resulting check will require that user. Alternatively you can specify '
                       '"grab user". If user is not selected the created check will not check for a specific user.</p>'
                       '<p>Specifying "grab user" makes the created check expect the process to run as the same user as during inventory: the user '
                       'name will be hardcoded into the check. In that case if you put %u into the service description, that will be replaced '
                       'by the actual user name during inventory. You need that if your rule might match for more than one user - your would '
                       'create duplicate services with the same description otherwise.</p><p>Windows users are specified by the namespace followed by '
                       'the actual user name. For example "\\\\NT AUTHORITY\\NETWORK SERVICE" or "\\\\CHKMKTEST\\Administrator".</p>'
                      ),
                 )),
                ('icon',
                 UserIconOrAction(
                     title=_("Add custom icon or action"),
                     help=_(
                         "You can assign icons or actions to the found services in the status GUI."
                     ),
                 )),
                ("cpu_rescale_max",
                 RadioChoice(
                     title=_("CPU rescale maximum load"),
                     help=_("CPU utilization is delivered by the Operating "
                            "System as a per CPU core basis. Thus each core contributes "
                            "with a 100% at full utilization, producing a maximum load "
                            "of N*100% (N=number of cores). For simplicity this maximum "
                            "can be rescaled down, making 100% the maximum and thinking "
                            "in terms of total CPU utilization."),
                     default_value=True,
                     orientation="vertical",
                     choices=[
                         (True, _("100% is all cores at full load")),
                         (False,
                          _("<b>N</b> * 100% as each core contributes with 100% at full load")),
                     ])),
                ('default_params',
                 Dictionary(
                     title=_("Default parameters for detected services"),
                     help=
                     _("Here you can select default parameters that are being set "
                       "for detected services. Note: the preferred way for setting parameters is to use "
                       "the rule set <a href='wato.py?varname=checkgroup_parameters%3Apsmode=edit_ruleset'> "
                       "State and Count of Processes</a> instead. "
                       "A change there will immediately be active, while a change in this rule "
                       "requires a re-discovery of the services."),
                     elements=process_level_elements,
                 )),
            ],
            required_keys=["descr", "cpu_rescale_max"],
        ),
        forth=convert_inventory_processes,
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inv_domino_tasks_rules",
    title=_('Lotus Domino Task Discovery'),
    help=_("This rule controls the discovery of tasks on Lotus Domino systems. "
           "Any changes later on require a host re-discovery"),
    valuespec=Dictionary(
        elements=[
            ('descr',
             TextAscii(
                 title=_('Service Description'),
                 allow_empty=False,
                 help=
                 _('<p>The service description may contain one or more occurances of <tt>%s</tt>. In this '
                   'case, the pattern must be a regular expression prefixed with ~. For each '
                   '<tt>%s</tt> in the description, the expression has to contain one "group". A group '
                   'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or '
                   '<tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a task '
                   'matching the pattern, it will substitute all such groups with the actual values when '
                   'creating the check. In this way one rule can create several checks on a host.</p>'
                   '<p>If the pattern contains more groups than occurrences of <tt>%s</tt> in the service '
                   'description, only the first matching subexpressions are used for the service '
                   'descriptions. The matched substrings corresponding to the remaining groups '
                   'are nevertheless copied into the regular expression.</p>'
                   '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                   'These expressions will be replaced by the first, second, ... matching group, allowing '
                   'you to reorder things.</p>'),
             )),
            (
                'match',
                Alternative(
                    title=_("Task Matching"),
                    elements=[
                        TextAscii(
                            title=_("Exact name of the task"),
                            size=50,
                        ),
                        Transform(
                            RegExp(
                                size=50,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching command line"),
                            help=_("This regex must match the <i>beginning</i> of the task"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all tasks"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                    default_value='foo')),
            ('levels',
             Tuple(
                 title=_('Levels'),
                 help=
                 _("Please note that if you specify and also if you modify levels here, the change is "
                   "activated only during an inventory.  Saving this rule is not enough. This is due to "
                   "the nature of inventory rules."),
                 elements=[
                     Integer(
                         title=_("Critical below"),
                         unit=_("processes"),
                         default_value=1,
                     ),
                     Integer(
                         title=_("Warning below"),
                         unit=_("processes"),
                         default_value=1,
                     ),
                     Integer(
                         title=_("Warning above"),
                         unit=_("processes"),
                         default_value=1,
                     ),
                     Integer(
                         title=_("Critical above"),
                         unit=_("processes"),
                         default_value=1,
                     ),
                 ],
             )),
        ],
        required_keys=['match', 'levels', 'descr'],
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_sap_values",
    title=_('SAP R/3 Single Value Inventory'),
    valuespec=Dictionary(
        elements=[
            (
                'match',
                Alternative(
                    title=_("Node Path Matching"),
                    elements=[
                        TextAscii(
                            title=_("Exact path of the node"),
                            size=100,
                        ),
                        Transform(
                            RegExp(
                                size=100,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching the path"),
                            help=_("This regex must match the <i>beginning</i> of the complete "
                                   "path of the node as reported by the agent"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all nodes"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                    default_value=
                    'SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime')
            ),
            ('limit_item_levels',
             Integer(
                 title=_("Limit Path Levels for Service Names"),
                 unit=_('path levels'),
                 minvalue=1,
                 help=
                 _("The service descriptions of the inventorized services are named like the paths "
                   "in SAP. You can use this option to let the inventory function only use the last "
                   "x path levels for naming."),
             ))
        ],
        optional_keys=['limit_item_levels'],
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="sap_value_groups",
    title=_('SAP Value Grouping Patterns'),
    help=_('The check <tt>sap.value</tt> normally creates one service for each SAP value. '
           'By defining grouping patterns, you can switch to the check <tt>sap.value-groups</tt>. '
           'That check monitors a list of SAP values at once.'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one value grouping pattern"),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                Tuple(
                    show_titles=True,
                    orientation="vertical",
                    elements=[
                        RegExpUnicode(
                            title=_("Include Pattern"),
                            mode=RegExp.prefix,
                        ),
                        RegExpUnicode(
                            title=_("Exclude Pattern"),
                            mode=RegExp.prefix,
                        )
                    ],
                ),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_heartbeat_crm_rules",
    title=_("Heartbeat CRM Discovery"),
    valuespec=Dictionary(
        elements=[
            ("naildown_dc",
             Checkbox(
                 title=_("Naildown the DC"),
                 label=_("Mark the currently distinguished controller as preferred one"),
                 help=_(
                     "Nails down the DC to the node which is the DC during discovery. The check "
                     "will report CRITICAL when another node becomes the DC during later checks."))
            ),
            ("naildown_resources",
             Checkbox(
                 title=_("Naildown the resources"),
                 label=_("Mark the nodes of the resources as preferred one"),
                 help=_(
                     "Nails down the resources to the node which is holding them during discovery. "
                     "The check will report CRITICAL when another holds the resource during later checks."
                 ))),
        ],
        help=_('This rule can be used to control the discovery for Heartbeat CRM checks.'),
        optional_keys=[],
    ),
    match='dict',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_df_rules",
    title=_("Discovery parameters for filesystem checks"),
    valuespec=Dictionary(
        elements=[
            ("include_volume_name", Checkbox(title=_("Include Volume name in item"))),
            ("ignore_fs_types",
             ListChoice(
                 title=_("Filesystem types to ignore"),
                 choices=[
                     ("tmpfs", "tmpfs"),
                     ("nfs", "nfs"),
                     ("smbfs", "smbfs"),
                     ("cifs", "cifs"),
                     ("iso9660", "iso9660"),
                 ],
                 default_value=["tmpfs", "nfs", "smbfs", "cifs", "iso9660"])),
            ("never_ignore_mountpoints",
             ListOf(
                 TextUnicode(),
                 title=_(u"Mountpoints to never ignore"),
                 help=_(
                     u"Regardless of filesystem type, these mountpoints will always be discovered."
                     u"Globbing or regular expressions are currently not supported."),
             )),
        ],),
    match="dict",
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_mssql_counters_rules",
    title=_("Include MSSQL Counters services"),
    valuespec=Dictionary(
        elements=[
            ("add_zero_based_services", Checkbox(title=_("Include service with zero base."))),
        ],
        optional_keys=[]),
    match="dict",
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_fujitsu_ca_ports",
    title=_("Discovery of Fujtsu storage CA ports"),
    valuespec=Dictionary(
        elements=[
            ("indices", ListOfStrings(title=_("CA port indices"))),
            ("modes",
             DualListChoice(
                 title=_("CA port modes"),
                 choices=[
                     ("CA", _("CA")),
                     ("RA", _("RA")),
                     ("CARA", _("CARA")),
                     ("Initiator", _("Initiator")),
                 ],
                 row=4,
                 size=30,
             )),
        ],),
    match="dict",
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="discovery_mssql_backup",
    title=_("Discovery of MSSQL backup"),
    valuespec=Dictionary(
        elements=[
            ("mode",
             DropdownChoice(
                 title=_("Backup modes"),
                 choices=[
                     ("summary", _("Create a service for each instance")),
                     ("per_type", _("Create a service for each instance and backup type")),
                 ])),
        ],),
    match="dict",
)

#.
#   .--Applications--------------------------------------------------------.
#   |          _                _ _           _   _                        |
#   |         / \   _ __  _ __ | (_) ___ __ _| |_(_) ___  _ __  ___        |
#   |        / _ \ | '_ \| '_ \| | |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |       / ___ \| |_) | |_) | | | (_| (_| | |_| | (_) | | | \__ \       |
#   |      /_/   \_\ .__/| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |              |_|   |_|                                               |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersApplications,
    varname="logwatch_rules",
    title=_('Logwatch Patterns'),
    valuespec=Transform(
        Dictionary(
            elements=[
                ("reclassify_patterns",
                 ListOf(
                     Tuple(
                         help=_("This defines one logfile pattern rule"),
                         show_titles=True,
                         orientation="horizontal",
                         elements=[
                             DropdownChoice(
                                 title=_("State"),
                                 choices=[
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                 ],
                             ),
                             RegExpUnicode(
                                 title=_("Pattern (Regex)"),
                                 size=40,
                                 mode=RegExp.infix,
                             ),
                             TextUnicode(
                                 title=_("Comment"),
                                 size=40,
                             ),
                         ]),
                     title=_("Reclassify state matching regex pattern"),
                     help=
                     _('<p>You can define one or several patterns (regular expressions) in each logfile pattern rule. '
                       'These patterns are applied to the selected logfiles to reclassify the '
                       'matching log messages. The first pattern which matches a line will '
                       'be used for reclassifying a message. You can use the '
                       '<a href="wato.py?mode=pattern_editor">Logfile Pattern Analyzer</a> '
                       'to test the rules you defined here.</p>'
                       '<p>Select "Ignore" as state to get the matching logs deleted. Other states will keep the '
                       'log entries but reclassify the state of them.</p>'),
                     add_label=_("Add pattern"),
                 )),
                ("reclassify_states",
                 Dictionary(
                     title=_("Reclassify complete state"),
                     help=_(
                         "This setting allows you to convert all incoming states to another state. "
                         "The option is applied before the state conversion via regexes. So the regex values can "
                         "modify the state even further."),
                     elements=[
                         ("c_to",
                          DropdownChoice(
                              title=_("Change CRITICAL State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="C",
                          )),
                         ("w_to",
                          DropdownChoice(
                              title=_("Change WARNING State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="W",
                          )),
                         ("o_to",
                          DropdownChoice(
                              title=_("Change OK State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="O",
                          )),
                         ("._to",
                          DropdownChoice(
                              title=_("Change Context Info to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value=".",
                          )),
                     ],
                     optional_keys=False,
                 )),
            ],
            optional_keys=["reclassify_states"],
        ),
        forth=lambda x: isinstance(x, dict) and x or {"reclassify_patterns": x}),
    itemtype='item',
    itemname='Logfile',
    itemhelp=_("Put the item names of the logfiles here. For example \"System$\" "
               "to select the service \"LOG System\". You can use regular "
               "expressions which must match the beginning of the logfile name."),
    match='all',
)

#.
#   .--Unsorted--(Don't create new stuff here!)----------------------------.
#   |              _   _                      _           _                |
#   |             | | | |_ __  ___  ___  _ __| |_ ___  __| |               |
#   |             | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |               |
#   |             | |_| | | | \__ \ (_) | |  | ||  __/ (_| |               |
#   |              \___/|_| |_|___/\___/|_|   \__\___|\__,_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  All these rules have not been moved into their according sections.  |
#   |  Please move them as you come along - but beware of dependecies!     |
#   |  Remove this section as soon as it's empty.                          |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="filesystem_groups",
    title=_('Filesystem grouping patterns'),
    help=_('Normally the filesystem checks (<tt>df</tt>, <tt>hr_fs</tt> and others) '
           'will create a single service for each filesystem. '
           'By defining grouping '
           'patterns you can handle groups of filesystems like one filesystem. '
           'For each group you can define one or several patterns. '
           'The filesystems matching one of the patterns '
           'will be monitored like one big filesystem in a single service.'),
    valuespec=ListOf(
        Tuple(
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                TextAscii(
                    title=_("Pattern for mount point (using * and ?)"),
                    help=_("You can specify one or several patterns containing "
                           "<tt>*</tt> and <tt>?</tt>, for example <tt>/spool/tmpspace*</tt>. "
                           "The filesystems matching the patterns will be monitored "
                           "like one big filesystem in a single service."),
                ),
            ]),
        add_label=_("Add pattern"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="fileinfo_groups",
    title=_('File Grouping Patterns'),
    help=_('The check <tt>fileinfo</tt> monitors the age and size of '
           'a single file. Each file information that is sent '
           'by the agent will create one service. By defining grouping '
           'patterns you can switch to the check <tt>fileinfo.groups</tt>. '
           'That check monitors a list of files at once. You can set levels '
           'not only for the total size and the age of the oldest/youngest '
           'file but also on the count. You can define one or several '
           'patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example '
           '<tt>/var/log/apache/*.log</tt>. Please see Python\'s fnmatch for more '
           'information regarding globbing patterns and special characters. '
           'If the pattern begins with a tilde then this pattern is interpreted as '
           'a regular expression instead of as a filename globbing pattern and '
           '<tt>*</tt> and <tt>?</tt> are treated differently. '
           'For files contained in a group '
           'the discovery will automatically create a group service instead '
           'of single services for each file. This rule also applies when '
           'you use manually configured checks instead of inventorized ones. '
           'Furthermore, the current time/date in a configurable format '
           'may be included in the include pattern. The syntax is as follows: '
           '$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec '
           'is a list of time format directives of the unix date command. '
           'Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern '
           'of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files '
           'with todays date  as name in the directory /var/tmp/backups. '
           'The YESTERDAY syntax simply subtracts one day from the reference time.'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one file grouping pattern."),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_("Name of group"),
                    size=10,
                ),
                Transform(
                    Tuple(
                        show_titles=True,
                        orientation="vertical",
                        elements=[
                            TextAscii(title=_("Include Pattern"), size=40),
                            TextAscii(title=_("Exclude Pattern"), size=40),
                        ],
                    ),
                    forth=lambda params: isinstance(params, str) and (params, '') or params),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "checkpoint_packets",
    _("Checkpoint Firewall Packet Rates"),
    Dictionary(elements=[
        ("accepted",
         Levels(
             title=_("Maximum Rate of Accepted Packets"),
             default_value=None,
             default_levels=(100000, 200000),
             unit="pkts/sec")),
        ("rejected",
         Levels(
             title=_("Maximum Rate of Rejected Packets"),
             default_value=None,
             default_levels=(100000, 200000),
             unit="pkts/sec")),
        ("dropped",
         Levels(
             title=_("Maximum Rate of Dropped Packets"),
             default_value=None,
             default_levels=(100000, 200000),
             unit="pkts/sec")),
        ("logged",
         Levels(
             title=_("Maximum Rate of Logged Packets"),
             default_value=None,
             default_levels=(100000, 200000),
             unit="pkts/sec")),
    ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "f5_pools", _("F5 Loadbalancer Pools"),
    Tuple(
        title=_("Minimum number of pool members"),
        elements=[
            Integer(title=_("Warning if below"), unit=_("Members ")),
            Integer(title=_("Critical if below"), unit=_("Members")),
        ],
    ), TextAscii(title=_("Name of pool")), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "mysql_db_size", _("Size of MySQL databases"),
    Optional(
        Tuple(elements=[
            Filesize(title=_("warning at")),
            Filesize(title=_("critical at")),
        ]),
        help=_("The check will trigger a warning or critical state if the size of the "
               "database exceeds these levels."),
        title=_("Impose limits on the size of the database"),
    ),
    TextAscii(
        title=_("Name of the database"),
        help=_("Don't forget the instance: instance:dbname"),
    ), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "postgres_sessions",
    _("PostgreSQL Sessions"),
    Dictionary(
        help=_("This check monitors the current number of active and idle sessions on PostgreSQL"),
        elements=[
            (
                "total",
                Tuple(
                    title=_("Number of current sessions"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                    ],
                ),
            ),
            (
                "running",
                Tuple(
                    title=_("Number of currently running sessions"),
                    help=_("Levels for the number of sessions that are currently active"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=10),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=20),
                    ],
                ),
            ),
        ]),
    None,
    match_type="dict",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "postgres_instance_sessions",
    _("PostgreSQL Sessions"),
    Dictionary(
        help=_("This check monitors the current number of active and idle sessions on PostgreSQL"),
        elements=[
            (
                "total",
                Tuple(
                    title=_("Number of current sessions"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                    ],
                ),
            ),
            (
                "running",
                Tuple(
                    title=_("Number of currently running sessions"),
                    help=_("Levels for the number of sessions that are currently active"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=10),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=20),
                    ],
                ),
            ),
        ]),
    TextAscii(title=_("Instance")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "asa_svc_sessions",
    _("Cisco SSl VPN Client Sessions"),
    Tuple(
        title=_("Number of active sessions"),
        help=_("This check monitors the current number of active sessions"),
        elements=[
            Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
            Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
        ],
    ),
    None,
    match_type="first",
)


def convert_oracle_sessions(value):
    if isinstance(value, tuple):
        return {'sessions_abs': value}
    if 'sessions_abs' not in value:
        value['sessions_abs'] = (100, 200)
    return value


register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "oracle_sessions",
    _("Oracle Sessions"),
    Transform(
        Dictionary(
            elements=[
                ("sessions_abs",
                 Alternative(
                     title=_("Absolute levels of active sessions"),
                     style="dropdown",
                     help=_("This check monitors the current number of active sessions on Oracle"),
                     elements=[
                         FixedValue(None, title=_("Do not use absolute levels"), totext=""),
                         Tuple(
                             title=_("Number of active sessions"),
                             elements=[
                                 Integer(
                                     title=_("Warning at"), unit=_("sessions"), default_value=100),
                                 Integer(
                                     title=_("Critical at"), unit=_("sessions"), default_value=200),
                             ],
                         ),
                     ],
                 )),
                (
                    "sessions_perc",
                    Tuple(
                        title=_("Relative levels of active sessions."),
                        help=
                        _("Set upper levels of active sessions relative to max. number of sessions. This is optional."
                         ),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
            ],
            optional_keys=["sessions_perc"],
        ),
        forth=convert_oracle_sessions),
    TextAscii(title=_("Database name"), allow_empty=False),
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "oracle_locks",
    _("Oracle Locks"),
    Dictionary(elements=[("levels",
                          Tuple(
                              title=_("Levels for minimum wait time for a lock"),
                              elements=[
                                  Age(title=_("warning if higher then"), default_value=1800),
                                  Age(title=_("critical if higher then"), default_value=3600),
                              ]))]),
    TextAscii(title=_("Database SID"), size=12, allow_empty=False),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "oracle_longactivesessions",
    _("Oracle Long Active Sessions"),
    Dictionary(elements=[("levels",
                          Tuple(
                              title=_("Levels of active sessions"),
                              elements=[
                                  Integer(title=_("Warning if more than"), unit=_("sessions")),
                                  Integer(title=_("Critical if more than"), unit=_("sessions")),
                              ]))]),
    TextAscii(title=_("Database SID"), size=12, allow_empty=False),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "postgres_stat_database",
    _("PostgreSQL Database Statistics"),
    Dictionary(
        help=_(
            "This check monitors how often database objects in a PostgreSQL Database are accessed"),
        elements=[
            (
                "blocks_read",
                Tuple(
                    title=_("Blocks read"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("blocks/s")),
                        Float(title=_("Critical at"), unit=_("blocks/s")),
                    ],
                ),
            ),
            (
                "xact_commit",
                Tuple(
                    title=_("Commits"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_fetched",
                Tuple(
                    title=_("Fetches"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_deleted",
                Tuple(
                    title=_("Deletes"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_updated",
                Tuple(
                    title=_("Updates"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_inserted",
                Tuple(
                    title=_("Inserts"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
        ],
    ),
    TextAscii(title=_("Database name"), allow_empty=False),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "win_dhcp_pools",
    _("DHCP Pools for Windows and Linux"),
    Transform(
        Dictionary(
            elements = [
                ("free_leases",
                    Alternative(
                        title = _("Free leases levels"),
                        elements = [
                            Tuple(
                                title = _("Free leases levels in percent"),
                                elements = [
                                    Percentage(title = _("Warning if below"),  default_value = 10.0),
                                    Percentage(title = _("Critical if below"), default_value = 5.0)
                                ]
                            ),
                            Tuple(
                                title = _("Absolute free leases levels"),
                                elements = [
                                    Integer(title = _("Warning if below"),  unit = _("free leases")),
                                    Integer(title = _("Critical if below"), unit = _("free leases"))
                                ]
                            )
                        ]
                    )
                ),
                ("used_leases",
                    Alternative(
                        title = _("Used leases levels"),
                        elements = [
                            Tuple(
                                title = _("Used leases levels in percent"),
                                elements = [
                                    Percentage(title = _("Warning if below")),
                                    Percentage(title = _("Critical if below"))
                                ]
                            ),
                            Tuple(
                                title = _("Absolute used leases levels"),
                                elements = [
                                    Integer(title = _("Warning if below"),  unit = _("used leases")),
                                    Integer(title = _("Critical if below"), unit = _("used leases"))
                                ]
                            )
                        ]
                    )
                ),
            ]
        ),
        forth = lambda params: isinstance(params, tuple) and {"free_leases" : (float(params[0]), float(params[1]))} or params,
    ),
    TextAscii(
        title = _("Pool name"),
        allow_empty = False,
    ),
    match_type = "first",
)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem,
    "threads",
    _("Number of threads"),
    Tuple(
        help=_(
            "These levels check the number of currently existing threads on the system. Each process has at "
            "least one thread."),
        elements=[
            Integer(title=_("Warning at"), unit=_("threads"), default_value=1000),
            Integer(title=_("Critical at"), unit=_("threads"), default_value=2000)
        ]),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem,
    "logins",
    _("Number of Logins on System"),
    Tuple(
        help=_("This rule defines upper limits for the number of logins on a system."),
        elements=[
            Integer(title=_("Warning at"), unit=_("users"), default_value=20),
            Integer(title=_("Critical at"), unit=_("users"), default_value=30)
        ]),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "vms_procs",
    _("Number of processes on OpenVMS"),
    Optional(
        Tuple(elements=[
            Integer(title=_("Warning at"), unit=_("processes"), default_value=100),
            Integer(title=_("Critical at"), unit=_("processes"), default_value=200)
        ]),
        title=_("Impose levels on number of processes"),
    ),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem, "vm_counter",
    _("Number of kernel events per second"),
    Levels(
        help=_("This ruleset applies to several similar checks measing various kernel "
               "events like context switches, process creations and major page faults. "
               "Please create separate rules for each type of kernel counter you "
               "want to set levels for."),
        unit=_("events per second"),
        default_levels=(1000, 5000),
        default_difference=(500.0, 1000.0),
        default_value=None,
    ),
    DropdownChoice(
        title=_("kernel counter"),
        choices=[("Context Switches", _("Context Switches")),
                 ("Process Creations", _("Process Creations")),
                 ("Major Page Faults", _("Major Page Faults"))]), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "ibm_svc_total_latency",
    _("IBM SVC: Levels for total disk latency"),
    Dictionary(elements=[
        ("read",
         Levels(
             title=_("Read latency"),
             unit=_("ms"),
             default_value=None,
             default_levels=(50.0, 100.0))),
        ("write",
         Levels(
             title=_("Write latency"),
             unit=_("ms"),
             default_value=None,
             default_levels=(50.0, 100.0))),
    ]),
    DropdownChoice(
        choices=[
            ("Drives", _("Total latency for all drives")),
            ("MDisks", _("Total latency for all MDisks")),
            ("VDisks", _("Total latency for all VDisks")),
        ],
        title=_("Disk/Drive type"),
        help=_("Please enter <tt>Drives</tt>, <tt>Mdisks</tt> or <tt>VDisks</tt> here.")),
    match_type="dict",
)


def transform_ibm_svc_host(params):
    if params is None:
        # Old inventory rule until version 1.2.7
        # params were None instead of emtpy dictionary
        params = {'always_ok': False}

    if 'always_ok' in params:
        if params['always_ok'] is False:
            params = {'degraded_hosts': (1, 1), 'offline_hosts': (1, 1), 'other_hosts': (1, 1)}
        else:
            params = {}
    return params


register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "ibm_svc_host",
    _("IBM SVC: Options for SVC Hosts Check"),
    Transform(
        Dictionary(elements=[
            (
                "active_hosts",
                Tuple(
                    title=_("Count of active hosts"),
                    elements=[
                        Integer(title=_("Warning at or below"), minvalue=0, unit=_("active hosts")),
                        Integer(
                            title=_("Critical at or below"), minvalue=0, unit=_("active hosts")),
                    ]),
            ),
            (
                "inactive_hosts",
                Tuple(
                    title=_("Count of inactive hosts"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"), minvalue=0, unit=_("inactive hosts")),
                        Integer(
                            title=_("Critical at or above"), minvalue=0, unit=_("inactive hosts")),
                    ]),
            ),
            (
                "degraded_hosts",
                Tuple(
                    title=_("Count of degraded hosts"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"), minvalue=0, unit=_("degraded hosts")),
                        Integer(
                            title=_("Critical at or above"), minvalue=0, unit=_("degraded hosts")),
                    ]),
            ),
            (
                "offline_hosts",
                Tuple(
                    title=_("Count of offline hosts"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"), minvalue=0, unit=_("offline hosts")),
                        Integer(
                            title=_("Critical at or above"), minvalue=0, unit=_("offline hosts")),
                    ]),
            ),
            (
                "other_hosts",
                Tuple(
                    title=_("Count of other hosts"),
                    elements=[
                        Integer(title=_("Warning at or above"), minvalue=0, unit=_("other hosts")),
                        Integer(title=_("Critical at or above"), minvalue=0, unit=_("other hosts")),
                    ]),
            ),
        ]),
        forth=transform_ibm_svc_host,
    ),
    None,
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "ibm_svc_mdisk",
    _("IBM SVC: Options for SVC Disk Check"),
    Dictionary(
        optional_keys=False,
        elements=[
            (
                "online_state",
                MonitoringState(
                    title=_("Resulting state if disk is online"),
                    default_value=0,
                ),
            ),
            (
                "degraded_state",
                MonitoringState(
                    title=_("Resulting state if disk is degraded"),
                    default_value=1,
                ),
            ),
            (
                "offline_state",
                MonitoringState(
                    title=_("Resulting state if disk is offline"),
                    default_value=2,
                ),
            ),
            (
                "excluded_state",
                MonitoringState(
                    title=_("Resulting state if disk is excluded"),
                    default_value=2,
                ),
            ),
            (
                "managed_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in managed mode"),
                    default_value=0,
                ),
            ),
            (
                "array_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in array mode"),
                    default_value=0,
                ),
            ),
            (
                "image_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in image mode"),
                    default_value=0,
                ),
            ),
            (
                "unmanaged_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in unmanaged mode"),
                    default_value=1,
                ),
            ),
        ]),
    TextAscii(
        title=_("IBM SVC disk"),
        help=_("Name of the disk, e.g. mdisk0"),
    ),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "diskstat",
    _("Levels for disk IO"),
    Dictionary(
        help=_(
            "With this rule you can set limits for various disk IO statistics. "
            "Keep in mind that not all of these settings may be applicable for the actual "
            "check. For example, if the check doesn't provide a <i>Read wait</i> information in its "
            "output, any configuration setting referring to <i>Read wait</i> will have no effect."),
        elements=[
            ("read",
             Levels(
                 title=_("Read throughput"),
                 unit=_("MB/s"),
                 default_levels=(50.0, 100.0),
             )),
            ("write",
             Levels(
                 title=_("Write throughput"),
                 unit=_("MB/s"),
                 default_levels=(50.0, 100.0),
             )),
            ("utilization",
             Levels(
                 title=_("Disk Utilization"),
                 unit=_("%"),
                 default_levels=(80.0, 90.0),
             )),
            ("latency", Levels(
                title=_("Disk Latency"),
                unit=_("ms"),
                default_levels=(80.0, 160.0),
            )),
            ("read_wait", Levels(title=_("Read wait"), unit=_("ms"), default_levels=(30.0, 50.0))),
            ("write_wait", Levels(title=_("Write wait"), unit=_("ms"), default_levels=(30.0,
                                                                                       50.0))),
            ("average",
             Age(
                 title=_("Averaging"),
                 help=_(
                     "When averaging is set, then all of the disk's metrics are averaged "
                     "over the selected interval - rather then the check interval. This allows "
                     "you to make your monitoring less reactive to short peaks. But it will also "
                     "introduce a loss of accuracy in your graphs. "),
                 default_value=300,
             )),
            ("read_ios",
             Levels(title=_("Read operations"), unit=_("1/s"), default_levels=(400.0, 600.0))),
            ("write_ios",
             Levels(title=_("Write operations"), unit=_("1/s"), default_levels=(300.0, 400.0))),
        ]),
    TextAscii(
        title=_("Device"),
        help=_(
            "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>,  "
            "a per-disk IO is specified by the drive letter, a colon and a slash on Windows "
            "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "disk_io", _("Levels on disk IO (old style checks)"),
    Dictionary(elements=[
        ("read",
         Levels(
             title=_("Read throughput"),
             unit=_("MB/s"),
             default_value=None,
             default_levels=(50.0, 100.0))),
        ("write",
         Levels(
             title=_("Write throughput"),
             unit=_("MB/s"),
             default_value=None,
             default_levels=(50.0, 100.0))),
        ("average",
         Integer(
             title=_("Average"),
             help=_("When averaging is set, a floating average value "
                    "of the disk throughput is computed and the levels for read "
                    "and write will be applied to the average instead of the current "
                    "value."),
             default_value=5,
             minvalue=1,
             unit=_("minutes"))),
        ("latency",
         Tuple(
             title=_("IO Latency"),
             elements=[
                 Float(title=_("warning at"), unit=_("ms"), default_value=80.0),
                 Float(title=_("critical at"), unit=_("ms"), default_value=160.0),
             ])),
        (
            "latency_perfdata",
            Checkbox(
                title=_("Performance Data for Latency"),
                label=_("Collect performance data for disk latency"),
                help=_("Note: enabling performance data for the latency might "
                       "cause incompatibilities with existing historical data "
                       "if you are running PNP4Nagios in SINGLE mode.")),
        ),
        ("read_ql",
         Tuple(
             title=_("Read Queue-Length"),
             elements=[
                 Float(title=_("warning at"), default_value=80.0),
                 Float(title=_("critical at"), default_value=90.0),
             ])),
        ("write_ql",
         Tuple(
             title=_("Write Queue-Length"),
             elements=[
                 Float(title=_("warning at"), default_value=80.0),
                 Float(title=_("critical at"), default_value=90.0),
             ])),
        (
            "ql_perfdata",
            Checkbox(
                title=_("Performance Data for Queue Length"),
                label=_("Collect performance data for disk latency"),
                help=_("Note: enabling performance data for the latency might "
                       "cause incompatibilities with existing historical data "
                       "if you are running PNP4Nagios in SINGLE mode.")),
        ),
    ]),
    TextAscii(
        title=_("Device"),
        help=_(
            "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
            "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
            "A per-disk IO is specified by the drive letter, a colon and a slash on Windows "
            "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")),
    "dict")

register_rule(
    RulespecGroupCheckParametersStorage,
    "diskstat_inventory",
    ListChoice(
        title=_("Discovery mode for Disk IO check"),
        help=_("This rule controls which and how many checks will be created "
               "for monitoring individual physical and logical disks. "
               "Note: the option <i>Create a summary for all read, one for "
               "write</i> has been removed. Some checks will still support "
               "this settings, but it will be removed there soon."),
        choices=[
            ("summary", _("Create a summary over all physical disks")),
            # This option is still supported by some checks, but is deprecated and
            # we fade it out...
            # ( "legacy",   _("Create a summary for all read, one for write") ),
            ("physical", _("Create a separate check for each physical disk")),
            ("lvm", _("Create a separate check for each LVM volume (Linux)")),
            ("vxvm", _("Creata a separate check for each VxVM volume (Linux)")),
            ("diskless", _("Creata a separate check for each partition (XEN)")),
        ],
        default_value=['summary'],
    ),
    match="first")


def transform_if_groups_forth(params):
    for param in params:
        if param.get("name"):
            param["group_name"] = param["name"]
            del param["name"]
        if param.get("include_items"):
            param["items"] = param["include_items"]
            del param["include_items"]
        if param.get("single") is not None:
            if param["single"]:
                param["group_presence"] = "instead"
            else:
                param["group_presence"] = "separate"
            del param["single"]
    return params


vs_elements_if_groups_matches = [
    ("iftype",
     Transform(
         DropdownChoice(
             title=_("Select interface port type"),
             choices=defines.interface_port_types(),
             help=_("Only interfaces with the given port type are put into this group. "
                    "For example 53 (propVirtual)."),
         ),
         forth=str,
         back=int,
     )),
    ("items",
     ListOfStrings(
         title=_("Restrict interface items"),
         help=_("Only interface with these item names are put into this group."),
     )),
]

vs_elements_if_groups_group = [
    ("group_name",
     TextAscii(
         title=_("Group name"),
         help=_("Name of group in service description"),
         allow_empty=False,
     )),
    ("group_presence",
     DropdownChoice(
         title=_("Group interface presence"),
         help=_("Determine whether the group interface is created as an "
                "separate service or not. In second case the choosen interface "
                "services disapear."),
         choices=[
             ("separate", _("List grouped interfaces separately")),
             ("instead", _("List grouped interfaces instead")),
         ],
         default_value="instead",
     )),
]

register_rule(
    RulespecGroupCheckParametersNetworking,
    varname="if_groups",
    title=_('Network interface groups'),
    help=_(
        'Normally the Interface checks create a single service for interface. '
        'By defining if-group patterns multiple interfaces can be combined together. '
        'A single service is created for this interface group showing the total traffic amount '
        'of its members. You can configure if interfaces which are identified as group interfaces '
        'should not show up as single service. You can restrict grouped interfaces by iftype and the '
        'item name of the single interface.'),
    valuespec=Transform(
        Alternative(
            style="dropdown",
            elements=[
                ListOf(
                    title=_("Groups on single host"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(
                        elements=vs_elements_if_groups_group + vs_elements_if_groups_matches,
                        required_keys=["group_name", "group_presence"]),
                ),
                ListOf(
                    magic="@!!",
                    title=_("Groups on cluster"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(
                        elements=vs_elements_if_groups_group +
                        [("node_patterns",
                          ListOf(
                              title=_("Patterns for each node"),
                              add_label=_("Add pattern"),
                              valuespec=Dictionary(
                                  elements=[("node_name", TextAscii(title=_("Node name")))] +
                                  vs_elements_if_groups_matches,
                                  required_keys=["node_name"]),
                              allow_empty=False,
                          ))],
                        optional_keys=[])),
            ],
        ),
        forth=transform_if_groups_forth),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="winperf_msx_queues_inventory",
    title=_('MS Exchange Message Queues Discovery'),
    help=_(
        'Per default the offsets of all Windows performance counters are preconfigured in the check. '
        'If the format of your counters object is not compatible then you can adapt the counter '
        'offsets manually.'),
    valuespec=ListOf(
        Tuple(
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_("Name of Counter"),
                    help=_("Name of the Counter to be monitored."),
                    size=50,
                    allow_empty=False,
                ),
                Integer(
                    title=_("Offset"),
                    help=_("The offset of the information relative to counter base"),
                    allow_empty=False,
                ),
            ]),
        movable=False,
        add_label=_("Add Counter")),
    match='all',
)

mailqueue_params = Dictionary(
    elements=[
        (
            "deferred",
            Tuple(
                title=_("Mails in outgoing mail queue/deferred mails"),
                help=_("This rule is applied to the number of E-Mails currently "
                       "in the deferred mail queue, or in the general outgoing mail "
                       "queue, if such a distinction is not available."),
                elements=[
                    Integer(title=_("Warning at"), unit=_("mails"), default_value=10),
                    Integer(title=_("Critical at"), unit=_("mails"), default_value=20),
                ],
            ),
        ),
        (
            "active",
            Tuple(
                title=_("Mails in active mail queue"),
                help=_("This rule is applied to the number of E-Mails currently "
                       "in the active mail queue"),
                elements=[
                    Integer(title=_("Warning at"), unit=_("mails"), default_value=800),
                    Integer(title=_("Critical at"), unit=_("mails"), default_value=1000),
                ],
            ),
        ),
    ],
    optional_keys=["active"],
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "mailqueue_length",
    _("Number of mails in outgoing mail queue"),
    Transform(
        mailqueue_params,
        forth=lambda old: not isinstance(old, dict) and {"deferred": old} or old,
    ),
    None,
    match_type="dict",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "mail_queue_length",
    _("Number of mails in outgoing mail queue"),
    Transform(
        mailqueue_params,
        forth=lambda old: not isinstance(old, dict) and {"deferred": old} or old,
    ),
    TextAscii(title=_("Mail queue name")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "mail_latency", _("Mail Latency"),
    Tuple(
        title=_("Upper levels for Mail Latency"),
        elements=[
            Age(title=_("Warning at"), default_value=40),
            Age(title=_("Critical at"), default_value=60),
        ]), None, "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "zpool_status",
    _("ZFS storage pool status"),
    None,
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersVirtualization,
    "vm_state",
    _("Overall state of a virtual machine (for example ESX VMs)"),
    None,
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersHardware,
    "hw_errors",
    _("Simple checks for BIOS/Hardware errors"),
    None,
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "omd_status", _("OMD site status"), None,
    TextAscii(
        title=_("Name of the OMD site"),
        help=_("The name of the OMD site to check the status for")), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage, "network_fs",
    _("Network filesystem - overall status (e.g. NFS)"),
    Dictionary(
        elements=[
            (
                "has_perfdata",
                DropdownChoice(
                    title=_("Performance data settings"),
                    choices=[
                        (True, _("Enable performance data")),
                        (False, _("Disable performance data")),
                    ],
                    default_value=False),
            ),
        ],),
    TextAscii(
        title=_("Name of the mount point"), help=_("For NFS enter the name of the mount point.")),
    "dict")

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "windows_multipath",
    _("Windows Multipath Count"),
    Alternative(
        help=_("This rules sets the expected number of active paths for a multipath LUN."),
        title=_("Expected number of active paths"),
        elements=[
            Integer(title=_("Expected number of active paths")),
            Tuple(
                title=_("Expected percentage of active paths"),
                elements=[
                    Integer(title=_("Expected number of active paths")),
                    Percentage(title=_("Warning if less then")),
                    Percentage(title=_("Critical if less then")),
                ]),
        ]),
    None,
    "first",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "multipath", _("Linux and Solaris Multipath Count"),
    Alternative(
        help=_("This rules sets the expected number of active paths for a multipath LUN "
               "on Linux and Solaris hosts"),
        title=_("Expected number of active paths"),
        elements=[
            Integer(title=_("Expected number of active paths")),
            Tuple(
                title=_("Expected percentage of active paths"),
                elements=[
                    Percentage(title=_("Warning if less then")),
                    Percentage(title=_("Critical if less then")),
                ]),
        ]),
    TextAscii(
        title=_("Name of the MP LUN"),
        help=_("For Linux multipathing this is either the UUID (e.g. "
               "60a9800043346937686f456f59386741), or the configured "
               "alias.")), "first")

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="inventory_multipath_rules",
    title=_("Linux Multipath Inventory"),
    valuespec=Dictionary(
        elements=[
            ("use_alias",
             Checkbox(
                 title=_("Use the multipath alias as service name, if one is set"),
                 label=_("use alias"),
                 help=_(
                     "If a multipath device has an alias then you can use it for specifying "
                     "the device instead of the UUID. The alias will then be part of the service "
                     "description. The UUID will be displayed in the plugin output."))),
        ],
        help=_(
            "This rule controls whether the UUID or the alias is used in the service description during "
            "discovery of Multipath devices on Linux."),
    ),
    match='dict',
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "multipath_count", _("ESX Multipath Count"),
    Alternative(
        help=_("This rules sets the expected number of active paths for a multipath LUN "
               "on ESX servers"),
        title=_("Match type"),
        elements=[
            FixedValue(
                None,
                title=_("OK if standby count is zero or equals active paths."),
                totext="",
            ),
            Dictionary(
                title=_("Custom settings"),
                elements=[
                    (element,
                     Transform(
                         Tuple(
                             title=description,
                             elements=[
                                 Integer(title=_("Critical if less than")),
                                 Integer(title=_("Warning if less than")),
                                 Integer(title=_("Warning if more than")),
                                 Integer(title=_("Critical if more than")),
                             ]),
                         forth=lambda x: len(x) == 2 and (0, 0, x[0], x[1]) or x))
                    for (element,
                         description) in [("active", _("Active paths")), (
                             "dead", _("Dead paths")), (
                                 "disabled", _("Disabled paths")), (
                                     "standby", _("Standby paths")), ("unknown",
                                                                      _("Unknown paths"))]
                ]),
        ]), TextAscii(title=_("Path ID")), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage, "hpux_multipath", _("HP-UX Multipath Count"),
    Tuple(
        title=_("Expected path situation"),
        help=_("This rules sets the expected number of various paths for a multipath LUN "
               "on HPUX servers"),
        elements=[
            Integer(title=_("Number of active paths")),
            Integer(title=_("Number of standby paths")),
            Integer(title=_("Number of failed paths")),
            Integer(title=_("Number of unopen paths")),
        ]), TextAscii(title=_("WWID of the LUN")), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "drbd",
    _("DR:BD roles and diskstates"),
    Dictionary(elements=[(
        "roles",
        Alternative(
            title=_("Roles"),
            elements=[
                FixedValue(None, totext="", title=_("Do not monitor")),
                ListOf(
                    Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("DRBD shows up as"),
                                default_value="running",
                                choices=[("primary_secondary", _("Primary / Secondary")
                                         ), ("primary_primary", _("Primary / Primary")
                                            ), ("secondary_primary", _("Secondary / Primary")
                                               ), ("secondary_secondary",
                                                   _("Secondary / Secondary"))]),
                            MonitoringState(title=_("Resulting state"),),
                        ],
                        default_value=("ignore", 0)),
                    title=_("Set roles"),
                    add_label=_("Add role rule"))
            ])),
                         (
                             "diskstates",
                             Alternative(
                                 title=_("Diskstates"),
                                 elements=[
                                     FixedValue(None, totext="", title=_("Do not monitor")),
                                     ListOf(
                                         Tuple(
                                             elements=[
                                                 DropdownChoice(
                                                     title=_("Diskstate"),
                                                     choices=[
                                                         ("primary_Diskless",
                                                          _("Primary - Diskless")),
                                                         ("primary_Attaching",
                                                          _("Primary - Attaching")),
                                                         ("primary_Failed", _("Primary - Failed")),
                                                         ("primary_Negotiating",
                                                          _("Primary - Negotiating")),
                                                         ("primary_Inconsistent",
                                                          _("Primary - Inconsistent")),
                                                         ("primary_Outdated",
                                                          _("Primary - Outdated")),
                                                         ("primary_DUnknown",
                                                          _("Primary - DUnknown")),
                                                         ("primary_Consistent",
                                                          _("Primary - Consistent")),
                                                         ("primary_UpToDate",
                                                          _("Primary - UpToDate")),
                                                         ("secondary_Diskless",
                                                          _("Secondary - Diskless")),
                                                         ("secondary_Attaching",
                                                          _("Secondary - Attaching")),
                                                         ("secondary_Failed",
                                                          _("Secondary - Failed")),
                                                         ("secondary_Negotiating",
                                                          _("Secondary - Negotiating")),
                                                         ("secondary_Inconsistent",
                                                          _("Secondary - Inconsistent")),
                                                         ("secondary_Outdated",
                                                          _("Secondary - Outdated")),
                                                         ("secondary_DUnknown",
                                                          _("Secondary - DUnknown")),
                                                         ("secondary_Consistent",
                                                          _("Secondary - Consistent")),
                                                         ("secondary_UpToDate",
                                                          _("Secondary - UpToDate")),
                                                     ]),
                                                 MonitoringState(title=_("Resulting state"))
                                             ],
                                             orientation="horizontal",
                                         ),
                                         title=_("Set diskstates"),
                                         add_label=_("Add diskstate rule"))
                                 ]),
                         )]),
    TextAscii(title=_("DRBD device")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "snapvault",
    _("NetApp Snapvaults / Snapmirror Lag Time"),
    Dictionary(
        elements=
        [(
            "lag_time",
            Tuple(
                title=_("Default levels"),
                elements=[
                    Age(title=_("Warning at")),
                    Age(title=_("Critical at")),
                ],
            ),
        ),
         ("policy_lag_time",
          ListOf(
              Tuple(
                  orientation="horizontal",
                  elements=[
                      TextAscii(title=_("Policy name")),
                      Tuple(
                          title=_("Maximum age"),
                          elements=[
                              Age(title=_("Warning at")),
                              Age(title=_("Critical at")),
                          ],
                      ),
                  ]),
              title=_('Policy specific levels (Clustermode only)'),
              help=_(
                  "Here you can specify levels for different policies which overrule the levels "
                  "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."
              ),
              allow_empty=False,
          ))],),
    TextAscii(title=_("Source Path"), allow_empty=False),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "netapp_snapshots",
    _("NetApp Snapshot Reserve"),
    Dictionary(
        elements=[
            ("levels",
             Tuple(
                 title=_("Levels for used configured reserve"),
                 elements=[
                     Percentage(title=_("Warning at or above"), unit="%", default_value=85.0),
                     Percentage(title=_("Critical at or above"), unit="%", default_value=90.0),
                 ])),
            ("state_noreserve", MonitoringState(title=_("State if no reserve is configured"),)),
        ],),
    TextAscii(title=_("Volume name")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "netapp_disks",
    _("Filer Disk Levels (NetApp, IBM SVC)"),
    Transform(
        Dictionary(
            elements=[
                ("failed_spare_ratio",
                 Tuple(
                     title=_("Failed to spare ratio"),
                     help=_("You can set a limit to the failed to spare disk ratio. "
                            "The ratio is calculated with <i>spare / (failed + spare)</i>."),
                     elements=[
                         Percentage(title=_("Warning at or above"), default_value=1.0),
                         Percentage(title=_("Critical at or above"), default_value=50.0),
                     ])),
                ("offline_spare_ratio",
                 Tuple(
                     title=_("Offline to spare ratio"),
                     help=_("You can set a limit to the offline to spare disk ratio. "
                            "The ratio is calculated with <i>spare / (offline + spare)</i>."),
                     elements=[
                         Percentage(title=_("Warning at or above"), default_value=1.0),
                         Percentage(title=_("Critical at or above"), default_value=50.0),
                     ])),
                ("number_of_spare_disks",
                 Tuple(
                     title=_("Number of spare disks"),
                     help=_("You can set a lower limit to the absolute number of spare disks."),
                     elements=[
                         Integer(title=_("Warning below"), default_value=2, min_value=0),
                         Integer(title=_("Critical below"), default_value=1, min_value=0),
                     ])),
            ],),
        forth=
        lambda a: "broken_spare_ratio" in a and {"failed_spare_ratio": a["broken_spare_ratio"]} or a
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "netapp_volumes",
    _("NetApp Volumes"),
    Dictionary(elements=[
        ("levels",
         Alternative(
             title=_("Levels for volume"),
             show_alternative_title=True,
             default_value=(80.0, 90.0),
             match=match_dual_level_type,
             elements=[
                 get_free_used_dynamic_valuespec("used", "volume"),
                 Transform(
                     get_free_used_dynamic_valuespec("free", "volume", default_value=(20.0, 10.0)),
                     allow_empty=False,
                     forth=transform_filesystem_free,
                     back=transform_filesystem_free)
             ])),
        ("perfdata",
         ListChoice(
             title=_("Performance data for protocols"),
             help=_("Specify for which protocol performance data should get recorded."),
             choices=[
                 ("", _("Summarized data of all protocols")),
                 ("nfs", _("NFS")),
                 ("cifs", _("CIFS")),
                 ("san", _("SAN")),
                 ("fcp", _("FCP")),
                 ("iscsi", _("iSCSI")),
             ],
         )),
        ("magic",
         Float(
             title=_("Magic factor (automatic level adaptation for large volumes)"),
             default_value=0.8,
             minvalue=0.1,
             maxvalue=1.0)),
        ("magic_normsize",
         Integer(
             title=_("Reference size for magic factor"), default_value=20, minvalue=1, unit=_("GB"))
        ),
        ("levels_low",
         Tuple(
             title=_("Minimum levels if using magic factor"),
             help=_("The volume levels will never fall below these values, when using "
                    "the magic factor and the volume is very small."),
             elements=[
                 Percentage(
                     title=_("Warning if above"),
                     unit=_("% usage"),
                     allow_int=True,
                     default_value=50),
                 Percentage(
                     title=_("Critical if above"),
                     unit=_("% usage"),
                     allow_int=True,
                     default_value=60)
             ])),
        ("inodes_levels",
         Alternative(
             title=_("Levels for Inodes"),
             help=_("The number of remaining inodes on the filesystem. "
                    "Please note that this setting has no effect on some filesystem checks."),
             elements=[
                 Tuple(
                     title=_("Percentage free"),
                     elements=[
                         Percentage(title=_("Warning if less than")),
                         Percentage(title=_("Critical if less than")),
                     ]),
                 Tuple(
                     title=_("Absolute free"),
                     elements=[
                         Integer(
                             title=_("Warning if less than"),
                             size=10,
                             unit=_("inodes"),
                             minvalue=0,
                             default_value=10000),
                         Integer(
                             title=_("Critical if less than"),
                             size=10,
                             unit=_("inodes"),
                             minvalue=0,
                             default_value=5000),
                     ])
             ],
             default_value=(10.0, 5.0),
         )),
        ("show_inodes",
         DropdownChoice(
             title=_("Display inode usage in check output..."),
             choices=[
                 ("onproblem", _("Only in case of a problem")),
                 ("onlow", _("Only in case of a problem or if inodes are below 50%")),
                 ("always", _("Always")),
             ],
             default_value="onlow",
         )),
        ("trend_range",
         Optional(
             Integer(
                 title=_("Time Range for filesystem trend computation"),
                 default_value=24,
                 minvalue=1,
                 unit=_("hours")),
             title=_("Trend computation"),
             label=_("Enable trend computation"))),
        ("trend_mb",
         Tuple(
             title=_("Levels on trends in MB per time range"),
             elements=[
                 Integer(title=_("Warning at"), unit=_("MB / range"), default_value=100),
                 Integer(title=_("Critical at"), unit=_("MB / range"), default_value=200)
             ])),
        ("trend_perc",
         Tuple(
             title=_("Levels for the percentual growth per time range"),
             elements=[
                 Percentage(
                     title=_("Warning at"),
                     unit=_("% / range"),
                     default_value=5,
                 ),
                 Percentage(
                     title=_("Critical at"),
                     unit=_("% / range"),
                     default_value=10,
                 ),
             ])),
        ("trend_timeleft",
         Tuple(
             title=_("Levels on the time left until the filesystem gets full"),
             elements=[
                 Integer(
                     title=_("Warning if below"),
                     unit=_("hours"),
                     default_value=12,
                 ),
                 Integer(
                     title=_("Critical if below"),
                     unit=_("hours"),
                     default_value=6,
                 ),
             ])),
        ("trend_showtimeleft",
         Checkbox(
             title=_("Display time left in check output"),
             label=_("Enable"),
             help=_("Normally, the time left until the disk is full is only displayed when "
                    "the configured levels have been breached. If you set this option "
                    "the check always reports this information"))),
        ("trend_perfdata",
         Checkbox(
             title=_("Trend performance data"),
             label=_("Enable generation of performance data from trends"))),
    ]),
    TextAscii(title=_("Volume name")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "netapp_luns",
    _("NetApp LUNs"),
    Dictionary(
        title=_("Configure levels for used space"),
        elements=[
            ("ignore_levels",
             FixedValue(
                 title=_("Ignore used space (this option disables any other options)"),
                 help=_(
                     "Some luns, e.g. jfs formatted, tend to report incorrect used space values"),
                 label=_("Ignore used space"),
                 value=True,
                 totext="",
             )),
            ("levels",
             Alternative(
                 title=_("Levels for LUN"),
                 show_alternative_title=True,
                 default_value=(80.0, 90.0),
                 match=match_dual_level_type,
                 elements=[
                     get_free_used_dynamic_valuespec("used", "LUN"),
                     Transform(
                         get_free_used_dynamic_valuespec("free", "LUN", default_value=(20.0, 10.0)),
                         allow_empty=False,
                         forth=transform_filesystem_free,
                         back=transform_filesystem_free,
                     )
                 ])),
            ("trend_range",
             Optional(
                 Integer(
                     title=_("Time Range for lun filesystem trend computation"),
                     default_value=24,
                     minvalue=1,
                     unit=_("hours")),
                 title=_("Trend computation"),
                 label=_("Enable trend computation"))),
            ("trend_mb",
             Tuple(
                 title=_("Levels on trends in MB per time range"),
                 elements=[
                     Integer(title=_("Warning at"), unit=_("MB / range"), default_value=100),
                     Integer(title=_("Critical at"), unit=_("MB / range"), default_value=200)
                 ])),
            ("trend_perc",
             Tuple(
                 title=_("Levels for the percentual growth per time range"),
                 elements=[
                     Percentage(
                         title=_("Warning at"),
                         unit=_("% / range"),
                         default_value=5,
                     ),
                     Percentage(
                         title=_("Critical at"),
                         unit=_("% / range"),
                         default_value=10,
                     ),
                 ])),
            ("trend_timeleft",
             Tuple(
                 title=_("Levels on the time left until the lun filesystem gets full"),
                 elements=[
                     Integer(
                         title=_("Warning if below"),
                         unit=_("hours"),
                         default_value=12,
                     ),
                     Integer(
                         title=_("Critical if below"),
                         unit=_("hours"),
                         default_value=6,
                     ),
                 ])),
            ("trend_showtimeleft",
             Checkbox(
                 title=_("Display time left in check output"),
                 label=_("Enable"),
                 help=_(
                     "Normally, the time left until the lun filesystem is full is only displayed when "
                     "the configured levels have been breached. If you set this option "
                     "the check always reports this information"))),
            ("trend_perfdata",
             Checkbox(
                 title=_("Trend performance data"),
                 label=_("Enable generation of performance data from trends"))),
            ("read_only",
             Checkbox(
                 title=_("LUN is read-only"),
                 help=_("Display a warning if a LUN is not read-only. Without "
                        "this setting a warning will be displayed if a LUN is "
                        "read-only."),
                 label=_("Enable"))),
        ]),
    TextAscii(title=_("LUN name")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "services",
    _("Windows Services"),
    Dictionary(elements=[
        ("additional_servicenames",
         ListOfStrings(
             title=_("Alternative names for the service"),
             help=_("Here you can specify alternative names that the service might have. "
                    "This helps when the exact spelling of the services can changed from "
                    "one version to another."),
         )),
        ("states",
         ListOf(
             Tuple(
                 orientation="horizontal",
                 elements=[
                     DropdownChoice(
                         title=_("Expected state"),
                         default_value="running",
                         choices=[(None,
                                   _("ignore the state")), ("running",
                                                            _("running")), ("stopped",
                                                                            _("stopped"))]),
                     DropdownChoice(
                         title=_("Start type"),
                         default_value="auto",
                         choices=[
                             (None, _("ignore the start type")),
                             ("demand",
                              _("demand")),
                             ("disabled", _("disabled")),
                             ("auto", _("auto")),
                             ("unknown", _("unknown (old agent)")),
                         ]),
                     MonitoringState(title=_("Resulting state"),),
                 ],
                 default_value=("running", "auto", 0)),
             title=_("Services states"),
             help=_("You can specify a separate monitoring state for each possible "
                    "combination of service state and start type. If you do not use "
                    "this parameter, then only running/auto will be assumed to be OK."),
         )), (
             "else",
             MonitoringState(
                 title=_("State if no entry matches"),
                 default_value=2,
             ),
         ),
        ('icon',
         UserIconOrAction(
             title=_("Add custom icon or action"),
             help=_("You can assign icons or actions to the found services in the status GUI."),
         ))
    ]),
    TextAscii(
        title=_("Name of the service"),
        help=_("Please Please note, that the agent replaces spaces in "
               "the service names with underscores. If you are unsure about the "
               "correct spelling of the name then please look at the output of "
               "the agent (cmk -d HOSTNAME). The service names  are in the first "
               "column of the section &lt;&lt;&lt;services&gt;&gt;&gt;. Please "
               "do not mix up the service name with the display name of the service."
               "The latter one is just being displayed as a further information."),
        allow_empty=False),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "solaris_services",
    _("Solaris Services"),
    Dictionary(
        elements=[
            ("additional_servicenames",
             ListOfStrings(
                 title=_("Alternative names for the service"),
                 help=_("Here you can specify alternative names that the service might have. "
                        "This helps when the exact spelling of the services can changed from "
                        "one version to another."),
             )),
            ("states",
             ListOf(
                 Tuple(
                     orientation="horizontal",
                     elements=[
                         DropdownChoice(
                             title=_("Expected state"),
                             choices=[
                                 (None, _("Ignore the state")),
                                 ("online", _("Online")),
                                 ("disabled", _("Disabled")),
                                 ("maintenance", _("Maintenance")),
                                 ("legacy_run", _("Legacy run")),
                             ]),
                         DropdownChoice(
                             title=_("STIME"),
                             choices=[
                                 (None, _("Ignore")),
                                 (True, _("Has changed")),
                                 (False, _("Did not changed")),
                             ]),
                         MonitoringState(title=_("Resulting state"),),
                     ],
                 ),
                 title=_("Services states"),
                 help=_("You can specify a separate monitoring state for each possible "
                        "combination of service state. If you do not use this parameter, "
                        "then only online/legacy_run will be assumed to be OK."),
             )),
            ("else", MonitoringState(
                title=_("State if no entry matches"),
                default_value=2,
            )),
        ],),
    TextAscii(title=_("Name of the service"), allow_empty=False),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "winperf_ts_sessions",
    _("Windows Terminal Server Sessions"),
    Dictionary(
        help=_("This check monitors number of active and inactive terminal "
               "server sessions."),
        elements=[
            (
                "active",
                Tuple(
                    title=_("Number of active sessions"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                    ],
                ),
            ),
            (
                "inactive",
                Tuple(
                    title=_("Number of inactive sessions"),
                    help=_("Levels for the number of sessions that are currently inactive"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=10),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=20),
                    ],
                ),
            ),
        ]),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "raid", _("RAID: overall state"), None,
    TextAscii(
        title=_("Name of the device"),
        help=_("For Linux MD specify the device name without the "
               "<tt>/dev/</tt>, e.g. <tt>md0</tt>, for hardware raids "
               "please refer to the manual of the actual check being used.")), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage, "raid_summary", _("RAID: summary state"),
    Dictionary(elements=[
        ("use_device_states",
         DropdownChoice(
             title=_("Use device states and overwrite expected status"),
             choices=[
                 (False, _("Ignore")),
                 (True, _("Use device states")),
             ],
             default_value=True,
         )),
    ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersStorage, "raid_disk", _("RAID: state of a single disk"),
    Transform(
        Dictionary(elements=[
            (
                "expected_state",
                TextAscii(
                    title=_("Expected state"),
                    help=_("State the disk is expected to be in. Typical good states "
                           "are online, host spare, OK and the like. The exact way of how "
                           "to specify a state depends on the check and hard type being used. "
                           "Please take examples from discovered checks for reference.")),
            ),
            ("use_device_states",
             DropdownChoice(
                 title=_("Use device states and overwrite expected status"),
                 choices=[
                     (False, _("Ignore")),
                     (True, _("Use device states")),
                 ],
                 default_value=True,
             )),
        ]),
        forth=lambda x: isinstance(x, str) and {"expected_state": x} or x,
    ),
    TextAscii(
        title=_("Number or ID of the disk"),
        help=_("How the disks are named depends on the type of hardware being "
               "used. Please look at already discovered checks for examples.")), "first")

register_check_parameters(
    RulespecGroupCheckParametersStorage, "pfm_health", _("PCIe flash module"),
    Dictionary(
        elements=[
            (
                "health_lifetime_perc",
                Tuple(
                    title=_("Lower levels for health lifetime"),
                    elements=[
                        Percentage(title=_("Warning if below"), default_value=10),
                        Percentage(title=_("Critical if below"), default_value=5)
                    ],
                ),
            ),
        ],),
    TextAscii(
        title=_("Number or ID of the disk"),
        help=_("How the disks are named depends on the type of hardware being "
               "used. Please look at already discovered checks for examples.")), "dict")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "switch_contact",
    _("Switch contact state"),
    DropdownChoice(
        help=_("This rule sets the required state of a switch contact"),
        label=_("Required switch contact state"),
        choices=[
            ("open", "Switch contact is <b>open</b>"),
            ("closed", "Switch contact is <b>closed</b>"),
            ("ignore", "Ignore switch contact state"),
        ],
    ),
    TextAscii(title=_("Sensor"), allow_empty=False),
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "plugs",
    _("State of PDU Plugs"),
    DropdownChoice(
        help=_("This rule sets the required state of a PDU plug. It is meant to "
               "be independent of the hardware manufacturer."),
        title=_("Required plug state"),
        choices=[
            ("on", _("Plug is ON")),
            ("off", _("Plug is OFF")),
        ],
        default_value="on"),
    TextAscii(
        title=_("Plug item number or name"),
        help=
        _("Whether you need the number or the name depends on the check. Just take a look to the service description."
         ),
        allow_empty=True),
    match_type="first",
)

# New temperature rule for modern temperature checks that have the
# sensor type (e.g. "CPU", "Chassis", etc.) as the beginning of their
# item (e.g. "CPU 1", "Chassis 17/11"). This will replace all other
# temperature rulesets in future. Note: those few temperature checks
# that do *not* use an item, need to be converted to use one single
# item (other than None).
register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "temperature",
    _("Temperature"),
    Transform(
        Dictionary(elements=[
            ("levels",
             Tuple(
                 title=_("Upper Temperature Levels"),
                 elements=[
                     Float(title=_("Warning at"), unit=u"°C", default_value=26),
                     Float(title=_("Critical at"), unit=u"°C", default_value=30),
                 ])),
            ("levels_lower",
             Tuple(
                 title=_("Lower Temperature Levels"),
                 elements=[
                     Float(title=_("Warning below"), unit=u"°C", default_value=0),
                     Float(title=_("Critical below"), unit=u"°C", default_value=-10),
                 ])),
            ("output_unit",
             DropdownChoice(
                 title=_("Display values in "),
                 choices=[
                     ("c", _("Celsius")),
                     ("f", _("Fahrenheit")),
                     ("k", _("Kelvin")),
                 ])),
            ("input_unit",
             DropdownChoice(
                 title=_("Override unit of sensor"),
                 help=_("In some rare cases the unit that is signalled by the sensor "
                        "is wrong and e.g. the sensor sends values in Fahrenheit while "
                        "they are misinterpreted as Celsius. With this setting you can "
                        "force the reading of the sensor to be interpreted as customized. "),
                 choices=[
                     ("c", _("Celsius")),
                     ("f", _("Fahrenheit")),
                     ("k", _("Kelvin")),
                 ])),
            ("device_levels_handling",
             DropdownChoice(
                 title=_("Interpretation of the device's own temperature status"),
                 choices=[
                     ("usr", _("Ignore device's own levels")),
                     ("dev", _("Only use device's levels, ignore yours")),
                     ("best", _("Use least critical of your and device's levels")),
                     ("worst", _("Use most critical of your and device's levels")),
                     ("devdefault", _("Use device's levels if present, otherwise yours")),
                     ("usrdefault", _("Use your own levels if present, otherwise the device's")),
                 ],
                 default_value="usrdefault",
             )),
            (
                "trend_compute",
                Dictionary(
                    title=_("Trend computation"),
                    label=_("Enable trend computation"),
                    elements=[
                        ("period",
                         Integer(
                             title=_("Observation period for temperature trend computation"),
                             default_value=30,
                             minvalue=5,
                             unit=_("minutes"))),
                        ("trend_levels",
                         Tuple(
                             title=_("Levels on temperature increase per period"),
                             elements=[
                                 Integer(
                                     title=_("Warning at"),
                                     unit=u"°C / " + _("period"),
                                     default_value=5),
                                 Integer(
                                     title=_("Critical at"),
                                     unit=u"°C / " + _("period"),
                                     default_value=10)
                             ])),
                        ("trend_levels_lower",
                         Tuple(
                             title=_("Levels on temperature decrease per period"),
                             elements=[
                                 Integer(
                                     title=_("Warning at"),
                                     unit=u"°C / " + _("period"),
                                     default_value=5),
                                 Integer(
                                     title=_("Critical at"),
                                     unit=u"°C / " + _("period"),
                                     default_value=10)
                             ])),
                        ("trend_timeleft",
                         Tuple(
                             title=
                             _("Levels on the time left until a critical temperature (upper or lower) is reached"
                              ),
                             elements=[
                                 Integer(
                                     title=_("Warning if below"),
                                     unit=_("minutes"),
                                     default_value=240,
                                 ),
                                 Integer(
                                     title=_("Critical if below"),
                                     unit=_("minutes"),
                                     default_value=120,
                                 ),
                             ]))
                    ],
                    optional_keys=["trend_levels", "trend_levels_lower", "trend_timeleft"],
                ),
            ),
        ]),
        forth=lambda v: isinstance(v, tuple) and {"levels": v} or v,
    ),
    TextAscii(title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "room_temperature",
    _("Room temperature (external thermal sensors)"),
    Tuple(
        help=_("Temperature levels for external thermometers that are used "
               "for monitoring the temperature of a datacenter. An example "
               "is the webthem from W&T."),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=26),
            Integer(title=_("critical at"), unit=u"°C", default_value=30),
        ]),
    TextAscii(title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "hw_single_temperature",
    _("Host/Device temperature"),
    Tuple(
        help=_("Temperature levels for hardware devices with "
               "a single temperature sensor."),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=35),
            Integer(title=_("critical at"), unit=u"°C", default_value=40),
        ]),
    None,
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "evolt",
    _("Voltage levels (UPS / PDU / Other Devices)"),
    Tuple(
        help=_("Voltage Levels for devices like UPS or PDUs. "
               "Several phases may be addressed independently."),
        elements=[
            Integer(title=_("warning if below"), unit="V", default_value=210),
            Integer(title=_("critical if below"), unit="V", default_value=180),
        ]),
    TextAscii(title=_("Phase"),
              help=_("The identifier of the phase the power is related to.")), "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "efreq", _("Nominal Frequencies"),
    Tuple(
        help=_("Levels for the nominal frequencies of AC devices "
               "like UPSs or PDUs. Several phases may be addressed independently."),
        elements=[
            Integer(title=_("warning if below"), unit="Hz", default_value=40),
            Integer(title=_("critical if below"), unit="Hz", default_value=45),
        ]),
    TextAscii(title=_("Phase"), help=_("The identifier of the phase the power is related to.")),
    "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "epower", _("Electrical Power"),
    Tuple(
        help=_("Levels for the electrical power consumption of a device "
               "like a UPS or a PDU. Several phases may be addressed independently."),
        elements=[
            Integer(title=_("warning if below"), unit="Watt", default_value=20),
            Integer(title=_("critical if below"), unit="Watt", default_value=1),
        ]),
    TextAscii(title=_("Phase"), help=_("The identifier of the phase the power is related to.")),
    "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "ups_out_load",
    _("Parameters for output loads of UPSs and PDUs"),
    Tuple(elements=[
        Integer(title=_("warning at"), unit=u"%", default_value=85),
        Integer(title=_("critical at"), unit=u"%", default_value=90),
    ]), TextAscii(title=_("Phase"), help=_("The identifier of the phase the power is related to.")),
    "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "epower_single",
    _("Electrical Power for Devices with only one phase"),
    Tuple(
        help=_("Levels for the electrical power consumption of a device "),
        elements=[
            Integer(title=_("warning if at"), unit="Watt", default_value=300),
            Integer(title=_("critical if at"), unit="Watt", default_value=400),
        ]), None, "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "hw_temperature",
    _("Hardware temperature, multiple sensors"),
    Tuple(
        help=_("Temperature levels for hardware devices like "
               "Brocade switches with (potentially) several "
               "temperature sensors. Sensor IDs can be selected "
               "in the rule."),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=35),
            Integer(title=_("critical at"), unit=u"°C", default_value=40),
        ]),
    TextAscii(title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "hw_temperature_single",
    _("Hardware temperature, single sensor"),
    Tuple(
        help=_("Temperature levels for hardware devices like "
               "DELL Powerconnect that have just one temperature sensor. "),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=35),
            Integer(title=_("critical at"), unit=u"°C", default_value=40),
        ]),
    None,
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "disk_temperature",
    _("Harddisk temperature (e.g. via SMART)"),
    Tuple(
        help=_("Temperature levels for hard disks, that is determined e.g. via SMART"),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=35),
            Integer(title=_("critical at"), unit=u"°C", default_value=40),
        ]),
    TextAscii(
        title=_("Hard disk device"),
        help=_("The identificator of the hard disk device, e.g. <tt>/dev/sda</tt>.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "eaton_enviroment",
    _("Temperature and Humidity for Eaton UPS"),
    Dictionary(elements=[
        ("temp",
         Tuple(
             title=_("Temperature"),
             elements=[
                 Integer(title=_("warning at"), unit=u"°C", default_value=26),
                 Integer(title=_("critical at"), unit=u"°C", default_value=30),
             ])),
        ("remote_temp",
         Tuple(
             title=_("Remote Temperature"),
             elements=[
                 Integer(title=_("warning at"), unit=u"°C", default_value=26),
                 Integer(title=_("critical at"), unit=u"°C", default_value=30),
             ])),
        ("humidity",
         Tuple(
             title=_("Humidity"),
             elements=[
                 Integer(title=_("warning at"), unit=u"%", default_value=60),
                 Integer(title=_("critical at"), unit=u"%", default_value=75),
             ])),
    ]), None, "dict")

phase_elements = [
    ("voltage",
     Tuple(
         title=_("Voltage"),
         elements=[
             Integer(title=_("warning if below"), unit=u"V", default_value=210),
             Integer(title=_("critical if below"), unit=u"V", default_value=200),
         ],
     )),
    ("power",
     Tuple(
         title=_("Power"),
         elements=[
             Integer(title=_("warning at"), unit=u"W", default_value=1000),
             Integer(title=_("critical at"), unit=u"W", default_value=1200),
         ],
     )),
    ("appower",
     Tuple(
         title=_("Apparent Power"),
         elements=[
             Integer(title=_("warning at"), unit=u"VA", default_value=1100),
             Integer(title=_("critical at"), unit=u"VA", default_value=1300),
         ],
     )),
    ("current",
     Tuple(
         title=_("Current"),
         elements=[
             Integer(title=_("warning at"), unit=u"A", default_value=5),
             Integer(title=_("critical at"), unit=u"A", default_value=10),
         ],
     )),
    ("frequency",
     Tuple(
         title=_("Frequency"),
         elements=[
             Integer(title=_("warning if below"), unit=u"Hz", default_value=45),
             Integer(title=_("critical if below"), unit=u"Hz", default_value=40),
             Integer(title=_("warning if above"), unit=u"Hz", default_value=55),
             Integer(title=_("critical if above"), unit=u"Hz", default_value=60),
         ],
     )),
    ("differential_current_ac",
     Tuple(
         title=_("Differential current AC"),
         elements=[
             Float(title=_("warning at"), unit=u"mA", default_value=3.5),
             Float(title=_("critical at"), unit=u"mA", default_value=30),
         ],
     )),
    ("differential_current_dc",
     Tuple(
         title=_("Differential current DC"),
         elements=[
             Float(title=_("warning at"), unit=u"mA", default_value=70),
             Float(title=_("critical at"), unit=u"mA", default_value=100),
         ],
     )),
]

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "ups_outphase",
    _("Parameters for output phases of UPSs and PDUs"),
    Dictionary(
        help=_("This rule allows you to specify levels for the voltage, current, load, power "
               "and apparent power of your device. The levels will only be applied if the device "
               "actually supplies values for these parameters."),
        elements=phase_elements + [
            ("load",
             Tuple(
                 title=_("Load"),
                 elements=[
                     Integer(title=_("warning at"), unit=u"%", default_value=80),
                     Integer(title=_("critical at"), unit=u"%", default_value=90),
                 ])),
            ("map_device_states",
             ListOf(
                 Tuple(elements=[TextAscii(size=10), MonitoringState()]),
                 title=_("Map device state"),
                 help=_("Here you can enter either device state number (eg. from SNMP devices) "
                        "or exact device state name and the related monitoring state."),
             )),
        ]),
    TextAscii(
        title=_("Output Name"),
        help=_("The name of the output, e.g. <tt>Phase 1</tt>/<tt>PDU 1</tt>")), "dict")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "el_inphase",
    _("Parameters for input phases of UPSs and PDUs"),
    Dictionary(
        help=_("This rule allows you to specify levels for the voltage, current, power "
               "and apparent power of your device. The levels will only be applied if the device "
               "actually supplies values for these parameters."),
        elements=phase_elements + [
            ("map_device_states",
             ListOf(
                 Tuple(elements=[TextAscii(size=10), MonitoringState()]),
                 title=_("Map device state"),
                 help=_("Here you can enter either device state number (eg. from SNMP devices) "
                        "or exact device state name and the related monitoring state."),
             )),
        ],
    ), TextAscii(title=_("Input Name"), help=_("The name of the input, e.g. <tt>Phase 1</tt>")),
    "dict")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "hw_fans",
    _("FAN speed of Hardware devices"),
    Dictionary(
        elements=[
            (
                "lower",
                Tuple(
                    help=_("Lower levels for the fan speed of a hardware device"),
                    title=_("Lower levels"),
                    elements=[
                        Integer(title=_("warning if below"), unit=u"rpm"),
                        Integer(title=_("critical if below"), unit=u"rpm"),
                    ]),
            ),
            (
                "upper",
                Tuple(
                    help=_("Upper levels for the fan speed of a hardware device"),
                    title=_("Upper levels"),
                    elements=[
                        Integer(title=_("warning at"), unit=u"rpm", default_value=8000),
                        Integer(title=_("critical at"), unit=u"rpm", default_value=8400),
                    ]),
            ),
            ("output_metrics",
             Checkbox(title=_("Performance data"), label=_("Enable performance data"))),
        ],
        optional_keys=["upper"],
    ),
    TextAscii(title=_("Fan Name"), help=_("The identificator of the fan.")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "hw_fans_perc",
    _("Fan speed of hardware devices (in percent)"),
    Dictionary(elements=[
        ("levels",
         Tuple(
             title=_("Upper fan speed levels"),
             elements=[
                 Percentage(title=_("warning if at")),
                 Percentage(title=_("critical if at")),
             ])),
        ("levels_lower",
         Tuple(
             title=_("Lower fan speed levels"),
             elements=[
                 Percentage(title=_("warning if below")),
                 Percentage(title=_("critical if below")),
             ])),
    ]),
    TextAscii(title=_("Fan Name"), help=_("The identifier of the fan.")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem,
    "pf_used_states",
    _("Number of used states of OpenBSD PF engine"),
    Dictionary(
        elements=[
            (
                "used",
                Tuple(
                    title=_("Limits for the number of used states"),
                    elements=[
                        Integer(title=_("warning at")),
                        Integer(title=_("critical at")),
                    ]),
            ),
        ],
        optional_keys=[None],
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "pdu_gude",
    _("Levels for Gude PDU Devices"),
    Dictionary(elements=[
        ("kWh",
         Tuple(
             title=_("Total accumulated Active Energy of Power Channel"),
             elements=[
                 Integer(title=_("warning at"), unit=_("kW")),
                 Integer(title=_("critical at"), unit=_("kW")),
             ])),
        ("W",
         Tuple(
             title=_("Active Power"),
             elements=[
                 Integer(title=_("warning at"), unit=_("W")),
                 Integer(title=_("critical at"), unit=_("W")),
             ])),
        ("A",
         Tuple(
             title=_("Current on Power Channel"),
             elements=[
                 Integer(title=_("warning at"), unit=_("A")),
                 Integer(title=_("critical at"), unit=_("A")),
             ])),
        ("V",
         Tuple(
             title=_("Voltage on Power Channel"),
             elements=[
                 Integer(title=_("warning if below"), unit=_("V")),
                 Integer(title=_("critical if below"), unit=_("V")),
             ])),
        ("VA",
         Tuple(
             title=_("Line Mean Apparent Power"),
             elements=[
                 Integer(title=_("warning at"), unit=_("VA")),
                 Integer(title=_("critical at"), unit=_("VA")),
             ])),
    ]),
    TextAscii(title=_("Phase Number"), help=_("The Number of the power Phase.")),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "hostsystem_sensors", _("Hostsystem sensor alerts"),
    ListOf(
        Dictionary(
            help=_("This rule allows to override alert levels for the given sensor names."),
            elements=[
                ("name", TextAscii(title=_("Sensor name"))),
                ("states",
                 Dictionary(
                     title=_("Custom states"),
                     elements=[(element,
                                MonitoringState(
                                    title="Sensor %s" % description,
                                    label=_("Set state to"),
                                    default_value=int(element)))
                               for (element, description) in [("0", _("OK")), (
                                   "1", _("WARNING")), ("2", _("CRITICAL")), ("3", _("UNKNOWN"))]],
                 ))
            ],
            optional_keys=False),
        add_label=_("Add sensor name")), None, "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "netapp_instance", _("Netapp Instance State"),
    ListOf(
        Dictionary(
            help=_("This rule allows you to override netapp warnings"),
            elements=[("name", TextAscii(title=_("Warning starts with"))),
                      ("state", MonitoringState(title="Set state to", default_value=1))],
            optional_keys=False),
        add_label=_("Add warning")), None, "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "temperature_auto",
    _("Temperature sensors with builtin levels"),
    None,
    TextAscii(title=_("Sensor ID"), help=_("The identificator of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "temperature_trends",
    _("Temperature trends for devices with builtin levels"),
    Dictionary(
        title=_("Temperature Trend Analysis"),
        help=_(
            "This rule enables and configures a trend analysis and corresponding limits for devices, "
            "which have their own limits configured on the device. It will only work for supported "
            "checks, right now the <tt>adva_fsp_temp</tt> check."),
        elements=[
            ("trend_range",
             Optional(
                 Integer(
                     title=_("Time range for temperature trend computation"),
                     default_value=30,
                     minvalue=5,
                     unit=_("minutes")),
                 title=_("Trend computation"),
                 label=_("Enable trend computation"))),
            ("trend_c",
             Tuple(
                 title=_("Levels on trends in degrees Celsius per time range"),
                 elements=[
                     Integer(title=_("Warning at"), unit=u"°C / " + _("range"), default_value=5),
                     Integer(title=_("Critical at"), unit=u"°C / " + _("range"), default_value=10)
                 ])),
            ("trend_timeleft",
             Tuple(
                 title=_("Levels on the time left until limit is reached"),
                 elements=[
                     Integer(
                         title=_("Warning if below"),
                         unit=_("minutes"),
                         default_value=240,
                     ),
                     Integer(
                         title=_("Critical if below"),
                         unit=_("minutes"),
                         default_value=120,
                     ),
                 ])),
        ]),
    TextAscii(title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")),
    "dict",
    deprecated=True,
)
ntp_params = Tuple(
    title=_("Thresholds for quality of time"),
    elements=[
        Integer(
            title=_("Critical at stratum"),
            default_value=10,
            help=_(
                "The stratum (\"distance\" to the reference clock) at which the check gets critical."
            ),
        ),
        Float(
            title=_("Warning at"),
            unit=_("ms"),
            default_value=200.0,
            help=_("The offset in ms at which a warning state is triggered."),
        ),
        Float(
            title=_("Critical at"),
            unit=_("ms"),
            default_value=500.0,
            help=_("The offset in ms at which a critical state is triggered."),
        ),
    ])

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem, "ntp_time", _("State of NTP time synchronisation"),
    Transform(
        Dictionary(elements=[
            (
                "ntp_levels",
                ntp_params,
            ),
            ("alert_delay",
             Tuple(
                 title=_("Phases without synchronization"),
                 elements=[
                     Age(
                         title=_("Warning at"),
                         display=["hours", "minutes"],
                         default_value=300,
                     ),
                     Age(
                         title=_("Critical at"),
                         display=["hours", "minutes"],
                         default_value=3600,
                     ),
                 ])),
        ]),
        forth=lambda params: isinstance(params, tuple) and {"ntp_levels": params} or params), None,
    "dict")

register_check_parameters(RulespecGroupCheckParametersOperatingSystem, "ntp_peer",
                          _("State of NTP peer"), ntp_params,
                          TextAscii(title=_("Name of the peer")), "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "smoke",
    _("Smoke Detection"),
    Tuple(
        help=_("For devices which measure smoke in percent"),
        elements=[
            Percentage(title=_("Warning at"), allow_int=True, default_value=1),
            Percentage(title=_("Critical at"), allow_int=True, default_value=5),
        ]),
    TextAscii(title=_("Sensor ID"), help=_("The identifier of the sensor.")),
    "first",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "apc_ats_output",
    _("APC Automatic Transfer Switch Output"),
    Dictionary(
        title=_("Levels for ATS Output parameters"),
        optional_keys=True,
        elements=[
            ("output_voltage_max",
             Tuple(
                 title=_("Maximum Levels for Voltage"),
                 elements=[
                     Integer(title=_("Warning at"), unit="Volt"),
                     Integer(title=_("Critical at"), unit="Volt"),
                 ])),
            ("output_voltage_min",
             Tuple(
                 title=_("Minimum Levels for Voltage"),
                 elements=[
                     Integer(title=_("Warning if below"), unit="Volt"),
                     Integer(title=_("Critical if below"), unit="Volt"),
                 ])),
            ("load_perc_max",
             Tuple(
                 title=_("Maximum Levels for load in percent"),
                 elements=[
                     Percentage(title=_("Warning at")),
                     Percentage(title=_("Critical at")),
                 ])),
            ("load_perc_min",
             Tuple(
                 title=_("Minimum Levels for load in percent"),
                 elements=[
                     Percentage(title=_("Warning if below")),
                     Percentage(title=_("Critical if below")),
                 ])),
        ],
    ),
    TextAscii(title=_("ID of phase")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "airflow",
    _("Airflow levels"),
    Dictionary(
        title=_("Levels for airflow"),
        elements=[
            ("level_low",
             Tuple(
                 title=_("Lower levels"),
                 elements=[
                     Float(
                         title=_("Warning if below"),
                         unit=_("l/s"),
                         default_value=5.0,
                         allow_int=True),
                     Float(
                         title=_("Critical if below"),
                         unit=_("l/s"),
                         default_value=2.0,
                         allow_int=True)
                 ])),
            ("level_high",
             Tuple(
                 title=_("Upper levels"),
                 elements=[
                     Float(
                         title=_("Warning at"), unit=_("l/s"), default_value=10.0, allow_int=True),
                     Float(
                         title=_("Critical at"), unit=_("l/s"), default_value=11.0, allow_int=True)
                 ])),
        ]),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "ups_capacity",
    _("UPS Capacity"),
    Dictionary(
        title=_("Levels for battery parameters"),
        optional_keys=False,
        elements=[(
            "capacity",
            Tuple(
                title=_("Battery capacity"),
                elements=[
                    Integer(
                        title=_("Warning at"),
                        help=
                        _("The battery capacity in percent at and below which a warning state is triggered"
                         ),
                        unit="%",
                        default_value=95,
                    ),
                    Integer(
                        title=_("Critical at"),
                        help=
                        _("The battery capacity in percent at and below which a critical state is triggered"
                         ),
                        unit="%",
                        default_value=90,
                    ),
                ],
            ),
        ),
                  (
                      "battime",
                      Tuple(
                          title=_("Time left on battery"),
                          elements=[
                              Integer(
                                  title=_("Warning at"),
                                  help=
                                  _("Time left on Battery at and below which a warning state is triggered"
                                   ),
                                  unit=_("min"),
                                  default_value=0,
                              ),
                              Integer(
                                  title=_("Critical at"),
                                  help=
                                  _("Time Left on Battery at and below which a critical state is triggered"
                                   ),
                                  unit=_("min"),
                                  default_value=0,
                              ),
                          ],
                      ),
                  )],
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "mbg_lantime_state",
    _("Meinberg Lantime State"),
    Dictionary(
        title=_("Meinberg Lantime State"),
        elements=[
            ("stratum",
             Tuple(
                 title=_("Warning levels for Stratum"),
                 elements=[
                     Integer(
                         title=_("Warning at"),
                         default_value=2,
                     ),
                     Integer(
                         title=_("Critical at"),
                         default_value=3,
                     ),
                 ])),
            ("offset",
             Tuple(
                 title=_("Warning levels for Time Offset"),
                 elements=[
                     Integer(
                         title=_("Warning at"),
                         unit=_("microseconds"),
                         default_value=10,
                     ),
                     Integer(
                         title=_("Critical at"),
                         unit=_("microseconds"),
                         default_value=20,
                     ),
                 ])),
        ]),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "sansymphony_pool", _("Sansymphony: pool allocation"),
    Tuple(
        help=_("This rule sets the warn and crit levels for the percentage of allocated pools"),
        elements=[
            Integer(
                title=_("Warning at"),
                unit=_("percent"),
                default_value=80,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("percent"),
                default_value=90,
            ),
        ]), TextAscii(title=_("Name of the pool"),), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "sansymphony_alerts",
    _("Sansymphony: Number of unacknowlegded alerts"),
    Tuple(
        help=_("This rule sets the warn and crit levels for the number of unacknowlegded alerts"),
        elements=[
            Integer(
                title=_("Warning at"),
                unit=_("alerts"),
                default_value=1,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("alerts"),
                default_value=2,
            ),
        ]), None, "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "jvm_threads", _("JVM threads"),
    Tuple(
        help=_("This rule sets the warn and crit levels for the number of threads "
               "running in a JVM."),
        elements=[
            Integer(
                title=_("Warning at"),
                unit=_("threads"),
                default_value=80,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("threads"),
                default_value=100,
            ),
        ]),
    TextAscii(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    ), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "sym_brightmail_queues",
    "Symantec Brightmail Queues",
    Dictionary(
        help=_("This check is used to monitor successful email delivery through "
               "Symantec Brightmail Scanner appliances."),
        elements=[
            ("connections",
             Tuple(
                 title=_("Number of connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ])),
            ("messageRate",
             Tuple(
                 title=_("Number of messages delivered"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ])),
            ("dataRate",
             Tuple(
                 title=_("Amount of data processed"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Cricital at")),
                 ])),
            ("queuedMessages",
             Tuple(
                 title=_("Number of messages currently queued"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ])),
            ("queueSize",
             Tuple(
                 title=_("Size of the queue"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ])),
            ("deferredMessages",
             Tuple(
                 title=_("Number of messages in deferred state"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ])),
        ],
    ),
    TextAscii(title=_("Instance name"), allow_empty=True),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "db2_logsize", _("DB2 logfile usage"),
    Dictionary(elements=[(
        "levels",
        Transform(
            get_free_used_dynamic_valuespec("free", "logfile", default_value=(20.0, 10.0)),
            title=_("Logfile levels"),
            allow_empty=False,
            forth=transform_filesystem_free,
            back=transform_filesystem_free))]),
    TextAscii(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")),
    "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "db2_sortoverflow",
    _("DB2 Sort Overflow"),
    Dictionary(
        help=_("This rule allows you to set percentual limits for sort overflows."),
        elements=[
            (
                "levels_perc",
                Tuple(
                    title=_("Overflows"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%"), default_value=2.0),
                        Percentage(title=_("Critical at"), unit=_("%"), default_value=4.0),
                    ],
                ),
            ),
        ]),
    TextAscii(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "db2_connections", _("DB2 Connections"),
    Dictionary(
        help=_("This rule allows you to set limits for the maximum number of DB2 connections"),
        elements=[
            (
                "levels_total",
                Tuple(
                    title=_("Number of current connections"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("connections"), default_value=150),
                        Integer(title=_("Critical at"), unit=_("connections"), default_value=200),
                    ],
                ),
            ),
        ]),
    TextAscii(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")),
    "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "db2_counters",
    _("DB2 Counters"),
    Dictionary(
        help=_("This rule allows you to configure limits for the deadlocks and lockwaits "
               "counters of a DB2."),
        elements=[
            (
                "deadlocks",
                Tuple(
                    title=_("Deadlocks"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("deadlocks/sec")),
                        Float(title=_("Critical at"), unit=_("deadlocks/sec")),
                    ],
                ),
            ),
            (
                "lockwaits",
                Tuple(
                    title=_("Lockwaits"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("lockwaits/sec")),
                        Float(title=_("Critical at"), unit=_("lockwaits/sec")),
                    ],
                ),
            ),
        ]),
    TextAscii(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")),
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "db2_backup",
    _("DB2 Time since last database Backup"),
    Optional(
        Tuple(elements=[
            Age(title=_("Warning at"),
                display=["days", "hours", "minutes"],
                default_value=86400 * 14),
            Age(title=_("Critical at"),
                display=["days", "hours", "minutes"],
                default_value=86400 * 28)
        ]),
        title=_("Specify time since last successful backup"),
    ),
    TextAscii(
        title=_("Instance"),
        help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "db2_mem", _("Memory levels for DB2 memory usage"),
    Tuple(
        elements=[
            Percentage(title=_("Warning if less than"), unit=_("% memory left")),
            Percentage(title=_("Critical if less than"), unit=_("% memory left")),
        ],), TextAscii(title=_("Instance name"), allow_empty=True), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "windows_updates", _("WSUS (Windows Updates)"),
    Tuple(
        title=_("Parameters for the Windows Update Check with WSUS"),
        help=_("Set the according numbers to 0 if you want to disable alerting."),
        elements=[
            Integer(title=_("Warning if at least this number of important updates are pending")),
            Integer(title=_("Critical if at least this number of important updates are pending")),
            Integer(title=_("Warning if at least this number of optional updates are pending")),
            Integer(title=_("Critical if at least this number of optional updates are pending")),
            Age(title=_("Warning if time until forced reboot is less then"), default_value=604800),
            Age(title=_("Critical if time time until forced reboot is less then"),
                default_value=172800),
            Checkbox(title=_("display all important updates verbosely"), default_value=True),
        ],
    ), None, "first")

synology_update_states = [
    (1, "Available"),
    (2, "Unavailable"),
    (4, "Disconnected"),
    (5, "Others"),
]

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "synology_update",
    _("Synology Updates"),
    Dictionary(
        title=_("Update State"),
        elements=[
            ("ok_states",
             ListChoice(
                 title=_("States which result in OK"),
                 choices=synology_update_states,
                 default_value=[2])),
            ("warn_states",
             ListChoice(
                 title=_("States which result in Warning"),
                 choices=synology_update_states,
                 default_value=[5])),
            ("crit_states",
             ListChoice(
                 title=_("States which result in Critical"),
                 choices=synology_update_states,
                 default_value=[1, 4])),
        ],
        optional_keys=None,
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "antivir_update_age",
    _("Age of last AntiVirus update"),
    Tuple(
        title=_("Age of last AntiVirus update"),
        elements=[
            Age(title=_("Warning level for time since last update")),
            Age(title=_("Critical level for time since last update")),
        ]), None, "first")

register_check_parameters(RulespecGroupCheckParametersApplications,
    "logwatch_ec",
    _('Logwatch Event Console Forwarding'),
    Alternative(
        title = _("Forwarding"),
        help = _("Instead of using the regular logwatch check all lines received by logwatch can "
                 "be forwarded to a Check_MK event console daemon to be processed. The target event "
                 "console can be configured for each host in a separate rule."),
        style = "dropdown",
        elements = [
            FixedValue(
                "",
                totext = _("Messages are handled by logwatch."),
                title = _("No forwarding"),
            ),
            Dictionary(
                title = _('Forward Messages to Event Console'),
                elements = [
                    ('method', Transform(
                        # TODO: Clean this up to some CascadingDropdown()
                        Alternative(
                            style = "dropdown",
                            title = _("Forwarding Method"),
                            elements = [
                                FixedValue(
                                    "",
                                    title = _("Local: Send events to local Event Console in same OMD site"),
                                    totext = _("Directly forward to Event Console"),
                                ),
                                TextAscii(
                                    title = _("Local: Send events to local Event Console into unix socket"),
                                    allow_empty = False,
                                ),

                                FixedValue(
                                    "spool:",
                                    title = _("Local: Spooling - Send events to local event console in same OMD site"),
                                    totext = _("Spool to Event Console"),
                                ),
                                Transform(
                                    TextAscii(),
                                    title = _("Local: Spooling - Send events to local Event Console into given spool directory"),
                                    allow_empty = False,
                                    forth = lambda x: x[6:],        # remove prefix
                                    back  = lambda x: "spool:" + x, # add prefix
                                ),
                                CascadingDropdown(
                                    title = _("Remote: Send events to remote syslog host"),
                                    choices = [
                                        ("tcp", _("Send via TCP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                                ("spool", Dictionary(
                                                    title = _("Spool messages that could not be sent"),
                                                    help = _("Messages that can not be forwarded, e.g. when the target Event Console is "
                                                             "not running, can temporarily be stored locally. Forwarding is tried again "
                                                             "on next execution. When messages are spooled, the check will go into WARNING "
                                                             "state. In case messages are dropped by the rules below, the check will shortly "
                                                             "go into CRITICAL state for this execution."),
                                                    elements = [
                                                        ("max_age", Age(
                                                            title = _("Maximum spool duration"),
                                                            help = _("Messages that are spooled longer than this time will be thrown away."),
                                                            default_value = 60*60*24*7, # 1 week should be fine (if size is not exceeded)
                                                        )),
                                                        ("max_size", Filesize(
                                                            title = _("Maximum spool size"),
                                                            help = _("When the total size of spooled messages exceeds this number, the oldest "
                                                                     "messages of the currently spooled messages is thrown away until the left "
                                                                     "messages have the half of the maximum size."),
                                                            default_value = 500000, # do not save more than 500k of message
                                                        )),
                                                    ],
                                                    optional_keys = [],
                                                )),
                                            ],
                                            optional_keys = [ "spool" ],
                                        )),
                                        ("udp", _("Send via UDP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                            ],
                                            optional_keys = [],
                                        )),
                                    ],
                                ),
                            ],
                            match = lambda x: 4 if isinstance(x, tuple) else (0 if not x else (2 if x == 'spool:' else (3 if x.startswith('spool:') else 1)))
                        ),
                        # migrate old (tcp, address, port) tuple to new dict
                        forth = lambda v: (v[0], {"address": v[1], "port": v[2]}) if (isinstance(v, tuple) and not isinstance(v[1], dict)) else v,
                    )),
                    ('facility', DropdownChoice(
                        title = _("Syslog facility for forwarded messages"),
                        help = _("When forwarding messages and no facility can be extracted from the "
                                 "message this facility is used."),
                        choices = mkeventd.syslog_facilities,
                        default_value = 17, # local1
                    )),
                    ('restrict_logfiles',
                        ListOfStrings(
                            title = _('Restrict Logfiles (Prefix matching regular expressions)'),
                            help  = _("Put the item names of the logfiles here. For example \"System$\" "
                                      "to select the service \"LOG System\". You can use regular expressions "
                                      "which must match the beginning of the logfile name."),
                        ),
                    ),
                    ('monitor_logfilelist',
                        Checkbox(
                            title =  _("Monitoring of forwarded logfiles"),
                            label = _("Warn if list of forwarded logfiles changes"),
                            help = _("If this option is enabled, the check monitors the list of forwarded "
                                  "logfiles and will warn you if at any time a logfile is missing or exceeding "
                                  "when compared to the initial list that was snapshotted during service detection. "
                                  "Reinventorize this check in order to make it OK again."),
                     )
                    ),
                    ('expected_logfiles',
                        ListOfStrings(
                            title = _("List of expected logfiles"),
                            help = _("When the monitoring of forwarded logfiles is enabled, the check verifies that "
                                     "all of the logfiles listed here are reported by the monitored system."),
                        )
                    ),
                    ('logwatch_reclassify',
                        Checkbox(
                            title =  _("Reclassify messages before forwarding them to the EC"),
                            label = _("Apply logwatch patterns"),
                            help = _("If this option is enabled, the logwatch lines are first reclassified by the logwatch "
                                     "patterns before they are sent to the event console. If you reclassify specific lines to "
                                     "IGNORE they are not forwarded to the event console. This takes the burden from the "
                                     "event console to process the message itself through all of its rulesets. The reclassifcation "
                                     "of each line takes into account from which logfile the message originates. So you can create "
                                     "logwatch reclassification rules specifically designed for a logfile <i>access.log</i>, "
                                     "which do not apply to other logfiles."),
                     )
                    ),
                    ('separate_checks',
                        Checkbox(
                            title =  _("Create a separate check for each logfile"),
                            label = _("Separate check"),
                            help = _("If this option is enabled, there will be one separate check for each logfile found during "
                                     "the service discovery. This option also changes the behaviour for unknown logfiles. "
                                     "The default logwatch check forwards all logfiles to the event console, even logfiles "
                                     "which were not known during the service discovery. Creating one check per logfile changes "
                                     "this behaviour so that any data from unknown logfiles is discarded."),
                     )
                    )
                ],
                optional_keys = ['restrict_logfiles', 'expected_logfiles', 'logwatch_reclassify', 'separate_checks'],
            ),
        ],
        default_value = '',
    ),
    None,
    'first',
                         )

register_rule(
    RulespecGroupCheckParametersApplications,
    varname="logwatch_groups",
    title=_('Logfile Grouping Patterns'),
    help=_('The check <tt>logwatch</tt> normally creates one service for each logfile. '
           'By defining grouping patterns you can switch to the check <tt>logwatch.groups</tt>. '
           'If the pattern begins with a tilde then this pattern is interpreted as a regular '
           'expression instead of as a filename globbing pattern and  <tt>*</tt> and <tt>?</tt> '
           'are treated differently. '
           'That check monitors a list of logfiles at once. This is useful if you have '
           'e.g. a folder with rotated logfiles where the name of the current logfile'
           'also changes with each rotation'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one logfile grouping pattern"),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                Tuple(
                    show_titles=True,
                    orientation="vertical",
                    elements=[
                        TextAscii(title=_("Include Pattern")),
                        TextAscii(title=_("Exclude Pattern"))
                    ],
                ),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersNetworking,
    "if_disable_if64_hosts",
    title=_("Hosts forced to use <tt>if</tt> instead of <tt>if64</tt>"),
    help=_("A couple of switches with broken firmware report that they "
           "support 64 bit counters but do not output any actual data "
           "in those counters. Listing those hosts in this rule forces "
           "them to use the interface check with 32 bit counters instead."))

# wmic_process does not support inventory at the moment
register_check_parameters(
    RulespecGroupCheckParametersApplications, "wmic_process",
    _("Memory and CPU of processes on Windows"),
    Tuple(
        elements=[
            TextAscii(
                title=_("Name of the process"),
                allow_empty=False,
            ),
            Integer(title=_("Memory warning at"), unit="MB"),
            Integer(title=_("Memory critical at"), unit="MB"),
            Integer(title=_("Pagefile warning at"), unit="MB"),
            Integer(title=_("Pagefile critical at"), unit="MB"),
            Percentage(title=_("CPU usage warning at")),
            Percentage(title=_("CPU usage critical at")),
        ],),
    TextAscii(
        title=_("Process name for usage in the Nagios service description"), allow_empty=False),
    "first", False)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem,
    "zypper",
    _("Zypper Updates"),
    None,
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersOperatingSystem,
    "apt",
    _("APT Updates"),
    Dictionary(elements=[
        ("normal",
         MonitoringState(
             title=_("State when normal updates are pending"),
             default_value=1,
         )),
        ("security",
         MonitoringState(
             title=_("State when security updates are pending"),
             default_value=2,
         )),
    ]),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "airflow_deviation", _("Airflow Deviation in Percent"),
    Tuple(
        help=_("Levels for Airflow Deviation measured at airflow sensors "),
        elements=[
            Float(title=_("critical if below or equal"), unit=u"%", default_value=-20),
            Float(title=_("warning if below or equal"), unit=u"%", default_value=-20),
            Float(title=_("warning if above or equal"), unit=u"%", default_value=20),
            Float(title=_("critical if above or equal"), unit=u"%", default_value=20),
        ]), TextAscii(title=_("Detector ID"), help=_("The identifier of the detector.")), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "citrix_load",
    _("Load of Citrix Server"),
    Transform(
        Tuple(
            title=_("Citrix Server load"),
            elements=[
                Percentage(title=_("Warning at"), default_value=85.0, unit="percent"),
                Percentage(title=_("Critical at"), default_value=95.0, unit="percent"),
            ]),
        forth=lambda x: (x[0] / 100.0, x[1] / 100.0),
        back=lambda x: (int(x[0] * 100), int(x[1] * 100))),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking, "adva_ifs", _("Adva Optical Transport Laser Power"),
    Dictionary(elements=[
        ("limits_output_power",
         Tuple(
             title=_("Sending Power"),
             elements=[
                 Float(title=_("lower limit"), unit="dBm"),
                 Float(title=_("upper limit"), unit="dBm"),
             ])),
        ("limits_input_power",
         Tuple(
             title=_("Received Power"),
             elements=[
                 Float(title=_("lower limit"), unit="dBm"),
                 Float(title=_("upper limit"), unit="dBm"),
             ])),
    ]), TextAscii(
        title=_("Interface"),
        allow_empty=False,
    ), "dict")

bluecat_operstates = [
    (1, "running normally"),
    (2, "not running"),
    (3, "currently starting"),
    (4, "currently stopping"),
    (5, "fault"),
]

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "bluecat_ntp",
    _("Bluecat NTP Settings"),
    Dictionary(elements=[
        ("oper_states",
         Dictionary(
             title=_("Operations States"),
             elements=[
                 ("warning",
                  ListChoice(
                      title=_("States treated as warning"),
                      choices=bluecat_operstates,
                      default_value=[2, 3, 4],
                  )),
                 ("critical",
                  ListChoice(
                      title=_("States treated as critical"),
                      choices=bluecat_operstates,
                      default_value=[5],
                  )),
             ],
             required_keys=['warning', 'critical'],
         )),
        ("stratum",
         Tuple(
             title=_("Levels for Stratum "),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "bluecat_dhcp",
    _("Bluecat DHCP Settings"),
    Dictionary(
        elements=[
            ("oper_states",
             Dictionary(
                 title=_("Operations States"),
                 elements=[
                     ("warning",
                      ListChoice(
                          title=_("States treated as warning"),
                          choices=bluecat_operstates,
                          default_value=[2, 3, 4],
                      )),
                     ("critical",
                      ListChoice(
                          title=_("States treated as critical"),
                          choices=bluecat_operstates,
                          default_value=[5],
                      )),
                 ],
                 required_keys=['warning', 'critical'],
             )),
        ],
        required_keys=['oper_states'],  # There is only one value, so its required
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "bluecat_command_server",
    _("Bluecat Command Server Settings"),
    Dictionary(
        elements=[
            ("oper_states",
             Dictionary(
                 title=_("Operations States"),
                 elements=[
                     ("warning",
                      ListChoice(
                          title=_("States treated as warning"),
                          choices=bluecat_operstates,
                          default_value=[2, 3, 4],
                      )),
                     ("critical",
                      ListChoice(
                          title=_("States treated as critical"),
                          choices=bluecat_operstates,
                          default_value=[5],
                      )),
                 ],
                 required_keys=['warning', 'critical'],
             )),
        ],
        required_keys=['oper_states'],  # There is only one value, so its required
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "bluecat_dns",
    _("Bluecat DNS Settings"),
    Dictionary(
        elements=[
            ("oper_states",
             Dictionary(
                 title=_("Operations States"),
                 elements=[
                     ("warning",
                      ListChoice(
                          title=_("States treated as warning"),
                          choices=bluecat_operstates,
                          default_value=[2, 3, 4],
                      )),
                     ("critical",
                      ListChoice(
                          title=_("States treated as critical"),
                          choices=bluecat_operstates,
                          default_value=[5],
                      )),
                 ],
                 required_keys=['warning', 'critical'],
             )),
        ],
        required_keys=['oper_states'],  # There is only one value, so its required
    ),
    None,
    match_type="dict",
)

bluecat_ha_operstates = [
    (1, "standalone"),
    (2, "active"),
    (3, "passiv"),
    (4, "stopped"),
    (5, "stopping"),
    (6, "becoming active"),
    (7, "becomming passive"),
    (8, "fault"),
]

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "bluecat_ha",
    _("Bluecat HA Settings"),
    Dictionary(
        elements=[
            ("oper_states",
             Dictionary(
                 title=_("Operations States"),
                 elements=[
                     (
                         "warning",
                         ListChoice(
                             title=_("States treated as warning"),
                             choices=bluecat_ha_operstates,
                             default_value=[5, 6, 7],
                         ),
                     ),
                     (
                         "critical",
                         ListChoice(
                             title=_("States treated as critical"),
                             choices=bluecat_ha_operstates,
                             default_value=[8, 4],
                         ),
                     ),
                 ],
                 required_keys=['warning', 'critical'],
             )),
        ],
        required_keys=['oper_states'],  # There is only one value, so its required
    ),
    None,
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "steelhead_connections",
    _("Steelhead connections"),
    Dictionary(
        elements=[
            ("total",
             Tuple(
                 title=_("Levels for total amount of connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("optimized",
             Tuple(
                 title=_("Levels for optimized connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("passthrough",
             Tuple(
                 title=_("Levels for passthrough connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("halfOpened",
             Tuple(
                 title=_("Levels for half opened connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("halfClosed",
             Tuple(
                 title=_("Levels for half closed connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("established",
             Tuple(
                 title=_("Levels for established connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("active",
             Tuple(
                 title=_("Levels for active connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
        ],),
    None,
    "dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "fc_port",
    _("FibreChannel Ports (FCMGMT MIB)"),
    Dictionary(elements=[
        ("bw",
         Alternative(
             title=_("Throughput levels"),
             help=_("Please note: in a few cases the automatic detection of the link speed "
                    "does not work. In these cases you have to set the link speed manually "
                    "below if you want to monitor percentage values"),
             elements=[
                 Tuple(
                     title=_("Used bandwidth of port relative to the link speed"),
                     elements=[
                         Percentage(title=_("Warning at"), unit=_("percent")),
                         Percentage(title=_("Critical at"), unit=_("percent")),
                     ]),
                 Tuple(
                     title=_("Used Bandwidth of port in megabyte/s"),
                     elements=[
                         Integer(title=_("Warning at"), unit=_("MByte/s")),
                         Integer(title=_("Critical at"), unit=_("MByte/s")),
                     ])
             ])),
        ("assumed_speed",
         Float(
             title=_("Assumed link speed"),
             help=_("If the automatic detection of the link speed does "
                    "not work you can set the link speed here."),
             unit=_("Gbit/s"))),
        ("rxcrcs",
         Tuple(
             title=_("CRC errors rate"),
             elements=[
                 Percentage(title=_("Warning at"), unit=_("percent")),
                 Percentage(title=_("Critical at"), unit=_("percent")),
             ])),
        ("rxencoutframes",
         Tuple(
             title=_("Enc-Out frames rate"),
             elements=[
                 Percentage(title=_("Warning at"), unit=_("percent")),
                 Percentage(title=_("Critical at"), unit=_("percent")),
             ])),
        ("notxcredits",
         Tuple(
             title=_("No-TxCredits errors"),
             elements=[
                 Percentage(title=_("Warning at"), unit=_("percent")),
                 Percentage(title=_("Critical at"), unit=_("percent")),
             ])),
        ("c3discards",
         Tuple(
             title=_("C3 discards"),
             elements=[
                 Percentage(title=_("Warning at"), unit=_("percent")),
                 Percentage(title=_("Critical at"), unit=_("percent")),
             ])),
        ("average",
         Integer(
             title=_("Averaging"),
             help=_("If this parameter is set, all throughputs will be averaged "
                    "over the specified time interval before levels are being applied. Per "
                    "default, averaging is turned off. "),
             unit=_("minutes"),
             minvalue=1,
             default_value=5,
         )),
        #            ("phystate",
        #                Optional(
        #                    ListChoice(
        #                        title = _("Allowed states (otherwise check will be critical)"),
        #                        choices = [ (1, _("unknown") ),
        #                                    (2, _("failed") ),
        #                                    (3, _("bypassed") ),
        #                                    (4, _("active") ),
        #                                    (5, _("loopback") ),
        #                                    (6, _("txfault") ),
        #                                    (7, _("nomedia") ),
        #                                    (8, _("linkdown") ),
        #                                  ]
        #                    ),
        #                    title = _("Physical state of port") ,
        #                    negate = True,
        #                    label = _("ignore physical state"),
        #                )
        #            ),
        #            ("opstate",
        #                Optional(
        #                    ListChoice(
        #                        title = _("Allowed states (otherwise check will be critical)"),
        #                        choices = [ (1, _("unknown") ),
        #                                    (2, _("unused") ),
        #                                    (3, _("ready") ),
        #                                    (4, _("warning") ),
        #                                    (5, _("failure") ),
        #                                    (6, _("not participating") ),
        #                                    (7, _("initializing") ),
        #                                    (8, _("bypass") ),
        #                                    (9, _("ols") ),
        #                                  ]
        #                    ),
        #                    title = _("Operational state") ,
        #                    negate = True,
        #                    label = _("ignore operational state"),
        #                )
        #            ),
        #            ("admstate",
        #                Optional(
        #                    ListChoice(
        #                        title = _("Allowed states (otherwise check will be critical)"),
        #                        choices = [ (1, _("unknown") ),
        #                                    (2, _("online") ),
        #                                    (3, _("offline") ),
        #                                    (4, _("bypassed") ),
        #                                    (5, _("diagnostics") ),
        #                                  ]
        #                    ),
        #                    title = _("Administrative state") ,
        #                    negate = True,
        #                    label = _("ignore administrative state"),
        #                )
        #            )
    ]),
    TextAscii(
        title=_("port name"),
        help=_("The name of the FC port"),
    ),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "plug_count", _("Number of active Plugs"),
    Tuple(
        help=_("Levels for the number of active plugs in a device."),
        elements=[
            Integer(title=_("critical if below or equal"), default_value=30),
            Integer(title=_("warning if below or equal"), default_value=32),
            Integer(title=_("warning if above or equal"), default_value=38),
            Integer(title=_("critical if above or equal"), default_value=40),
        ]), None, "first")

# Rules for configuring parameters of checks (services)
register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "ucs_bladecenter_chassis_voltage",
    _("UCS Bladecenter Chassis Voltage Levels"),
    Dictionary(
        help=_("Here you can configure the 3.3V and 12V voltage levels for each chassis."),
        elements=[
            ("levels_3v_lower",
             Tuple(
                 title=_("3.3 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                     Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                 ])),
            ("levels_3v_upper",
             Tuple(
                 title=_("3.3 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                     Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                 ])),
            ("levels_12v_lower",
             Tuple(
                 title=_("12 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=11.9),
                     Float(title=_("critical if below or equal"), unit="V", default_value=11.8),
                 ])),
            ("levels_12v_upper",
             Tuple(
                 title=_("12 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=12.1),
                     Float(title=_("critical if above or equal"), unit="V", default_value=12.2),
                 ]))
        ]), TextAscii(title=_("Chassis"), help=_("The identifier of the chassis.")), "dict")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "hp_msa_psu_voltage",
    _("HP MSA Power Supply Voltage Levels"),
    Dictionary(
        help=_("Here you can configure the 3.3V and 12V voltage levels for each power supply."),
        elements=[
            ("levels_33v_lower",
             Tuple(
                 title=_("3.3 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                     Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                 ])),
            ("levels_33v_upper",
             Tuple(
                 title=_("3.3 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                     Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                 ])),
            ("levels_5v_lower",
             Tuple(
                 title=_("5 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                     Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                 ])),
            ("levels_5v_upper",
             Tuple(
                 title=_("5 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                     Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                 ])),
            ("levels_12v_lower",
             Tuple(
                 title=_("12 Volt Output Lower Levels"),
                 elements=[
                     Float(title=_("warning if below or equal"), unit="V", default_value=11.9),
                     Float(title=_("critical if below or equal"), unit="V", default_value=11.8),
                 ])),
            ("levels_12v_upper",
             Tuple(
                 title=_("12 Volt Output Upper Levels"),
                 elements=[
                     Float(title=_("warning if above or equal"), unit="V", default_value=12.1),
                     Float(title=_("critical if above or equal"), unit="V", default_value=12.2),
                 ]))
        ]), TextAscii(title=_("Power Supply name"), help=_("The identifier of the power supply.")),
    "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "jvm_gc", _("JVM garbage collection levels"),
    Dictionary(
        help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements=[
            ("CollectionTime",
             Alternative(
                 title=_("Collection time levels"),
                 elements=[
                     Tuple(
                         title=_("Time of garbage collection in ms per minute"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("ms"), allow_empty=False),
                             Integer(title=_("Critical at"), unit=_("ms"), allow_empty=False),
                         ])
                 ])),
            ("CollectionCount",
             Alternative(
                 title=_("Collection count levels"),
                 elements=[
                     Tuple(
                         title=_("Count of garbage collection per minute"),
                         elements=[
                             Integer(title=_("Warning at"), allow_empty=False),
                             Integer(title=_("Critical at"), allow_empty=False),
                         ])
                 ])),
        ]),
    TextAscii(
        title=_("Name of the virtual machine and/or<br>garbage collection type"),
        help=_("The name of the application server"),
        allow_empty=False,
    ), "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "jvm_tp", _("JVM tomcat threadpool levels"),
    Dictionary(
        help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements=[
            ("currentThreadCount",
             Alternative(
                 title=_("Current thread count levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage levels of current thread count in threadpool"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_(u"%"), allow_empty=False),
                             Integer(title=_("Critical at"), unit=_(u"%"), allow_empty=False),
                         ])
                 ])),
            ("currentThreadsBusy",
             Alternative(
                 title=_("Current threads busy levels"),
                 elements=[
                     Tuple(
                         title=_("Percentage of current threads busy in threadpool"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_(u"%"), allow_empty=False),
                             Integer(title=_("Critical at"), unit=_(u"%"), allow_empty=False),
                         ])
                 ])),
        ]),
    TextAscii(
        title=_("Name of the virtual machine and/or<br>threadpool"),
        help=_("The name of the application server"),
        allow_empty=False,
    ), "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "docker_node_containers",
    _("Docker node container levels"),
    Dictionary(
        help=_(
            "Allows to define absolute levels for all, running, paused, and stopped containers."),
        elements=[
            ("upper_levels",
             Tuple(
                 title=_("Containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("lower_levels",
             Tuple(
                 title=_("Containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("running_upper_levels",
             Tuple(
                 title=_("Running containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("running_lower_levels",
             Tuple(
                 title=_("Running containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("paused_upper_levels",
             Tuple(
                 title=_("Paused containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("paused_lower_levels",
             Tuple(
                 title=_("Paused containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("stopped_upper_levels",
             Tuple(
                 title=_("Stopped containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("stopped_lower_levels",
             Tuple(
                 title=_("Stopped containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
        ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "docker_node_disk_usage", _("Docker node disk usage"),
    Dictionary(
        help=
        _("Allows to define levels for the counts and size of Docker Containers, Images, Local Volumes, and the Build Cache."
         ),
        elements=[
            ("size",
             Tuple(
                 title=_("Size"),
                 elements=[
                     Filesize(title=_("Warning at"), allow_empty=False),
                     Filesize(title=_("Critical at"), allow_empty=False),
                 ])),
            ("reclaimable",
             Tuple(
                 title=_("Reclaimable"),
                 elements=[
                     Filesize(title=_("Warning at"), allow_empty=False),
                     Filesize(title=_("Critical at"), allow_empty=False),
                 ])),
            ("count",
             Tuple(
                 title=_("Total count"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
            ("active",
             Tuple(
                 title=_("Active"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ])),
        ]),
    TextAscii(
        title=_("Type"),
        help=_("Either Containers, Images, Local Volumes or Build Cache"),
        allow_empty=True,
    ), "dict")

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "heartbeat_crm",
    _("Heartbeat CRM general status"),
    Tuple(elements=[
        Integer(
            title=_("Maximum age"),
            help=_("Maximum accepted age of the reported data in seconds"),
            unit=_("seconds"),
            default_value=60,
        ),
        Optional(
            TextAscii(allow_empty=False),
            title=_("Expected DC"),
            help=_("The hostname of the expected distinguished controller of the cluster"),
        ),
        Optional(
            Integer(min_value=2, default_value=2),
            title=_("Number of Nodes"),
            help=_("The expected number of nodes in the cluster"),
        ),
        Optional(
            Integer(min_value=0,),
            title=_("Number of Resources"),
            help=_("The expected number of resources in the cluster"),
        ),
    ]),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "heartbeat_crm_resources",
    _("Heartbeat CRM resource status"),
    Optional(
        TextAscii(allow_empty=False),
        title=_("Expected node"),
        help=_("The hostname of the expected node to hold this resource."),
        none_label=_("Do not enforce the resource to be hold by a specific node."),
    ),
    TextAscii(
        title=_("Resource Name"),
        help=_("The name of the cluster resource as shown in the service description."),
        allow_empty=False,
    ), "first")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "domino_tasks",
    _("Lotus Domino Tasks"),
    Dictionary(
        elements=[
            (
                "process",
                Alternative(
                    title=_("Name of the task"),
                    style="dropdown",
                    elements=[
                        TextAscii(
                            title=_("Exact name of the task"),
                            size=50,
                        ),
                        Transform(
                            RegExp(
                                size=50,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching tasks"),
                            help=_("This regex must match the <i>beginning</i> of the complete "
                                   "command line of the task including arguments"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all tasks"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0))),
            ("warnmin",
             Integer(
                 title=_("Minimum number of matched tasks for WARNING state"),
                 default_value=1,
             )),
            ("okmin",
             Integer(
                 title=_("Minimum number of matched tasks for OK state"),
                 default_value=1,
             )),
            ("okmax",
             Integer(
                 title=_("Maximum number of matched tasks for OK state"),
                 default_value=99999,
             )),
            ("warnmax",
             Integer(
                 title=_("Maximum number of matched tasks for WARNING state"),
                 default_value=99999,
             )),
        ],
        required_keys=['warnmin', 'okmin', 'okmax', 'warnmax', 'process'],
    ),
    TextAscii(
        title=_("Name of service"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _.-]*$",
        regex_error=_("Please use only a-z, A-Z, 0-9, space, underscore, "
                      "dot and hyphen for your service description"),
    ),
    match_type="dict",
    has_inventory=False)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "domino_mailqueues",
    _("Lotus Domino Mail Queues"),
    Dictionary(
        elements=[
            ("queue_length",
             Tuple(
                 title=_("Number of Mails in Queue"),
                 elements=[
                     Integer(title=_("warning at"), default_value=300),
                     Integer(title=_("critical at"), default_value=350),
                 ])),
        ],
        required_keys=['queue_length'],
    ),
    DropdownChoice(
        choices=[
            ('lnDeadMail', _('Mails in Dead Queue')),
            ('lnWaitingMail', _('Mails in Waiting Queue')),
            ('lnMailHold', _('Mails in Hold Queue')),
            ('lnMailTotalPending', _('Total Pending Mails')),
            ('InMailWaitingforDNS', _('Mails Waiting for DNS Queue')),
        ],
        title=_("Domino Mail Queue Names"),
    ),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "domino_users",
    _("Lotus Domino Users"),
    Tuple(
        title=_("Number of Lotus Domino Users"),
        elements=[
            Integer(title=_("warning at"), default_value=1000),
            Integer(title=_("critical at"), default_value=1500),
        ]),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "domino_transactions",
    _("Lotus Domino Transactions"),
    Tuple(
        title=_("Number of Transactions per Minute on a Lotus Domino Server"),
        elements=[
            Integer(title=_("warning at"), default_value=30000),
            Integer(title=_("critical at"), default_value=35000),
        ]),
    None,
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "netscaler_dnsrates",
    _("Citrix Netscaler DNS counter rates"),
    Dictionary(
        help=_("Counter rates of DNS parameters for Citrix Netscaler Loadbalancer "
               "Appliances"),
        elements=[
            (
                "query",
                Tuple(
                    title=_("Upper Levels for Total Number of DNS queries"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1500.0, unit="/sec"),
                        Float(title=_("Critical at"), default_value=2000.0, unit="/sec")
                    ],
                ),
            ),
            (
                "answer",
                Tuple(
                    title=_("Upper Levels for Total Number of DNS replies"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1500.0, unit="/sec"),
                        Float(title=_("Critical at"), default_value=2000.0, unit="/sec")
                    ],
                ),
            ),
        ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications, "netscaler_tcp_conns",
    _("Citrix Netscaler Loadbalancer TCP Connections"),
    Dictionary(elements=[
        (
            "client_conns",
            Tuple(
                title=_("Max. number of client connections"),
                elements=[
                    Integer(
                        title=_("Warning at"),
                        default_value=25000,
                    ),
                    Integer(
                        title=_("Critical at"),
                        default_value=30000,
                    ),
                ]),
        ),
        (
            "server_conns",
            Tuple(
                title=_("Max. number of server connections"),
                elements=[
                    Integer(
                        title=_("Warning at"),
                        default_value=25000,
                    ),
                    Integer(
                        title=_("Critical at"),
                        default_value=30000,
                    ),
                ]),
        ),
    ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "netscaler_sslcerts",
    _("Citrix Netscaler SSL certificates"),
    Dictionary(
        elements=[
            (
                'age_levels',
                Tuple(
                    title=_("Remaining days of validity"),
                    elements=[
                        Integer(title=_("Warning below"), default_value=30, min_value=0),
                        Integer(title=_("Critical below"), default_value=10, min_value=0),
                    ],
                ),
            ),
        ],),
    TextAscii(title=_("Name of Certificate"),),
    match_type="dict")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "siemens_plc_flag",
    _("State of Siemens PLC Flags"),
    DropdownChoice(
        help=_("This rule sets the expected state, the one which should result in an OK state, "
               "of the monitored flags of Siemens PLC devices."),
        title=_("Expected flag state"),
        choices=[
            (True, _("Expect the flag to be: On")),
            (False, _("Expect the flag to be: Off")),
        ],
        default_value=True),
    TextAscii(
        title=_("Device Name and Value Ident"),
        help=_("You need to concatenate the device name which is configured in the special agent "
               "for the PLC device separated by a space with the ident of the value which is also "
               "configured in the special agent."),
        allow_empty=True),
    match_type="first",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "siemens_plc_duration",
    _("Siemens PLC Duration"),
    Dictionary(
        elements=[
            ('duration',
             Tuple(
                 title=_("Duration"),
                 elements=[
                     Age(title=_("Warning at"),),
                     Age(title=_("Critical at"),),
                 ])),
        ],
        help=_("This rule is used to configure thresholds for duration values read from "
               "Siemens PLC devices."),
        title=_("Duration levels"),
    ),
    TextAscii(
        title=_("Device Name and Value Ident"),
        help=_("You need to concatenate the device name which is configured in the special agent "
               "for the PLC device separated by a space with the ident of the value which is also "
               "configured in the special agent."),
    ),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersEnvironment,
    "siemens_plc_counter",
    _("Siemens PLC Counter"),
    Dictionary(
        elements=[
            ('levels',
             Tuple(
                 title=_("Counter level"),
                 elements=[
                     Integer(title=_("Warning at"),),
                     Integer(title=_("Critical at"),),
                 ])),
        ],
        help=_("This rule is used to configure thresholds for counter values read from "
               "Siemens PLC devices."),
        title=_("Counter levels"),
    ),
    TextAscii(
        title=_("Device Name and Value Ident"),
        help=_("You need to concatenate the device name which is configured in the special agent "
               "for the PLC device separated by a space with the ident of the value which is also "
               "configured in the special agent."),
    ),
    match_type="dict",
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "bossock_fibers", _("Number of Running Bossock Fibers"),
    Tuple(
        title=_("Number of fibers"),
        elements=[
            Integer(title=_("Warning at"), unit=_("fibers")),
            Integer(title=_("Critical at"), unit=_("fibers")),
        ]), TextAscii(title=_("Node ID")), "first")

register_check_parameters(
    RulespecGroupCheckParametersEnvironment, "carbon_monoxide", ("Carbon monoxide"),
    Dictionary(elements=[
        ("levels_ppm",
         Tuple(
             title="Levels in parts per million",
             elements=[
                 Integer(title=_("Warning at"), unit=_("ppm"), default=10),
                 Integer(title=_("Critical at"), unit=_("ppm"), default=25),
             ])),
    ]), None, "dict")
