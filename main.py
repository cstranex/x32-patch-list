#!/usr/bin/env python3
"""
    Utility to generate paperwork from X32 scene files.

    It will show a list on inputs, outputs and various routing
    information. It will ignore channels that are black ('off')
    or have not been named.


    (c) Chris Stranex 2017 <cstranex@gmail.com>
    Under the GNU GPL v2 Licence
"""

import argparse
import csv
import re
import logging

from collections import defaultdict

logger = logging.getLogger(__name__)

CONFIG_RE = re.compile(
    r'/(ch|auxin|bus|mtx|main|fxrtn)/([0-3][0-9]|st|m)/config'
)
ROUTING_RE = re.compile(
    r'/config/routing/(IN|AES50A|AES50B|CARD|OUT)'
)

# main = outputs
OUTPUTS_RE = re.compile(
    r'/outputs/(aux|aes|main|p16)/([0-3][0-9])$'
)

OUTPUTS = ['bus', 'mtx', 'main']
INPUTS = ['ch', 'auxin']

MAX_CHANNELS = {
    'aes50a': 48,
    'aes50b': 48,
    'in': 40,
    'card': 32,
}

MAX_OUTPUTS = {
    'aes50a': 48,
    'aes50b': 48,
    'card': 32,
    'out': 16,
    'p16': 16,
    'aux': 6,
    'aes': 2
}

"""
Routing and Source information

IN - Input routing
AES50A/AES50B/CARD - Output routing
OUT - XLR outputs on back of X32

AN1-8 ... - XLR inputs on back of X32
A1-8  ... - AES50A inputs
B-18  ... - AES50B inputs
OUT1-8 .. - Output Route (NOT XLR outputs)
CARD1-8.. - Card channels
P161-8 .. - P-16 Outputs
AUX/CR    - Aux 1-6 Channels + Control Room outs
AUX/TB    - Aux 1-6 INPUTS from back of X32 + Talkback


Source Numbers:
    Inputs:
        0     - Off
        1-32  - Routed Inputs
        33-40 - Aux Inputs (1-6 + USB)
        41-48 - Effects 1-4
        49-64 - Bus 1 - 16

    Outputs:
        0     - Insert (if Aux output otherwise Off)
        1     - Main Left
        2     - Main Right
        3     - Centre
        4-19  - Mix Bus
        20-25 - Matrix
        26-57 - Direct Out Channel
        58-65 - Direct Out Aux
        66-73 - Effects 1-4
        74-75 - Monitor Left, Right, Talkback

"""


def RouteSourceFromRouteGroup(group, offset):
    """ Return a route source from a route group and offset"""

    src, n = re.match(
        '(AN|OUT|CARD|P16|AUX/CR|AUX/TB|AUX|A|B)([0-9][0-9]?)?',
        group
    ).groups()  # Ugly regex to split types and type offsets

    if src == 'AUX/CR':
        if offset < 6:
            return 'aux.{:02}'.format(offset + 1)
        elif offset == 6:
            return 'mon.l'
        elif offset == 7:
            return 'mon.r'
    elif src == 'AUX/TB':
        if offset < 6:
            return 'auxin.{:02}'.format(offset + 1)
        elif offset == 6:
            return 'tb'
    elif src == 'AUX':
        return 'in.{:02}'.format(offset + 33)
    elif src == 'AN':
        return '{}.{:02}'.format(
            'in',
            offset + int(n)
        )
    elif src == 'A':
        return '{}.{:02}'.format(
            'aes50a',
            offset + int(n)
        )
    elif src == 'B':
        return '{}.{:02}'.format(
            'aes50b',
            offset + int(n)
        )
    elif src == 'OUT':
        return '{}.{:02}'.format(
            'out',
            offset + int(n)
        )
    elif src == 'CARD':
        return '{}.{:02}'.format(
            'card',
            offset + int(n)
        )
    elif src == 'P16':
        return '{}.{:02}'.format(
            'p16',
            offset + int(n)
        )

    return None


def NameFromRouteGroup(group, offset):
    """ Return a name from a route group and offset """

    match = re.match(
        '(AUX|AN|A|B|OUT|CARD|P16)([0-9][0-9]?)?',
        group
    )
    if not match:
        return ''

    src, n = match.groups()

    name = ''
    if src == 'AN':
        name = 'Local {:02}'.format(offset + int(n))
    elif src == 'A':
        name = 'AES50-A {:02}'.format(offset + int(n))
    elif src == 'B':
        name = 'AES50-B {:02}'.format(offset + int(n))
    elif src == 'OUT':
        name = 'Output {:02}'.format(offset + int(n))
    elif src == 'CARD':
        name = 'Card {:02}'.format(offset + int(n))
    elif src == 'P16':
        name = 'P-16 {:02}'.format(offset + int(n))
    elif group.startswith('AUX/CR'):
        if offset < 6:
            name = 'Aux Out {:02}'.format(offset + 1)
        elif offset == 6:
            name = 'Control Room Left'
        elif offset == 7:
            name = 'Control Room Right'
    elif group.startswith('AUX/TB'):
        if offset < 6:
            name = 'Aux In {:02}'.format(offset + 1)
        elif offset == 6:
            name = 'Talkback'
    elif group.startswith('AUX1-4'):
        if offset < 6:
            name = 'Aux In {:02}'.format(offset + 1)
        elif offset == 6:
            name = 'USB L'
        elif offset == 7:
            name = 'USB R'

    return name


