# -*- coding: utf-8 -*-


from prefs import Prefs


__all__ = ['AnthyPrefs']


class AnthyPrefs(Prefs):
    _prefix = 'engine/anthy'

    def __init__(self, bus=None, config=None):
        super(AnthyPrefs, self).__init__(bus, config)
        self.default = _config

        self.fetch_all()

    def keys(self, section):
        if section.startswith('shortcut/'):
            return _cmd_keys
        return self.default[section].keys()


_cmd_keys = [
    "on_off",
    "circle_input_mode",
    "circle_kana_mode",
    "latin_mode",
    "wide_latin_mode",
    "hiragana_mode",
    "katakana_mode",
    "half_katakana_mode",
    "cancel_pseudo_ascii_mode_key",
    "circle_typing_method",

    "insert_space",
    "insert_alternate_space",
    "insert_half_space",
    "insert_wide_space",
    "backspace",
    "delete",
    "commit",
    "convert",
    "predict",
    "cancel",
    "cancel_all",
    "reconvert",
    "do_nothing",

    "select_first_candidate",
    "select_last_candidate",
    "select_next_candidate",
    "select_prev_candidate",
    "candidates_page_up",
    "candidates_page_down",

    "move_caret_first",
    "move_caret_last",
    "move_caret_forward",
    "move_caret_backward",

    "select_first_segment",
    "select_last_segment",
    "select_next_segment",
    "select_prev_segment",
    "shrink_segment",
    "expand_segment",
    "commit_first_segment",
    "commit_selected_segment",

    "select_candidates_1",
    "select_candidates_2",
    "select_candidates_3",
    "select_candidates_4",
    "select_candidates_5",
    "select_candidates_6",
    "select_candidates_7",
    "select_candidates_8",
    "select_candidates_9",
    "select_candidates_0",

    "convert_to_char_type_forward",
    "convert_to_char_type_backward",
    "convert_to_hiragana",
    "convert_to_katakana",
    "convert_to_half",
    "convert_to_half_katakana",
    "convert_to_wide_latin",
    "convert_to_latin",

    "dict_admin",
    "add_word",
]

_config = {
    'common': {
        'input_mode': 0,
        'typing_method': 0,

        'period_style': 0,
        'ten_key_mode': 0,
        'behivior_on_focus_out': 0,
        'behivior_on_period': 0,

        'page_size': 10,
        'half_width_symbol': False,
        'half_width_number': False,

        'shortcut_type': 'default'
    },
    'shortcut/default': {
        #mode_keys
        'on_off': ['Ctrl+J'],
        'circle_input_mode': ['Ctrl+comma', 'Ctrl+less'],
        'circle_kana_mode': ['Ctrl+period', 'Ctrl+greater', 'Hiragana_Katakana'],
        'latin_mode': [],
        'wide_latin_mode': [],
        'hiragana_mode': [],
        'katakana_mode': [],
        'half_katakana_mode': [],
        'cancel_pseudo_ascii_mode_key': ['Escape'],
        'circle_typing_method': ['Alt+Romaji', 'Ctrl+slash'],

        #edit_keys
        'insert_space': ['space'],
        'insert_alternate_space': ['Shift+space'],
        'insert_half_space': [],
        'insert_wide_space': [],
        'backspace': ['BackSpace', 'Ctrl+H'],
        'delete': ['Delete', 'Ctrl+D'],
        'commit': ['Return', 'KP_Enter', 'Ctrl+J', 'Ctrl+M'],
        'convert': ['space', 'KP_Space', 'Henkan'],
        'predict': ['Tab', 'ISO_Left_Tab'],
        'cancel': ['Escape', 'Ctrl+G'],
        'cancel_all': [],
        'reconvert': ['Shift+Henkan'],
        'do_nothing': [],

        #caret_keys
        'move_caret_first': ['Ctrl+A', 'Home'],
        'move_caret_last': ['Ctrl+E', 'End'],
        'move_caret_forward': ['Right', 'Ctrl+F'],
        'move_caret_backward': ['Left', 'Ctrl+B'],

        #segments_keys
        'select_first_segment': ['Ctrl+A', 'Home'],
        'select_last_segment': ['Ctrl+E', 'End'],
        'select_next_segment': ['Right', 'Ctrl+F'],
        'select_prev_segment': ['Left', 'Ctrl+B'],
        'shrink_segment': ['Shift+Left', 'Ctrl+I'],
        'expand_segment': ['Shift+Right', 'Ctrl+O'],
        'commit_first_segment': ['Shift+Down'],
        'commit_selected_segment': ['Ctrl+Down'],

        #candidates_keys
        'select_first_candidate': ['Home'],
        'select_last_candidate': ['End'],
        'select_next_candidate': ['space', 'KP_Space', 'Tab', 'ISO_Left_Tab', 'Henkan', 'Down', 'KP_Add', 'Ctrl+N'],
        'select_prev_candidate': ['Shift+Tab', 'Shift+ISO_Left_Tab', 'Up', 'KP_Subtract', 'Ctrl+P'],
        'candidates_page_up': ['Page_Up'],
        'candidates_page_down': ['Page_Down', 'KP_Tab'],

        #direct_select_keys
        'select_candidates_1': ['1'],
        'select_candidates_2': ['2'],
        'select_candidates_3': ['3'],
        'select_candidates_4': ['4'],
        'select_candidates_5': ['5'],
        'select_candidates_6': ['6'],
        'select_candidates_7': ['7'],
        'select_candidates_8': ['8'],
        'select_candidates_9': ['9'],
        'select_candidates_0': ['0'],

        #convert_keys
        'convert_to_char_type_forward': ['Muhenkan'],
        'convert_to_char_type_backward': [],
        'convert_to_hiragana': ['F6'],
        'convert_to_katakana': ['F7'],
        'convert_to_half': ['F8'],
        'convert_to_half_katakana': ['Shift+F8'],
        'convert_to_wide_latin': ['F9'],
        'convert_to_latin': ['F10'],

        #dictonary_keys
        'dict_admin': ['F11'],
        'add_word': ['F12'],
    },
}

