class TestTypeConversionError:
    pass


class TestCondition:
    def test___str__(self):  # synced
        assert True

    def test___call__(self):  # synced
        assert True

    def test_extract_name_from_condition(self):  # synced
        assert True


class TestValidatorMeta:
    pass


class TestValidator:
    def test___str__(self):  # synced
        assert True

    def test___call__(self):  # synced
        assert True

    def test_set_nullable(self):  # synced
        assert True

    def test_set_choices(self):  # synced
        assert True

    def test_add_condition(self):  # synced
        assert True

    def test_add_conditions(self):  # synced
        assert True

    def test_is_valid(self):  # synced
        assert True

    def test_convert(self):  # synced
        assert True

    def test__to_subtype(self):  # synced
        assert True

    def test__pre_process(self):  # synced
        assert True


class TestAnythingValidator:
    class TestAnything:
        def test_is_type(self):  # synced
            assert True

        def test_convert(self):  # synced
            assert True


class TestUnknownTypeValidator:
    def test_convert(self):  # synced
        assert True


class TestBooleanValidator:
    pass


class TestStringValidator:
    def test_max_len(self):  # synced
        assert True

    def test_min_len(self):  # synced
        assert True

    def test__to_subtype(self):  # synced
        assert True


class TestNumericValidator:
    def test_max_value(self):  # synced
        assert True

    def test_min_value(self):  # synced
        assert True


class TestIntegerValidator:
    pass


class TestFloatValidator:
    class TestFloat:
        def test_convert(self):  # synced
            assert True


class TestDecimalValidator:
    class TestDecimal:
        pass


class TestParametrizableValidator:
    def test__pre_process(self):  # synced
        assert True


class TestListValidator:
    def test___str__(self):  # synced
        assert True

    def test_parametrize(self):  # synced
        assert True

    def test_of_type(self):  # synced
        assert True

    def test_is_valid(self):  # synced
        assert True

    def test_convert(self):  # synced
        assert True

    def test__to_subtype(self):  # synced
        assert True


class TestSetValidator:
    class TestSet:
        def test_convert(self):  # synced
            assert True


class TestDictionaryValidator:
    def test___str__(self):  # synced
        assert True

    def test_is_parametrized(self):  # synced
        assert True

    def test_parametrize(self):  # synced
        assert True

    def test_of_type(self):  # synced
        assert True

    def test_is_valid(self):  # synced
        assert True

    def test_convert(self):  # synced
        assert True

    def test__to_subtype(self):  # synced
        assert True


class TestDateTimeValidator:
    def test_before(self):  # synced
        assert True

    def test_after(self):  # synced
        assert True

    def test__to_subtype(self):  # synced
        assert True


class TestDateValidator:
    class TestDate:
        def test_convert(self):  # synced
            assert True

    def test__to_subtype(self):  # synced
        assert True


class TestPathValidator:
    class TestPath:
        def test_is_type(self):  # synced
            assert True

        def test_convert(self):  # synced
            assert True


class TestFileValidator:
    class TestFile:
        def test_is_type(self):  # synced
            assert True

        def test_convert(self):  # synced
            assert True


class TestDirValidator:
    class TestDir:
        def test_is_type(self):  # synced
            assert True

        def test_convert(self):  # synced
            assert True


class TestValidate:
    def test_infer_type(self):  # synced
        assert True
