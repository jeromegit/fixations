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
    assert extract_timestamp("") is None
    assert extract_timestamp("bogus line") is None
    assert extract_timestamp("bogus line sans timestamp 8=FIX.4", {FIX_TAG_ID_SENDING_TIME:'11:22:33'}) == "11:22:33"
    assert extract_timestamp("bogus line prefix  1:23:45 and junk 8=FIX.4") == "1:23:45"
    assert extract_timestamp("bogus line prefix 01:23:45 and junk 8=FIX.4") == "01:23:45"
    assert extract_timestamp("bogus line prefix 01:23:45 and junk 8=FIX.4") == "01:23:45"
    assert extract_timestamp("bogus line prefix 01:23:45.678 and junk 8=FIX.4") == "01:23:45.678"
    assert extract_timestamp("bogus line prefix 01:23:45.678999 and junk 8=FIX.4") == "01:23:45.678999"
    assert extract_timestamp("bogus line prefix 01:23:45,678 and junk 8=FIX.4") == "01:23:45,678"