def GetRouteKeyFromSource(source):
    """ Get an input channel's route from source integer """

    if source == 0:
        return 'off'
    elif source <= 32:
        return 'in.{:02}'.format(source)
    elif source <= 40:
        return 'in.{:02}'.format(source)
    elif source <= 48:
        return 'fx.{:02}'.format(source - 40)
    elif source <= 64:
        return 'bus.{:02}'.format(source - 48)

    logger.warning("Input channel %s not found", source)
    return None


def GetChannelKeyFromSource(source):
    """ Return a channel key for an output's source integer """
    if source == 0:
        return None
    elif source == 1:
        return 'main.l'
    elif source == 2:
        return 'main.r'
    elif source == 3:
        return 'main.m'
    elif source <= 19:
        return 'bus.{:02}'.format(source - 3)
    elif source <= 25:
        return 'mtx.{:02}'.format(source - 19)
    elif source <= 57:
        return 'in.{:02}'.format(source - 25)
    elif source <= 65:
        return 'auxin.{:02}'.format(source - 57)
    elif source <= 73:
        return 'fx.{:02}'.format(source - 65)
    elif source == 74:
        return 'mon.l'
    elif source == 75:
        return 'mon.r'
    elif source == 76:
        return 'tb'


def GetNameForOutput(ch_type, ch_num):
    """ Return a human-readable name from output type and number """

    name = ''
    if ch_type == 'aux':
        name = 'Aux {}'.format(ch_num)
    elif ch_type == 'main':
        name = 'Output {}'.format(ch_num)
    elif ch_type == 'aes':
        if ch_num == 1:
            name = 'AES Left'
        else:
            name = 'AES Right'
    elif ch_type == 'p16':
        name = 'P16 {}'.format(ch_num)

    return name


