import os
import pdb
from datetime import timedelta
from typing import List

import pytest

import fixations
from fixations.fix_utils import extract_fix_lines_from_str_lines, extract_info_for_fix_version, \
    extract_version_from_first_fix_line, extract_timestamp, FIX_TAG_ID_SENDING_TIME, get_cfg_value, \
    CFG_FILE_KEY_FIX_DEFINITIONS_PATH, path_for_fix_version, get_list_of_available_fix_versions, \
    check_for_additional_fix_definitions, Additional_tag_cache, transpose_data_grid, get_timestamp_with_delta

ADDITIONAL_FIX_TAGS_URL = 'https://raw.githubusercontent.com/jeromegit/fixations/main/data/additional_fixtags.txt'


def get_additional_fixtags_file_url() -> str:
    data_dir_path = 'data'
    if not os.path.exists(data_dir_path):
        data_dir_path = '../data'
        assert os.path.exists(data_dir_path), "Can't find data dir!"
    file_url = f'file://{data_dir_path}/additional_fixtags.txt'

    return file_url


def test_lines_with_no_version():
    empty_lines = ["\n", "\n", "\n"]
    bogus_lines = ["\n", "20111107-10:52:22.133: with some stuff but no FIX signature\n", "\n", "\n"]

    for line_set in [empty_lines, bogus_lines]:
        fix_tag_dict, fix_lines, used_fix_tags, _ = extract_fix_lines_from_str_lines(line_set)
        assert len(fix_tag_dict) + len(fix_lines) + len(used_fix_tags) == 0, "Should not have returned any data"


def create_fix_lines_with_version(fix_version: str) -> List[str]:
    lines_with_ctrl_a = [
        f"<165>Dec 23 09:39:19.424357 CARLSRPXYA: [CARLSR01A] < 8={fix_version}^A9=396^A35=D^A49=MY_SENDERCOMPID^A56=MY_TARGETCOMPDID^A50=MY_SENDERSUBID..."
    ]

    return lines_with_ctrl_a


def test_lines_with_versions():
    assert extract_version_from_first_fix_line(create_fix_lines_with_version('FIX.4.2')) == '4.2'
    assert extract_version_from_first_fix_line(create_fix_lines_with_version('FIX.5.0SP1')) == '5.0SP1'
    assert extract_version_from_first_fix_line(create_fix_lines_with_version('FIXT.1.1')) == '1.1'
    # version specified as a !version=X.Y command
    assert extract_version_from_first_fix_line(["!version=4.2\n"]) == '4.2'
    assert extract_version_from_first_fix_line(["! VERSION = 4.3\n"]) == '4.3'
    assert extract_version_from_first_fix_line(["some bogus line\n", "!version=4.4\n"]) == '4.4'


def test_path_for_fix_versions():
    root_dir = get_cfg_value(CFG_FILE_KEY_FIX_DEFINITIONS_PATH)
    assert path_for_fix_version("4.2") == f"{root_dir}/FIX.4.2/Base"
    assert path_for_fix_version("5.0") == f"{root_dir}/FIX.5.0/Base"
    assert path_for_fix_version("5.0SP1") == f"{root_dir}/FIX.5.0SP1/Base"
    assert path_for_fix_version("1.1") == f"{root_dir}/FIXT.1.1/Base"


def test_fix_versions_available():
    versions = get_list_of_available_fix_versions()
    assert "4.2" in versions
    assert "5.0" in versions
    assert "5.0SP1" in versions
    assert "1.1" in versions


def test_match():
    VERSION_TO_TEST = '8.8'
    with pytest.raises(AssertionError, match=rf"The specified FIX version:{VERSION_TO_TEST} is not valid.*"):
        extract_info_for_fix_version(VERSION_TO_TEST)


