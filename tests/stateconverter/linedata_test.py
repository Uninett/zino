from zino.stateconverter.linedata import get_line_data


def test_only_quotes_on_start_and_end_of_value_are_removed():
    test_line = 'set ::EventAttrs_100(log) "{15000000 intf "ge-0/0/1" is down}"'
    expected_value = '{15000000 intf "ge-0/0/1" is down}'
    linedata = get_line_data(test_line)
    assert linedata.value == expected_value


def test_identifiers_are_parsed_correctly_for_event_attrs():
    test_line = 'set ::EventAttrs_100(log) "{15000000 intf "ge-0/0/1" is down}"'
    expected_identifiers = tuple(["log", "100"])
    linedata = get_line_data(test_line)
    assert linedata.identifiers == expected_identifiers


def test_identifiers_are_parsed_in_correct_order():
    test_line = 'set ::SomeCommand(id1,id2,id3) "some value"'
    expected_identifiers = tuple(["id1", "id2", "id3"])
    linedata = get_line_data(test_line)
    assert linedata.identifiers == expected_identifiers


def test_can_parse_global_setters():
    test_line = 'set ::pm::lastid "10"'
    linedata = get_line_data(test_line)
    assert linedata.value == "10"
    assert linedata.identifiers is None
