import pytest

from fixations.fix_utils import extract_fix_lines_from_str_lines, extract_tag_dict_for_fix_version, \
    extract_version_from_first_fix_line, extract_timestamp, FIX_TAG_ID_SENDING_TIME


def test_lines_with_no_version():
    empty_lines = ["\n", "\n", "\n"]
    bogus_lines = ["\n", "20111107-10:52:22.133: with some stuff but no FIX signature\n", "\n", "\n"]

    for line_set in [empty_lines, bogus_lines]:
        fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(line_set)
        assert len(fix_tag_dict) + len(fix_lines) + len(used_fix_tags) == 0, "Should not have returned any data"


def test_lines_with_versions():
    line_with_ctrl_a = [
        "<165>Dec 23 09:39:19.424357 CARLSRPXYA: [CARLSR01A] < 8=FIX.4.2^A9=396^A35=D^A49=MY_SENDERCOMPID^A56=MY_TARGETCOMPDID^A50=MY_SENDERSUBID..."]
    version = extract_version_from_first_fix_line(line_with_ctrl_a)
    assert version == '4.2'


def test_match():
    VERSION_TO_TEST = '8.8'
    with pytest.raises(AssertionError, match=rf"The specified FIX version:{VERSION_TO_TEST} is not valid.*"):
        extract_tag_dict_for_fix_version(VERSION_TO_TEST)


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


def test_line_without_leading_tmestamp():
    assert_lines_with_timestamp('')


def test_line_with_leading_tmestamp():
    assert_lines_with_timestamp('12:34:56.789')


def assert_lines_with_timestamp(timestamp_prefix=None):
    TAG52_TIMESTAMP = '20220215-14:30:01.870'
    if timestamp_prefix:
        timestamp = timestamp_prefix
    else:
        timestamp = TAG52_TIMESTAMP

    lines = [
        f"{timestamp_prefix} 8=FIX.4.2 | 9=0192 | 35=D | 34=000006393 | 52={TAG52_TIMESTAMP} | 49=MY_SCID | 56=MY_TCID | " +
        "44=88.7300 | 114=N | 55=GOOG | 8002=0 | 110=1000 | 10=042"]
    fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(lines)
    assert fix_lines == [(timestamp, {'8': 'FIX.4.2',
                                      '9': '0192',
                                      '35': 'D (NewOrderSingle)',
                                      '34': '000006393',
                                      '52': '20220215-14:30:01.870',
                                      '49': 'MY_SCID',
                                      '56': 'MY_TCID',
                                      '44': '88.7300',
                                      '114': 'N (No)',
                                      '55': 'GOOG',
                                      '8002': '0',
                                      '110': '1000',
                                      '10': '042'})]
    assert used_fix_tags == {'8': 1,
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


def test_tuple_equal():
    assert tuple_equal((), ())
    assert tuple_equal((), []) is False
    assert tuple_equal((1), (1, 2)) is False
    assert tuple_equal((1), (2)) is False
    assert tuple_equal((1), ('1')) is False
    assert tuple_equal((1, 2), (1, 2))


def tuple_equal(expected, actual):
    if type(expected) == tuple and \
            type(actual) == tuple and \
            len(expected) == len(actual):
        for i in range(0, len(expected)):
            if expected[i] != actual[i]:
                return False
        return True
    else:
        return False
