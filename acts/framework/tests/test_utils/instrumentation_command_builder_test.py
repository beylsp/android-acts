import unittest

from acts.test_utils.instrumentation_tests.instrumentation_command_builder \
    import InstrumentationCommandBuilder
from acts.test_utils.instrumentation_tests.instrumentation_command_builder \
    import InstrumentationTestCommandBuilder


class InstrumentationCommandBuilderTest(unittest.TestCase):

    def test__runner_and_manifest_package_definition(self):
        builder = InstrumentationCommandBuilder()
        builder.set_manifest_package('package')
        builder.set_runner('runner')
        call = builder.build()
        self.assertIn('package/runner', call)

    def test__manifest_package_must_be_defined(self):
        builder = InstrumentationCommandBuilder()

        with self.assertRaisesRegex(Exception, '.*package cannot be none.*'):
            builder.build()

    def test__runner_must_be_defined(self):
        builder = InstrumentationCommandBuilder()

        with self.assertRaisesRegex(Exception, '.*runner cannot be none.*'):
            builder.build()

    def test__key_value_param_definition(self):
        builder = InstrumentationCommandBuilder()
        builder.set_runner('runner')
        builder.set_manifest_package('some.manifest.package')

        builder.add_key_value_param('my_key_1', 'my_value_1')
        builder.add_key_value_param('my_key_2', 'my_value_2')

        call = builder.build()
        self.assertIn('-e my_key_1 my_value_1', call)
        self.assertIn('-e my_key_2 my_value_2', call)

    def test__flags(self):
        builder = InstrumentationCommandBuilder()
        builder.set_runner('runner')
        builder.set_manifest_package('some.manifest.package')

        builder.add_flag('--flag1')
        builder.add_flag('--flag2')

        call = builder.build()
        self.assertIn('--flag1', call)
        self.assertIn('--flag2', call)


class InstrumentationTestCommandBuilderTest(unittest.TestCase):
    """Test class for
    acts/test_utils/instrumentation_tests/instrumentation_call_builder.py
    """

    def test__test_packages_can_not_be_added_if_classes_were_added_first(self):
        builder = InstrumentationTestCommandBuilder()
        builder.add_tests_class('some.tests.Class')

        with self.assertRaisesRegex(Exception, '.*only a list of classes.*'):
            builder.add_tests_package('some.tests.package')

    def test__test_classes_can_not_be_added_if_packages_were_added_first(self):
        builder = InstrumentationTestCommandBuilder()
        builder.add_tests_package('some.tests.package')

        with self.assertRaisesRegex(Exception, '.*only a list of classes.*'):
            builder.add_tests_class('some.tests.Class')

    def test__test_classes_and_test_methods_can_be_combined(self):
        builder = InstrumentationTestCommandBuilder()
        builder.set_runner('runner')
        builder.set_manifest_package('some.manifest.package')
        builder.add_tests_class('some.tests.Class1')
        builder.add_test_method('some.tests.Class2', 'favoriteTestMethod')

        call = builder.build()
        self.assertIn('some.tests.Class1', call)
        self.assertIn('some.tests.Class2', call)
        self.assertIn('favoriteTestMethod', call)


if __name__ == '__main__':
    unittest.main()
