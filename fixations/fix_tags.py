#!/usr/bin/env python3

import re
import sys

import urwid
from tabulate import tabulate
from termcolor import colored

from fixations.fix_utils import extract_tag_dict_for_fix_version

DEFAULT_VERSION = "4.2"


def get_data_grid_for_search(search=None):
    rows = []
    for id in sorted(tag_dict_by_id, key=lambda k: int(k)):
        fix_tag = tag_dict_by_id[id]
        desc = fix_tag.desc
        if len(desc) > 80:
            desc = desc[:79] + '…'
        value_rows = "\n".join([f"{v.value}: {v.name}" for v in fix_tag.values.values()])
        if search:
            include = search.lower() in (id + fix_tag.name + fix_tag.desc + value_rows).lower()
        else:
            include = True
        if include:
            row = [id, fix_tag.name, fix_tag.type, desc, value_rows]
            rows.append(row)

    return tabulate(rows, headers=["ID", "NAME", "TYPE", "DESCRIPTION", "VALUES"], tablefmt='grid')


def create_highlighted_text(text, text_to_highlight, highlight_attr):
    tth_lc = text_to_highlight.lower()
    tth_len = len(text_to_highlight)
    if tth_len > 0:
        chunks = []
        stop = False
        while not stop:
            tth_pos = text.lower().find(tth_lc)
            if tth_pos == -1:
                stop = True
                chunks.append(text)
            else:
                chunks.append(text[:tth_pos])
                chunks.append((highlight_attr, text[tth_pos:tth_pos + tth_len]))
                text = text[tth_pos + tth_len:]
    else:
        chunks = [text]

    # for chunk in chunks:
    #     print(chunk)
    # exit(1)
    return chunks


def on_search_change(edit, search_string):
    text = get_data_grid_for_search(search_string)
    text_chunks = create_highlighted_text(text, search_string, 'highlight')
    search_results.set_text(text_chunks)


def color_search_string(text, search_string, color):
    insensitive_search = re.compile(re.escape(search_string), re.IGNORECASE)
    colored_replacement = colored(search_string, color, attrs=['bold'])
    return insensitive_search.sub(colored_replacement, text)


if __name__ == '__main__':
    tag_dict_by_id = extract_tag_dict_for_fix_version(DEFAULT_VERSION)
    if len(sys.argv) > 1:
        search = sys.argv[1]
        search_results = get_data_grid_for_search(search)
        print(color_search_string(search_results, search, 'red'))
    else:
        palette = [(None, 'white', 'default'),
                   ('input', 'light green', 'default'),
                   ('highlight', 'light green', 'default')]
        search = urwid.Edit((input, u"Search string: "))
        # results = urwid.AttrMap(urwid.Text(get_data_grid_for_search()), None, "focus")
        # lw = urwid.SimpleListWalker([])
        search_results = urwid.Text(get_data_grid_for_search())
        pile = urwid.Pile([search, search_results])
        top = urwid.Filler(pile, valign='top')

        urwid.connect_signal(search, 'change', on_search_change)
        urwid.MainLoop(top, palette).run()
