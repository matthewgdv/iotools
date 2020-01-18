# import pytest


class TestRunMode:
    pass


class TestArgType:
    pass


class TestIOHandler:
    def test_add_argument(self):  # synced
        assert True

    def test_add_subcommand(self):  # synced
        assert True

    def test_process(self):  # synced
        assert True

    def test_show_output(self):  # synced
        assert True

    def test_clear_output(self):  # synced
        assert True

    def test__choose_handler_method(self):  # synced
        assert True

    def test__save_latest_input_config(self):  # synced
        assert True

    def test__load_latest_input_config(self):  # synced
        assert True

    def test__determine_shortform_alias(self):  # synced
        assert True

    def test__validate_arg_name(self):  # synced
        assert True


class TestArgument:
    def test___str__(self):  # synced
        assert True

    def test_value(self):  # synced
        assert True

    def test_aliases(self):  # synced
        assert True

    def test_commandline_aliases(self):  # synced
        assert True

    def test_add(self):  # synced
        assert True


class TestDependency:
    class TestMode:
        pass

    def test___str__(self):  # synced
        assert True

    def test___bool__(self):  # synced
        assert True

    def test_bind(self):  # synced
        assert True

    def test_validate(self):  # synced
        assert True


class TestNullability:
    def test___str__(self):  # synced
        assert True

    def test___bool__(self):  # synced
        assert True


class TestCallableDict:
    def test___call__(self):  # synced
        assert True