class ScnParser(object):
    """ X32 File format parser """

    def __init__(self):
        self.route = {}
        self.channels = {}
        self.outputs = {}
        self.channel_by_route = defaultdict(list)
        self.input_route_source = {}
        self.output_route_source = {}

    def ParseFile(self, fobj):
        """ Parse a file-like object """

        self.__init__()

        for line in csv.reader(fobj, delimiter=' '):
            if ROUTING_RE.match(line[0]):
                self.ParseRouting(line)
            elif CONFIG_RE.match(line[0]):
                self.ParseConfig(line)
            elif OUTPUTS_RE.match(line[0]):
                self.ParseOutput(line)

        # Automatically create some presets for Monitor L, R and TB
        self.channels['tb'] = {
            'name': 'Talkback',
            'color': 'INT',
            'internal': 'tb'
        }
        self.channels['mon.l'] = {
            'name': 'Monitor L',
            'color': 'INT',
            'internal': 'mon'
        }
        self.channels['mon.r'] = {
            'name': 'Monitor R',
            'color': 'INT',
            'internal': 'mon'
        }

    def ParseRouting(self, line):
        """ Parse routing information """

        routing_type, = ROUTING_RE.match(line[0]).groups()
        if routing_type == 'OUT':
            group_size = 4
        else:
            # TODO: The Aux in block is a special case
            # The value can only have a few values (eg: A1-4)
            # The last values must then stay as their defaults.
            group_size = 8

        for n, group in enumerate(line[1:]):
            for i in range(group_size):
                name = NameFromRouteGroup(group, i)
                route_path = '{}.{:02}'.format(
                    routing_type.lower(),
                    (n * group_size) + i + 1
                )

                route_source = RouteSourceFromRouteGroup(
                    group, i
                )

                if name:
                    if routing_type == 'IN':
                        src = None

                        self.input_route_source[
                            route_source
                        ] = route_path
                    else:
                        src = route_source

                        self.output_route_source[route_path] = route_source

                    self.route[route_path] = {
                        'name': name,
                        'output_key': src
                    }
                else:
                    self.route[route_path] = {
                        'off': True
                    }

    def ParseOutput(self, line):
        """ Parse output routes """
        config_type, ch_num = OUTPUTS_RE.match(line[0]).groups()

        try:
            _path, source, _tap, _phase = line
        except ValueError:
            logger.error("Splitting output line failed: %s", line)
            raise RuntimeError("ParseOutput failed")

        if config_type == 'main':
            config_type = 'out'

        self.outputs['{}.{}'.format(
            config_type, ch_num)] = GetChannelKeyFromSource(int(source))

    def ParseConfig(self, line):
        """ Parse configuration """

        config_type, ch_num = CONFIG_RE.match(line[0]).groups()

        if config_type in OUTPUTS:
            try:
                _path, name, _, colour = line  # osc path, name, icon, colour
            except ValueError:
                logger.error("Splitting output line failed: %s", line)
                raise RuntimeError("ParseConfig Outputs failed")


            if config_type == 'main' and ch_num == 'st':
                ch_num = 'l'

            self.channels['{}.{}'.format(config_type, ch_num)] = {
                'name': name,
                'color': colour,
                'mix_index': ch_num,
                'mix': config_type
            }

            if config_type == 'main' and ch_num == 'l':
                self.channels['main.r'] = {}
                self.channels['main.r'].update(self.channels['main.l'])
                self.channels['main.r'].update({
                    'mix_index': 'r'
                })

        elif config_type in INPUTS:
            try:
                _path, name, _, colour, source = line  # osc path, name, icon, colour, source
            except ValueError:
                logger.error("Splitting input line failed: %s", line)
                raise RuntimeError("ParseConfig Inputs failed")

            if config_type == 'ch':
                config_type = 'in'

            route_key = GetRouteKeyFromSource(int(source))
            chan_key = '{}.{}'.format(config_type, ch_num)

            self.channels[chan_key] = {
                'name': name,
                'route_key': route_key,
                'channel': config_type,
                'channel_index': int(ch_num),
                'color': colour
            }
            self.channel_by_route[route_key].append(self.channels[chan_key])
        elif config_type == 'fxrtn':
            _path, name, _, colour = line
            self.channels['fx.{}'.format(ch_num)] = {
                'name': name,
                'color': colour,
                'mix_index': ch_num,
                'mix': config_type
            }

    def GetRoute(self, route):
        """ Get a route by key """
        return self.route.get(route)

    def GetOutputListForType(self, output_type):
        """
            Interate through all outputs for type and find output channel source.
        """
        patch = []
        for i in range(MAX_OUTPUTS[output_type]):
            key = '{}.{:02}'.format(output_type, i + 1)

            if output_type in ['p16', 'aux', 'aes']:
                # Source doesn't only have to be an output
                source = self.outputs.get(key)
                if not source:
                    patch.append(None)
                    continue
            elif key in self.output_route_source:
                source = self.output_route_source[key]
            else:
                patch.append(None)
                continue

            if source.startswith('p16'):
                patch.append({
                    'p16': True,
                    # 'channel_index': source.split('.')[1]
                })
                continue

            # Linked to an Output
            if source in self.outputs:
                source = self.outputs.get(source)

            patch.append(self.channels.get(source))

        return patch

    def GetChannelListForType(self, input_type):
        """
            Iterate through all inputs for type and find channel sources.

            eg:
            GetInputPatchForType('aes50a')
            [{'name': 'Test', channel_index: 1}, None, None, ...]
        """

        # Step 1: Get the route list for IN
        patch = []
        for i in range(MAX_CHANNELS[input_type]):
            key = '{}.{:02}'.format(input_type, i + 1)

            if key not in self.input_route_source:
                patch.append(None)
                continue

            route_key = self.input_route_source[key]
            if self.channel_by_route[route_key]:
                patch.append(self.channel_by_route[route_key])
            else:
                patch.append(None)

        return patch

    def GetOutput(self, output):
        """ Get an output by key """
        return self.outputs.get(output, None)

    def GetChannel(self, key):
        """ Get channel by key """
        if key not in self.channels:
            return None

        input_channel = dict(self.channels[key])

        if 'route_key' not in scene_parser.route:
            # Shouldn't really happen but in case
            del input_channel['route_key']

        return input_channel

    def GetInputChannel(self, channel):
        """
            Get channel details for channels 1 - 32 on the desk.
            Index starts from 1.
        """
        key = 'in.in.{:02}'.format(channel)
        return self.GetChannel(key)

    def GetInputAuxChannel(self, channel):
        """
            Get channel details for aux 1 to 8.
            Index starts from 1
        """
        key = 'in.auxin.{:02}'.format(channel)
        return self.GetChannel(key)

    def GetP16Channel(self, channel):
        """
            Get what the P-16 has been routed to
        """
        key = 'p16.{:02}'.format(channel)

        if key not in self.outputs:
            return None

        output = self.outputs[key]
        return output

    def GetAES50OutputChannel(self, bank, channel):
        """
            Get what an AES50 output is routed to
        """
        if bank.lower() not in ['a', 'b']:
            raise ValueError("Bank must either be A or B")
        return self.route.get('aes50{}.{:02}'.format(bank.lower(), channel), None)

    def GetCardOutputChannel(self, channel):
        """
            Get what an expansion card output is routed to
        """
        return self.route.get('card.{:02}'.format(channel), None)

    def GetAuxOutputChannel(self, channel):
        """
            Get what an aux output is routed to
        """
        return self.route.get('aux.{:02}'.format(channel), None)

    def GetXLROutputChannel(self, channel):
        """
            Get what an XLR output is routed to
        """
        return self.route.get('out.{:02}'.format(channel), None)