_shortcut_atok = {
    'on_off': ['Henkan', 'Eisu_toggle', 'Zenkaku_Hankaku'],
    'circle_input_mode': ['F10'],
    'hiragana_mode': ['Hiragana_Katakana'],
    'katakana_mode': ['Shift+Hiragana_Katakana'],
    'circle_typing_method': ['Romaji', 'Alt+Romaji'],
    'convert': ['space', 'Henkan', 'Shift+space', 'Shift+Henkan'],
    'predict': ['Tab'],
    'cancel': ['Escape', 'BackSpace', 'Ctrl+H', 'Ctrl+bracketleft'],
    'commit': ['Return', 'Ctrl+M'],
    'reconvert': ['Shift+Henkan'],

    'insert_space': ['space'],
    'insert_alternate_space': ['Shift+space'],
    'backspace': ['BackSpace', 'Ctrl+H'],
    'delete': ['Delete', 'Ctrl+G'],

    'move_caret_backward': ['Left', 'Ctrl+K'],
    'move_caret_forward': ['Right', 'Ctrl+L'],
    'move_caret_first': ['Ctrl+Left'],
    'move_caret_last': ['Ctrl+Right'],

    'select_prev_segment': ['Shift+Left'],
    'select_next_segment': ['Shift+Right'],
    'select_first_segment': ['Ctrl+Left'],
    'select_last_segment': ['Ctrl+Right'],
    'expand_segment': ['Right', 'Ctrl+L'],
    'shrink_segment': ['Left', 'Ctrl+K'],
    'commit_selected_segment': ['Down'],

    'candidates_page_up': ['Shift+Henkan', 'Page_Up'],
    'candidates_page_down': ['Henkan', 'Page_Down'],
    'select_next_candidate': ['space', 'Tab', 'Henkan', 'Shift+space', 'Shift+Henkan'],
    'select_prev_candidate': ['Up'],

    'select_candidates_1': ['1'],
    'select_candidates_2': ['2'],
    'select_candidates_3': ['3'],
    'select_candidates_4': ['4'],
    'select_candidates_5': ['5'],
    'select_candidates_6': ['6'],
    'select_candidates_7': ['7'],
    'select_candidates_8': ['8'],
    'select_candidates_9': ['9'],
    'select_candidates_0': ['0'],

    'convert_to_hiragana': ['F6', 'Ctrl+U'],
    'convert_to_katakana': ['F7', 'Ctrl+I'],
    'convert_to_half': ['F8', 'Ctrl+O'],
    'convert_to_half_katakana': ['Shift+F8'],
    'convert_to_wide_latin': ['F9', 'Ctrl+P'],
    'convert_to_latin': ['F10', 'Ctrl+at'],

    'add_word': ['Ctrl+F7'],
}

_config['shortcut/atok'] = dict.fromkeys(_cmd_keys, [])
_config['shortcut/atok'].update(_shortcut_atok)

_shortcut_wnn = {
    'on_off': ['Shift+space'],
    'convert': ['space'],
    'predict': ['Ctrl+Q'],
    'cancel': ['Escape', 'Ctrl+G', 'Alt+Down', 'Muhenkan'],
    'commit': ['Ctrl+L', 'Ctrl+M', 'Ctrl+J', 'Return'],
    'insert_space': ['space'],
    'backspace': ['Ctrl+H', 'BackSpace'],
    'delete': ['Ctrl+D', 'Delete'],

    'move_caret_backward': ['Ctrl+B', 'Left'],
    'move_caret_forward': ['Ctrl+F', 'Right'],
    'move_caret_first': ['Ctrl+A', 'Alt+Left'],
    'move_caret_last': ['Ctrl+E', 'Alt+Right'],

    'select_prev_segment': ['Ctrl+B', 'Left'],
    'select_next_segment': ['Ctrl+F', 'Right'],
    'select_first_segment': ['Ctrl+A', 'Alt+Left'],
    'select_last_segment': ['Ctrl+E', 'Alt+Right'],
    'expand_segment': ['Ctrl+O', 'F14'],
    'shrink_segment': ['Ctrl+I', 'F13'],

    'candidates_page_up': ['Tab'],
    'candidates_page_down': ['Shift+Tab'],
    'select_next_candidate': ['space', 'Ctrl+Q', 'Ctrl+P', 'Down'],
    'select_prev_candidate': ['Ctrl+N', 'Up'],

    'select_candidates_1': ['1'],
    'select_candidates_2': ['2'],
    'select_candidates_3': ['3'],
    'select_candidates_4': ['4'],
    'select_candidates_5': ['5'],
    'select_candidates_6': ['6'],
    'select_candidates_7': ['7'],
    'select_candidates_8': ['8'],
    'select_candidates_9': ['9'],
    'select_candidates_0': ['0'],

    'convert_to_hiragana': ['F6'],
    'convert_to_katakana': ['F7'],
    'convert_to_half': ['F8'],
    'convert_to_wide_latin': ['F9'],
    'convert_to_latin': ['F10'],
}

_config['shortcut/wnn'] = dict.fromkeys(_cmd_keys, [])
_config['shortcut/wnn'].update(_shortcut_wnn)