def test_extract_timestamp():
    assert tuple_equal(extract_timestamp(""), (None, "ERROR: FIX line w/o timestamp and SENDING_TIME tag52: "))
    assert tuple_equal(extract_timestamp("bogus line"),
                       (None, "ERROR: FIX line w/o timestamp and SENDING_TIME tag52: bogus line"))
    assert tuple_equal(extract_timestamp("bogus line sans timestamp 8=FIX.4", {FIX_TAG_ID_SENDING_TIME: '11:22:33'}),
                       ("11:22:33", None))
    assert tuple_equal(extract_timestamp("8=FIX.4", {FIX_TAG_ID_SENDING_TIME: '11:22:33'}), ("11:22:33", None))
    assert tuple_equal(extract_timestamp("bogus line prefix  1:23:45 and junk 8=FIX.4"), ("1:23:45", None))
    assert tuple_equal(extract_timestamp("bogus line prefix 01:23:45 and junk 8=FIX.4"), ("01:23:45", None))
    assert tuple_equal(extract_timestamp("bogus line prefix 01:23:45 and junk 8=FIX.4"), ("01:23:45", None))
    assert tuple_equal(extract_timestamp("bogus line prefix 01:23:45.678 and junk 8=FIX.4"), ("01:23:45.678", None))
    assert tuple_equal(extract_timestamp("bogus line prefix 01:23:45.678999 and junk 8=FIX.4"),
                       ("01:23:45.678999", None))
    assert tuple_equal(extract_timestamp("bogus line prefix 01:23:45,678 and junk 8=FIX.4"), ("01:23:45,678", None))


def test_line_without_leading_timestamp():
    assert_lines_with_timestamp('')


def test_line_with_leading_timestamp():
    assert_lines_with_timestamp('12:34:56.789')


def assert_lines_with_timestamp(timestamp_prefix):
    TAG52_TIMESTAMP = '20220215-14:30:01.870'
    if timestamp_prefix:
        timestamp = timestamp_prefix
    else:
        timestamp = TAG52_TIMESTAMP

    lines = [
        f"{timestamp_prefix} 8=FIX.4.2 | 9=0192 | 35=D | 34=000006393 | 52={TAG52_TIMESTAMP} | 49=MY_SCID | 56=MY_TCID | " +
        "44=88.7300 | 114=N | 55=GOOG | 8002=0 | 110=1000 | 10=042"]
    _, fix_lines, used_fix_tags, _ = extract_fix_lines_from_str_lines(lines)

    # remove FIX tag's 0-padding
    non_padded_fix_lines = [(timestamp, {k.lstrip('0'): v for k, v in fix_lines[0][1].items()})]
    non_padded_used_fix_tags = {k.lstrip('0'): v for k, v in used_fix_tags.items()}

    assert non_padded_fix_lines == [(timestamp, {'8': 'FIX.4.2',
                                                 '9': '0192',
                                                 '35': 'D (NewOrderSingle)',
                                                 '34': '000006393',
                                                 '52': TAG52_TIMESTAMP,
                                                 '49': 'MY_SCID',
                                                 '56': 'MY_TCID',
                                                 '44': '88.7300',
                                                 '114': 'N (No)',
                                                 '55': 'GOOG',
                                                 '8002': '0',
                                                 '110': '1000',
                                                 '10': '042'})]
    assert non_padded_used_fix_tags == {'8': 1,
                                        '9': 1,
                                        '35': 1,
                                        '34': 1,
                                        '52': 1,
                                        '49': 1,
                                        '56': 1,
                                        '44': 1,
                                        '114': 1,
                                        '55': 1,
                                        '8002': 1,
                                        '110': 1,
                                        '10': 1}


def test_dont_choke_on_emptyish_lines():
    lines = [
        "20220215-14:30:01.870 8=FIX.4.2 | 9=0192 | 35=D | 34=000006393| 49=MY_SCID | 56=MY_TCID | " +
        "44=88.7300 | 114=N | 55=GOOG | 8002=0 | 110=1000 | 10=042",
        None,
        "",  # test empty line
        " \t ",  # test with tab and spaces
    ]
    extract_fix_lines_from_str_lines(lines)


def test_additional_fixtags_with_bogus_urls_and_no_exception_was_raised():
    check_for_additional_fix_definitions('file://bogus/path.txt')
    check_for_additional_fix_definitions('https://bogus.com/path.txt')
    check_for_additional_fix_definitions('https://localhost:23456/path.txt')


def test_transpose_data_grid():
    headers = ['tag_id', 'tag_name', 'time 1', 'time 2']
    rows = [['1', 'one', '1_1', '1_2'],
            ['2', 'two', '2_1', '2_2'],
            ['3', 'three', '3_1', '3_2']
            ]
    expected_headers = ['tag_id', '1', '2', '3']
    expected_rows = [['tag_name', 'one', 'two', 'three'],
                     ['time 1', '1_1', '2_1', '3_1'],
                     ['time 2', '1_2', '2_2', '3_2'],
                     ]
    actual_headers, actual_rows = transpose_data_grid(headers, rows)
    assert expected_headers == actual_headers
    assert expected_rows == actual_rows


