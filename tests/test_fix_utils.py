import pytest

from fixations.fix_utils import extract_fix_lines_from_str_lines, extract_tag_dict_for_fix_version


def test_lines_with_no_version():
    empty_lines = ["\n", "\n", "\n"]
    bogus_lines = ["\n", "20111107-10:52:22.133: with some stuff but no FIX signature\n", "\n", "\n"]

    for line_set in [empty_lines, bogus_lines]:
        fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(line_set)
        assert len(fix_tag_dict) + len(fix_lines) + len(used_fix_tags) == 0, "Should not have returned any data"


def test_match():
    VERSION_TO_TEST = '8.8'
    with pytest.raises(AssertionError, match=rf"The specified FIX version:{VERSION_TO_TEST} is not valid.*"):
        extract_tag_dict_for_fix_version(VERSION_TO_TEST)
