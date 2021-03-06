# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twistedchecker.core.runner}.
"""

import sys
import os
import StringIO
import operator

from twisted.trial import unittest

import twistedchecker
from twistedchecker.core.runner import Runner
from twistedchecker.reporters.test import TestReporter
from twistedchecker.checkers.header import HeaderChecker

from twistedchecker.test.test_exceptionfinder import (
    createTestFiles as createTestFilesForFindingExceptions)



class RunnerTestCase(unittest.TestCase):
    """
    Test for twistedchecker.core.runner.Runner.
    """
    debug = False

    def setUp(self):
        """
        Redirect stdout to a temp C{StringIO} stream.
        """
        self.outputStream = StringIO.StringIO()
        self.patch(sys, "stdout", self.outputStream)


    def clearOutputStream(self):
        """
        A function to clear output stream.
        """
        self.outputStream = StringIO.StringIO()


    def _loadAllowedMessages(self):
        """
        Load allowed messages from test files.
        """
        pathTests = os.path.join(twistedchecker.abspath, "functionaltests")
        testfiles = reduce(operator.add,
                           [map(lambda f: os.path.join(pathDir, f), files)
                            for pathDir, _, files in os.walk(pathTests)])
        messagesAllowed = set(Runner.allowedMessagesFromPylint)
        for testfile in testfiles:
            firstline = open(testfile).readline().strip()
            if (firstline.startswith("#") and "enable" in firstline
                                          and ":" in firstline):
                messages = firstline.split(":")[1].strip().split(",")
                messagesAllowed.update(messages)
        return messagesAllowed


    def test_findUselessCheckers(self):
        """
        Test for method findUselessCheckers
        """
        runner = Runner()
        registeredCheckers = sum(runner.linter._checkers.values(), [])
        # remove checkers other than header checker
        headerCheckerList = filter(lambda ckr: type(ckr) == HeaderChecker,
                                   registeredCheckers)
        self.assertTrue(headerCheckerList)
        headerChecker = headerCheckerList[0]
        uselessCheckers = runner.findUselessCheckers(
                            headerChecker.msgs.keys()[:1])
        self.assertEqual(len(uselessCheckers) + 1, len(registeredCheckers))
        self.assertTrue(headerChecker not in uselessCheckers)


    def test_unregisterChecker(self):
        """
        Test for method unregisterChecker.

        Remove HeaderChecker from registered,
        and make sure it was removed.
        """
        runner = Runner()
        registeredCheckers = sum(runner.linter._checkers.values(), [])
        # Make sure an instance of HeaderChecker in registered checkers
        headerCheckerList = filter(lambda ckr: type(ckr) == HeaderChecker,
                                   registeredCheckers)
        self.assertTrue(headerCheckerList)
        headerChecker = headerCheckerList[0]
        # Make sure it in option providers
        self.assertTrue(headerChecker in runner.linter.options_providers)
        runner.unregisterChecker(headerChecker)
        # Make sure the instance of HeaderChecker was removed
        registeredCheckers = sum(runner.linter._checkers.values(), [])
        self.assertFalse(headerChecker in registeredCheckers)
        # Could not check reports because HeaderChecker is not be
        # recorded in that list
        # Make sure it was removed from option providers
        self.assertFalse(headerChecker in runner.linter.options_providers)


    def test_restrictCheckers(self):
        """
        Test for method restrictCheckers.

        Manually set allowed messages,
        then check for the result of registered checkers
        after run this method.
        """
        runner = Runner()
        runner.restrictCheckers(HeaderChecker.msgs.keys()[:1])
        # After run it, only HeaderChecker should be left in
        # registered checkers
        registeredCheckers = sum(runner.linter._checkers.values(), [])
        self.assertEqual(len(registeredCheckers), 1)
        self.assertEqual(type(registeredCheckers[0]), HeaderChecker)


    def test_allMessagesAreRegistered(self):
        """
        A test to assume all tests are registered to reporter.
        """
        linter = Runner().linter
        messagesFromTests = self._loadAllowedMessages()
        messagesFromReporter = linter.reporter.messagesAllowed
        messagesDisabled = set(linter
                           .cfgfile_parser.get("TWISTEDCHECKER", "disable")
                           .replace(" ", "").split(","))
        self.assertEqual(messagesFromTests - messagesDisabled,
                         messagesFromReporter)


    def test_run(self):
        """
        Pass argument "--version" to C{runner.run}, and it should show
        a version infomation, then exit. So that I could know it called pylint.
        """
        self.clearOutputStream()
        runner = Runner()
        runner.setOutput(self.outputStream)
        self.assertRaises(SystemExit, runner.run, ["--version"])
        self.assertTrue(self.outputStream.getvalue().count("Python") > 0, \
                        msg="failed to call pylint")


    def test_parseWarnings(self):
        """
        Test for twistedchecker.core.runner.Runner.parseWarnings.
        """
        textWarnings = """