def test_additional_fixtags_with_http_url():
    fixtags = check_for_additional_fix_definitions(ADDITIONAL_FIX_TAGS_URL)
    assert '8005' in fixtags


def test_additional_fixtags_with_file_url():
    fixtags = check_for_additional_fix_definitions(get_additional_fixtags_file_url())
    assert '8005' in fixtags


def test_additional_fixtags_was_cached():
    check_for_additional_fix_definitions(get_additional_fixtags_file_url())
    test_additional_fixtags_with_file_url()
    del Additional_tag_cache[get_additional_fixtags_file_url()]['8005']
    fixtags = check_for_additional_fix_definitions(get_additional_fixtags_file_url())
    assert '8005' not in fixtags

    # invalidate the cache and force to refresh/reload it
    fixations.fix_utils.Additional_tag_cache_expiry_time = 0
    fixtags = check_for_additional_fix_definitions(get_additional_fixtags_file_url())
    assert '8005' in fixtags


def test_get_timestamp_with_delta():
    # With None and no subsec
    assert get_timestamp_with_delta("12:34:56", None) == "12:34:56"
    assert get_timestamp_with_delta("12:34:57", "12:34:56") == "12:34:57\n(+1)"

    # negative deltas
    assert get_timestamp_with_delta("12:34:56", "12:34:57") == "12:34:56\n(-1)"
    assert get_timestamp_with_delta("12:34:00", "12:34:57") == "12:34:00\n(-57)"
    assert get_timestamp_with_delta("12:13:00", "12:34:57") == "12:13:00\n(-21:57)"
    assert get_timestamp_with_delta("12:13:00", "12:34:57.123") == "12:13:00\n(-21:57.123)"

    # with sub-second
    assert get_timestamp_with_delta("12:34:57.1", "12:34:56") == "12:34:57.1\n(+1.1)"
    assert get_timestamp_with_delta("12:34:57.222", "12:34:56.111") == "12:34:57.222\n(+1.111)"
    assert get_timestamp_with_delta("12:34:57.222001", "12:34:56.111001") == "12:34:57.222001\n(+1.111)"
    assert get_timestamp_with_delta("12:34:56.123457", "12:34:56.000057") == "12:34:56.123457\n(+.123,400)"
    assert get_timestamp_with_delta("12:34:56.123457", "12:34:56.000007") == "12:34:56.123457\n(+.123,450)"
    assert get_timestamp_with_delta("12:34:56.123457", "12:34:56.000001") == "12:34:56.123457\n(+.123,456)"
    last_us = "23:59:59.999999"
    last_us_with_delta = f"{last_us}\n(+23:59:59.999,999)"
    assert get_timestamp_with_delta(last_us, "00:00:00") == last_us_with_delta
    assert get_timestamp_with_delta(last_us, "00:00:00.000") == last_us_with_delta
    assert get_timestamp_with_delta(last_us, "00:00:00.000000") == last_us_with_delta
    assert get_timestamp_with_delta(last_us, "00:00:00.000001") == "23:59:59.999999\n(+23:59:59.999,998)"

    # Bad format
    assert get_timestamp_with_delta("12:34:57.",
                                    "12:34:56") == "12:34:57.\n(??? time data '12:34:57.' does not match format '%H:%M:%S.%f' ???)"
    assert get_timestamp_with_delta("12:34:57",
                                    "12:34:56.") == "12:34:57\n(??? time data '12:34:56.' does not match format '%H:%M:%S.%f' ???)"

    # With delta total
    delta_total = timedelta(minutes=1, seconds=23)
    timestamp_str = "12:34:56.123457"
    assert get_timestamp_with_delta(timestamp_str, "12:34:56.000001",
                                    delta_total)[0] == f"{timestamp_str}\nΔ:+.123,456\nΣ:+1:23.123,456"
    assert get_timestamp_with_delta(timestamp_str, None, delta_total)[0] == f"{timestamp_str}"


def test_tuple_equal():
    assert tuple_equal((), ())
    assert tuple_equal((), []) is False
    assert tuple_equal((1), (1, 2)) is False
    assert tuple_equal((1), (2)) is False
    assert tuple_equal((1), ('1')) is False
    assert tuple_equal((1, 2), (1, 2))


def tuple_equal(expected, actual):
    if isinstance(expected, tuple) and \
            isinstance(actual, tuple) and \
            len(expected) == len(actual):
        for i in range(0, len(expected)):
            if expected[i] != actual[i]:
                return False
        return True
    else:
        return False
