class TestDeclarativeMeta:
    def test__handle_argument_(self):  # synced
        assert True

    def test__handle_group_(self):  # synced
        assert True

    def test__handle_command_(self):  # synced
        assert True


class TestCommandMeta:
    def test__handle_command_(self):  # synced
        assert True


class TestCommand:
    def test___call__(self):  # synced
        assert True

    def test___getitem__(self):  # synced
        assert True

    def test___setitem__(self):  # synced
        assert True

    def test___getattr__(self):  # synced
        assert True

    def test__callback_(self):  # synced
        assert True


class TestGroupMeta:
    def test__handle_command_(self):  # synced
        assert True


class TestGroup:
    def test___getattr__(self):  # synced
        assert True


class TestInclusiveGroup:
    pass


class TestExclusiveGroup:
    pass


class TestArgumentGroup:
    pass
