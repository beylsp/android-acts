#!/usr/bin/env python3
#
#   Copyright 2018 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from functools import partial
from mock import Mock
from mock import patch
import unittest
from unittest import TestCase
from acts.event.event import TestCaseEvent
from acts.event.event import TestCaseBeginEvent
from acts.event.event import TestCaseEndEvent
from acts.event.event import TestClassEvent
from acts.event.event import TestClassBeginEvent
from acts.event.event import TestClassEndEvent
from acts.context import get_context_for_event
from acts.context import get_current_context
from acts.context import _update_test_class_context
from acts.context import _update_test_case_context
from acts.context import TestContext
from acts.context import TestCaseContext
from acts.context import TestClassContext

LOGGING = 'acts.context.logging'


class TestClass:
    def __init__(self):
        self.test_name = self.test_case.__name__

    def test_case(self):
        pass


class ModuleTest(TestCase):
    """Unit tests for the context module."""

    def test_get_context_for_event_for_test_case(self):
        event = Mock(spec=TestCaseEvent)
        event.test_class = Mock()
        event.test_case = Mock()
        context = get_context_for_event(event)

        self.assertIsInstance(context, TestCaseContext)
        self.assertEqual(context.test_class, event.test_class)
        self.assertEqual(context.test_case, event.test_case)

    def test_get_context_for_event_for_test_class(self):
        event = Mock(spec=TestClassEvent)
        event.test_class = Mock()
        context = get_context_for_event(event)

        self.assertIsInstance(context, TestClassContext)
        self.assertEqual(context.test_class, event.test_class)

    def test_get_context_for_unknown_event_type(self):
        event = Mock()

        self.assertRaises(TypeError, partial(get_context_for_event, event))

    def test_update_test_class_context_for_test_class_begin(self):
        event = Mock(spec=TestClassBeginEvent)
        event.test_class = Mock()

        _update_test_class_context(event)
        self.assertIsInstance(get_current_context(), TestClassContext)

    def test_update_test_class_context_for_test_class_end(self):
        event = Mock(spec=TestClassBeginEvent)
        event.test_class = Mock()
        event2 = Mock(spec=TestClassEndEvent)
        event2.test_class = Mock()

        _update_test_class_context(event)
        _update_test_class_context(event2)

        self.assertIsNone(get_current_context())

    def test_update_test_case_context_for_test_case_begin(self):
        event = Mock(spec=TestClassBeginEvent)
        event.test_class = Mock()
        event2 = Mock(spec=TestCaseBeginEvent)
        event2.test_class = Mock()
        event2.test_case = Mock()

        _update_test_class_context(event)
        _update_test_case_context(event2)

        self.assertIsInstance(get_current_context(), TestCaseContext)

    def test_update_test_case_context_for_test_case_end(self):
        event = Mock(spec=TestClassBeginEvent)
        event.test_class = Mock()
        event2 = Mock(spec=TestCaseBeginEvent)
        event2.test_class = Mock()
        event2.test_case = Mock()
        event3 = Mock(spec=TestCaseEndEvent)
        event3.test_class = Mock()
        event3.test_case = Mock()

        _update_test_class_context(event)
        _update_test_case_context(event2)
        _update_test_case_context(event3)

        self.assertIsInstance(get_current_context(), TestClassContext)


class TestContextTest(TestCase):
    """Unit tests for the TestContext class."""

    @patch(LOGGING)
    def test_get_base_output_path_uses_default(self, logging):
        context = TestContext()

        self.assertEqual(context.get_base_output_path(), logging.log_path)

    def test_set_base_output_path_overrides_default(self):
        context = TestContext()
        mock_path = Mock()

        context.set_base_output_path(mock_path)

        self.assertEqual(context.get_base_output_path(), mock_path)

    def test_get_output_dir_attempts_to_use_default(self):
        context = TestContext()

        self.assertRaises(NotImplementedError, context.get_output_dir)

    def test_set_output_dir_overrides_default(self):
        context = TestContext()
        mock_dir = Mock()

        context.set_output_dir(mock_dir)

        self.assertEqual(context.get_output_dir(), mock_dir)

    def test_get_full_output_path_returns_correct_path(self):
        context = TestContext()
        path = 'base/path'
        dir = 'output/dir'
        context.set_base_output_path(path)
        context.set_output_dir(dir)

        full_path = 'base/path/output/dir'
        self.assertEqual(context.get_full_output_path(), full_path)

    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_get_full_output_path_makes_directory(self, makedirs, exists):
        exists.return_value = False

        context = TestContext()
        path = 'base/path'
        dir = 'output/dir'
        context.set_base_output_path(path)
        context.set_output_dir(dir)

        full_path = 'base/path/output/dir'
        context.get_full_output_path()

        self.assertTrue(makedirs.called)
        self.assertEqual(makedirs.call_args[0][0], full_path)

    def test_identifier_not_implemented(self):
        context = TestContext()

        self.assertRaises(NotImplementedError, lambda: context.identifier)


class TestClassContextTest(TestCase):
    """Unit tests for the TestClassContext class."""

    def test_init_attributes(self):
        test_class = Mock()
        context = TestClassContext(test_class)

        self.assertEqual(context.test_class, test_class)

    def test_get_class_name(self):
        class TestClass:
            pass
        test_class = TestClass()
        context = TestClassContext(test_class)

        self.assertEqual(context.test_class_name, TestClass.__name__)

    def test_get_output_dir_is_class_name(self):
        class TestClass:
            pass
        test_class = TestClass()
        context = TestClassContext(test_class)

        self.assertEqual(context.get_output_dir(), TestClass.__name__)

    def test_identifier_is_class_name(self):
        class TestClass:
            pass
        test_class = TestClass()
        context = TestClassContext(test_class)

        self.assertEqual(context.identifier, TestClass.__name__)


class TestCaseContextTest(TestCase):
    """Unit tests for the TestCaseContext class."""

    def test_init_attributes(self):
        test_case = Mock()
        test_case.__name__ = 'test_case_name'
        test_class = Mock()
        test_class.test_name = test_case.__name__
        context = TestCaseContext(test_class, test_case)

        self.assertEqual(context.test_class, test_class)
        self.assertEqual(context.test_case, test_case)
        self.assertEqual(context.test_case_name, test_case.__name__)

    def test_get_class_name(self):
        class TestClass:
            pass
        test_class = TestClass()
        test_case_name = Mock()
        context = TestCaseContext(test_class, test_case_name)

        self.assertEqual(context.test_class_name, TestClass.__name__)

    def test_get_output_dir_is_class_and_test_case_name(self):
        test_class = TestClass()
        test_case = TestClass.test_case
        context = TestCaseContext(test_class, test_case)

        output_dir = TestClass.__name__ + '/' + test_case.__name__
        self.assertEqual(context.get_output_dir(), output_dir)

    def test_identifier_is_class_and_test_case_name(self):
        test_class = TestClass()
        test_case = TestClass.test_case
        context = TestCaseContext(test_class, test_case)

        identifier = TestClass.__name__ + '.' + test_case.__name__
        self.assertEqual(context.identifier, identifier)


if __name__ == '__main__':
    unittest.main()
