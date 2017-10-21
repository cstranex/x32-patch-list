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
    'aes50a': 'AES50-A',
    'aes50b': 'AES50-B',
    'card': 'Card',

    'p16': 'Ultranet',
    'out': 'Local',
}


def GetTypeName(type, n):
    if type == 'in' and n > 32:
        return 'Aux In'
    else:
        return TYPE_NAMES[type]


@app.route('/generate', methods=['POST'])
def generate():
    """
        Generation method, accepts an uploaded scn file along with some user-specified options.

        Current options allowed (all are either 1 for true or 0 for false):
        set-bg-color    -   Set the background colour of the table row to channel colour (if applicable)
        set-fg-color    -   Set the foreground colour of the table row to channel colour (if applicable)
        set-color       -   Add a separate column to show colour
        hide-blank      -   Hide rows that have a blank name
        hide-black      -   Hide black coloured rows
        title           -   Title
    """

    opts = {
        'setbgcolor': True if request.files.get('set-bg-color') == '1' else False,
        'setfgcolor': True if request.files.get('set-fg-color') == '1' else False,
        'setcolor': True if request.files.get('set-color') == '1' else False,
        'hide-blank':  True if request.files.get('hide-blank') == '1' else False,
        'hide-black': True if request.files.get('hide-black') == '1' else False,
        'title': request.files.get('title', '')
    }

    parser.ParseFile(request.files['scene'])

    kwargs = {
        'parser': parser,
        'options': opts,
        'TYPE_NAMES': TYPE_NAMES,
        'GetTypeName': GetTypeName
    }

    return render_template('template.html', **kwargs)