************* Module foo
W9001:  1,0: Missing copyright header
************* Module bar
W9002:  1,0: Missing a reference to test module in header
C0111:  10,0: Missing docstring
        """.strip()

        warningsCorrect = {
            "foo": {"W9001:  1,0: Missing copyright header", },
            "bar": {"W9002:  1,0: Missing a reference "
                    "to test module in header",
                    "C0111:  10,0: Missing docstring"
                   }
        }

        warnings = Runner().parseWarnings(textWarnings)
        self.assertEqual(warnings, warningsCorrect)


    def test_formatWarnings(self):
        """
        Test for twistedchecker.core.runner.Runner.formatWarnings.
        """
        warnings = {
            "foo": {"W9001:  1,0: Missing copyright header", },
            "bar": {"W9002:  1,0: Missing a reference "
                    "to test module in header",
                    "C0111:  10,0: Missing docstring"
                   }
        }

        resultCorrect = """
************* Module foo
W9001:  1,0: Missing copyright header
************* Module bar
W9002:  1,0: Missing a reference to test module in header
C0111:  10,0: Missing docstring
        """.strip()

        result = Runner().formatWarnings(warnings)
        self.assertEqual(result, resultCorrect)


    def test_generateDiff(self):
        """
        Test for twistedchecker.core.runner.Runner.generateDiff.
        """
        oldWarnings = {
            "foo": {"W9001:  1,0: Missing copyright header"},
            "bar": {
                "W9002:  1,0: Missing a reference to test module in header",
                "C0111:  10,0: Missing docstring"
            }
        }

        newWarnings = {
            "foo": {
                "W9001:  1,0: Missing copyright header",
                "C0301: 10,0: Line too long"
            },
            "bar": {
                "W9002:  1,0: Missing a reference to test module in header",
                "C0111:  10,0: Missing docstring"
            },
            "baz": {
                "W9001:  1,0: Missing copyright header"
            }
        }

        diffCorrect = {
            "foo": {"C0301: 10,0: Line too long"},
            "baz": {"W9001:  1,0: Missing copyright header"}
        }

        # Make sure generated diff is correct.
        diff = Runner().generateDiff(oldWarnings, newWarnings)
        self.assertEqual(diff, diffCorrect)


    def test_getPathList(self):
        """
        Test for twistedchecker.core.runner.Runner.getPathList.
        """
        workingDir = os.getcwd()
        pathTwistedchecker = os.path.dirname(twistedchecker.__path__[0])
        inputList = [os.path.join("twistedchecker","functionaltests"),
                     "twistedchecker.core.util"]
        correctPaths = [os.path.join("twistedchecker","functionaltests"),
                        os.path.join("twistedchecker","core","util.py")]
        os.chdir(pathTwistedchecker)
        result = Runner().getPathList(inputList)
        # transform them to relative path.
        result = [os.path.relpath(path) for path in result]
        os.chdir(workingDir)

        self.assertEqual(result, correctPaths)


    def test_setNameExceptions(self):
        """
        Test for twistedchecker.core.runner.Runner.setNameExceptions.
        """
        pathTestFiles = createTestFilesForFindingExceptions(self.mktemp())
        self.clearOutputStream()
        runner = Runner()
        runner.setOutput(self.outputStream)
        # Set the reporter to C{twistedchecker.reporters.test.TestReporter}.
        runner.setReporter(TestReporter())
        # Limit messages.
        runner.linter.disable_noerror_messages()
        runner.linter.enable("C0103")

        workingDir = os.getcwd()
        os.chdir(os.path.dirname(pathTestFiles))
        moduleName = os.path.basename(pathTestFiles)
        runner.run([moduleName])
        os.chdir(workingDir)

        predictResult = "11:C0103\n14:C0103\n15:C0103\n"
        outputResult = self.outputStream.getvalue()
        self.assertEqual(outputResult, predictResult)
