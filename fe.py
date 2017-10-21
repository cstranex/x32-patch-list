"""
    Flask-based application that will generate patch lists for X32 show files.

    User uploads their show file to /generate which will create an HTML file based on
    their options.

    The template has a checkbox for each section/line to show that row. There is also a
    remarks and source column that user can enter text in.
"""

from flask import Flask, request, render_template
from main import ScnParser

app = Flask(__name__)
app.debug = True

parser = ScnParser()

TYPE_NAMES = {
    'in': 'Local',
    'aux': 'Aux',
    'aes': 'AES',

    'aes50a': 'AES50-A',
    'aes50b': 'AES50-B',
    'card': 'Card',

    'p16': 'Ultranet',
    'out': 'Local',
}

MIX_NAMES = {
    'bus': 'Bus',
    'main': 'Main',
    'fxrtn': 'FX'
}

CHANNEL_NAMES = {
    'auxin': 'Aux',

}


def GetMixName(type, n):
    """ Prefix a channel with its mix name """
    name = MIX_NAMES[type]
    if type == 'main':
        return '{} {}'.format(name, n.upper())

    if n.isdigit():
        n = "{:02}".format(int(n))

    return '{} {}'.format(name, n)


def GetChannelName(type, n):
    """ Prefix a channel with its channel type """
    if type in CHANNEL_NAMES:
        return ('{} {}'.format(CHANNEL_NAMES[type], n))
    else:
        return n


def GetDeskName(chan):
    """ Return either an input or output channel name """
    if not chan:
        return ''

    if 'mix' in chan:
        return GetMixName(chan['mix'], chan['mix_index'])
    elif 'channel' in chan:
        return GetChannelName(chan['channel'], chan['channel_index'])

    return ''


def GetTypeName(type, n):
    """ Return correct name from type """
    if type == 'in' and n > 32:
        return 'Aux In'
    else:
        return TYPE_NAMES[type]


def GetSourceIndex(type, n):
    """ Return correct source names """
    if type == 'in':
        if n < 33:
            return n
        elif n < 39:
            return 'Aux {:01}'.format(n - 32)
        elif n < 40:
            return 'USB L'
        elif n < 41:
            return 'USB R'
    else:
        return n


@app.route('/generate', methods=['POST'])
def generate():
    """
        Generation method, accepts an uploaded scn file along with some user-specified options.

        Current options allowed (all are either 1 for true or 0 for false):
        color           -   Add a separate column to show colour
        title           -   Title
    """

    opts = {
        'color': True if request.files.get('color', '1') == '1' else False,
        'title': request.files.get('title', '')
    }

    parser.ParseFile(request.files['scene'])

    kwargs = {
        'parser': parser,
        'options': opts,
        'TYPE_NAMES': TYPE_NAMES,
        'GetTypeName': GetTypeName,
        'GetSourceIndex': GetSourceIndex,
        'GetDeskName': GetDeskName
    }

    return render_template('template.html', **kwargs)
