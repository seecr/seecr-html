# -*- coding: utf-8 -*-
## begin license ##
#
# "Meresco Html" is a template engine based on generators, and a sequel to Slowfoot.
# It is also known as "DynamicHtml" or "Seecr Html".
#
# Copyright (C) 2008-2011 Seek You Too (CQ2) http://www.cq2.nl
# Copyright (C) 2011-2014, 2017-2018 Seecr (Seek You Too B.V.) http://seecr.nl
# Copyright (C) 2017 St. IZW (Stichting Informatievoorziening Zorg en Welzijn) http://izw-naz.nl
#
# This file is part of "Meresco Html"
#
# "Meresco Html" is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# "Meresco Html" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "Meresco Html"; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
## end license ##

from io import StringIO
import sys
from os import makedirs, rename, remove
from os.path import join

from seecr.test import SeecrTestCase, CallTrace

from weightless.core import compose, Yield, asString
from weightless.io import Reactor, reactor
from weightless.io.utils import asProcess, sleep as zleep

from meresco.html import DynamicHtml, Tag


class DynamicHtmlTest(SeecrTestCase):
    def testFileNotFound(self):
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/a/path', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 404 Not Found\r\nContent-Type: text/html; charset=utf-8\r\n\r\nFile "a" does not exist.', result)

    def testFileNotFound2(self):
        with open(join(self.tempdir, 'a.sf'), 'w') as f:
            f.write('def main(pipe, **kwargs):\n yield pipe')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/a/path', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue(result.startswith('HTTP/1.0 404 Not Found'), result)
        self.assertTrue('File "path" does not exist.' in result, result)

    def testCustomFileNotFound(self):
        with open(join(self.tempdir, 'not_found_template.sf'), 'w') as f:
            f.write("""
def main(**kwargs):
    yield "404 Handler"
""")
        d = DynamicHtml([self.tempdir], notFoundPage="/not_found_template", reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/a/path', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        headers, body = result.split('\r\n\r\n')
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8', headers)
        self.assertEqual('404 Handler', body)

    def testCustomFileNotFound_path_is_originalPath(self):
        with open(join(self.tempdir, "not_found_template.sf"), 'w') as f:
            f.write("""
def main(path, **kwargs):
    yield path
""")
        d = DynamicHtml([self.tempdir], notFoundPage="/not_found_template", reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/a/path', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        headers, body = result.split('\r\n\r\n')
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8', headers)
        self.assertEqual('/a/path', body)

    def testNotFound_HeadExistButHasNoMain(self):
        with open(self.tempdir + '/page.sf', 'w') as f:
            f.write("""""")
        with open(self.tempdir + '/_missing.sf', 'w') as f:
            f.write("""
def main(**kw):
    yield 'not-found'
""")
        reactor = Reactor()
        # /page
        d = DynamicHtml([self.tempdir], reactor=reactor, notFoundPage='/_missing')
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/page')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('not-found', message)

        # /page/does-not-exist
        d = DynamicHtml([self.tempdir], reactor=reactor, notFoundPage='/_missing')
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/page/does-not-exist')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('not-found', message)

    def testCustomFileNotFoundToFileThatDoesExist(self):
        d = DynamicHtml([self.tempdir], notFoundPage="/not_found_template", reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/a/path', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        headers, body = result.split('\r\n\r\n')
        self.assertEqual('HTTP/1.0 404 Not Found\r\nContent-Type: text/html; charset=utf-8', headers)
        self.assertEqual('File "not_found_template" does not exist.', body)

    def testASimpleFlatFile(self):
        with open(self.tempdir+'/afile.sf', 'w') as f:
            f.write('def main(*args, **kwargs): \n  yield "John is a nut"')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/afile', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\nJohn is a nut', result)

    def testPrefix(self):
        with open(self.tempdir+'/afile.sf', 'w') as f:
            f.write('def main(*args, **kwargs): \n  yield "John is a nut"')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'), prefix='/prefix')
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/prefix/afile', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\nJohn is a nut', result)

    def testSimpleGenerator(self):
        with open(self.tempdir+'/testSimple.sf', 'w') as f:
            f.write("""
def main(*args, **kwargs):
  for n in ('aap', 'noot', 'mies'):
    yield str(n)
"""
        )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\naapnootmies', result)

    def testIncludeOther(self):
        with open(self.tempdir+'/simple.sf', 'w') as f:
            f.write("""
def main(*args, **kwargs):
    yield 'is'
    yield 'snake'
"""
        )
        with open(self.tempdir+'/other.sf', 'w') as f:
            f.write("""
import simple
def main(*args, **kwargs):
    yield 'me'
    yield simple.main()
"""
        )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(compose(s.handleRequest(scheme='http', netloc='host.nl', path='/other', query='?query=something', fragments='#fragments', arguments={'query': 'something'})))
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\nmeissnake', result)

    def testUseModuleLocals(self):
        with open(self.tempdir+'/testSimple.sf', 'w') as f:
            f.write("""
moduleLocal = "local is available"
def main(*args, **kwargs):
    yield moduleLocal
"""
            )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue('local is available' in result, result)

    def testUseModuleLocalsRecursive(self):
        with open(self.tempdir+'/testSimple.sf', 'w') as f:
            f.write("""
def recursiveModuleLocal(recurse):
    if recurse:
        return recursiveModuleLocal(recurse=False)
    return "recursiveModuleLocal result"

def main(*args, **kwargs):
    yield recursiveModuleLocal(recurse=True)
"""
            )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue('recursiveModuleLocal result' in result, result)

    def testUseModuleLocalsCrissCross(self):
        with open(self.tempdir+'/testSimple.sf', 'w') as f:
            f.write("""
def f():
    return "f()"

def g():
    return "g(%s)" % f()

def main(*args, **kwargs):
    yield g()
"""
            )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue('g(f())' in result, result)

    def testErrorWhileImporting(self):
        sys.stderr = StringIO()
        try:
            open(self.tempdir+'/testSimple.sf', 'w').write("""
x = 1/0
def main(*args, **kwargs):
  pass
"""
            )
            s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
            result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))

            self.assertTrue('x = 1/0\nZeroDivisionError: division by zero' in result)
        finally:
            sys.stderr = sys.__stderr__

    def testRuntimeError(self):
        with open(self.tempdir+'/testSimple.sf', 'w') as f:
            f.write("""
def main(*args, **kwargs):
  yield 1/0
  yield "should not get here"
"""
        )
        s = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(s.handleRequest(scheme='http', netloc='host.nl', path='/testSimple', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue("HTTP/1.0 500 Internal Server Error\r\n\r\n" in result, result)
        self.assertTrue("division by zero" in result, result)

    def testObservability(self):
        onces = []
        dos = []
        class Something(object):
            def callSomething(self, *args, **kwargs):
                return "call"
            def allSomething(self, *args, **kwargs):
                yield "all"
            def anySomething(self, *args, **kwargs):
                yield "any"
                return 'retval'
            def doSomething(self, *args, **kwargs):
                dos.append(True)
            def onceSomething(self, *args, **kwargs):
                onces.append(True)

        with open(self.tempdir+'/afile.sf', 'w') as f:
            f.write("""#
def main(*args, **kwargs):
  result = observable.call.callSomething()
  yield result
  yield observable.all.allSomething()
  result = yield observable.any.anySomething()
  assert result == 'retval'
  observable.do.doSomething()
  yield observable.once.onceSomething()
""")
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        d.addObserver(Something())
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/afile', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.maxDiff = None
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\ncallallany', ''.join(result))

        self.assertEqual([True], dos)
        self.assertEqual([True], onces)

    def testObservabilityOutsideMainOnModuleLevel(self):
        class X(object):
            def getX(*args, **kwargs):
                return "eks"

        with open(self.tempdir+'/afile.sf', 'w') as f:
            f.write("""#
x = observable.call.getX()
def main(*args, **kwargs):
  yield x
""")
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        d.addObserver(X())
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/afile', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\neks', ''.join(result))


    def testHeaders(self):
        reactor = Reactor()

        d = DynamicHtml([self.tempdir], reactor=reactor)
        with open(self.tempdir+'/file.sf', 'w') as f:
            f.write("""
def main(Headers={}, *args, **kwargs):
    yield str(Headers)
""")
        reactor.step()

        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file', query='?query=something', fragments='#fragments', arguments={'query': 'something'}, Headers={'key': 'value'})
        self.assertEqual("""HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{'key': 'value'}""", ''.join(result))


    def XtestCreateFileCausesReload(self):
        reactor = Reactor()

        d = DynamicHtml([self.tempdir], reactor=reactor)
        open(self.tempdir+'/file1.sf', 'w').write('def main(*args, **kwargs): \n  yield "one"')
        reactor.step()

        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\none', ''.join(result))

    def XtestModifyFileCausesReload(self):
        reactor = Reactor()

        open(self.tempdir+'/file1.sf', 'w').write('def main(*args, **kwargs): \n  yield "one"')
        d = DynamicHtml([self.tempdir], reactor=reactor)

        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\none', ''.join(result))

        open(self.tempdir+'/file1.sf', 'w').write('def main(*args, **kwargs): \n  yield "two"')
        reactor.step()

        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\ntwo', ''.join(result))

    def XtestNoDirectoryWatcherAddedToReactorWhenNotWatch(self):
        reactor = CallTrace('reactor')
        d = DynamicHtml([self.tempdir], reactor=reactor, watch=False)
        self.assertEqual([], reactor.calledMethodNames())

    def XtestNoReactorWorksJustNoWatcher(self):
        open(self.tempdir+'/afile.sf', 'w').write('def main(*args, **kwargs): \n  yield "John is a nut"')
        d = DynamicHtml([self.tempdir], reactor=None)
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/afile', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\nJohn is a nut', result)

    def XtestFileMovedIntoDirectoryCausesReload(self):
        reactor = Reactor()

        open('/tmp/file1.sf', 'w').write('def main(*args, **kwargs): \n  yield "one"')
        d = DynamicHtml([self.tempdir], reactor=reactor)

        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertEqual('HTTP/1.0 404 Not Found\r\nContent-Type: text/html; charset=utf-8\r\n\r\nFile "file1" does not exist.', result)

        rename('/tmp/file1.sf', self.tempdir+'/file1.sf')
        reactor.step()

        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\none', ''.join(result))

    def XtestReloadImportedModules(self):
        reactor = Reactor()

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(value, *args, **kwargs):
    return "original template %s" % value
""")
        open(self.tempdir + '/file2.sf', 'w').write("""
import file1

def main(*args, **kwargs):
   yield file1.main(value='word!', *args, **kwargs)
""")

        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/file2'))
        self.assertTrue('original template word!' in result, result)

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(value, *args, **kwargs):
    return "changed template %s" % value
""")

        reactor.step()
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/file2'))
        self.assertTrue('changed template word!' in result, result)

    def XtestReloadEverythingOnAnyChangeWhenWatching(self):
        def howOften(name):
            _anIdState = [0]
            def anId():
                _anIdState[0] += 1
                return '{0}:{1}'.format(name, _anIdState[0])
            return anId

        fp_util = join(self.tempdir, 'util.sf')
        util_contents = '''
reloaded = util_reloaded_id()

def f():
    return reloaded
'''
        with open(fp_util, 'w') as f:
            f.write(util_contents)

        fp_orphan = join(self.tempdir, 'orphan.sf')
        with open(fp_orphan, 'w') as f:
            f.write('''
reloaded = orphan_reloaded_id()

def orphan():
    return reloaded
''')

        fp_using_util = join(self.tempdir, 'using-util.sf')
        with open(fp_using_util, 'w') as f:
            f.write('''
import util

reloaded = using_util_reloaded_id()

def using():
    return reloaded + ' - ' + util.f()
''')
        def Xtest():
            additionalGlobals = {
                'util_reloaded_id': howOften("util-reloaded"),
                'using_util_reloaded_id': howOften("using-util-reloaded"),
                'orphan_reloaded_id': howOften("orphan-reloaded"),
            }
            d = DynamicHtml([self.tempdir], reactor=reactor(), additionalGlobals=additionalGlobals)

            # Allow cleanup of directoryWatcherReadFD (whitebox)
            _reactorFdsKeys = list(reactor()._fds.keys())
            self.assertEqual(1, len(_reactorFdsKeys))
            directoryWatcherReadFD = _reactorFdsKeys[0]

            yield zleep(0.01)   # Allow DirectoryWatcher some reactor time

            # Initialized once
            util, orphan, using_util = d.getModule('util'), d.getModule('orphan'), d.getModule('using-util')
            self.assertEqual(
                ['util-reloaded:1',
                 'orphan-reloaded:1',
                 'using-util-reloaded:1'],
                [util.reloaded, orphan.reloaded, using_util.reloaded])
            self.assertEqual('using-util-reloaded:1 - util-reloaded:1', using_util.using())

            # Touch & **all** reloaded
            with open(fp_util, 'w') as f:
                f.write(util_contents)
            yield zleep(0.02)   # Allow DirectoryWatcher some reactor time

            util, orphan, using_util = d.getModule('util'), d.getModule('orphan'), d.getModule('using-util')
            self.assertEqual(
                ['util-reloaded:2',
                 'orphan-reloaded:2',
                 'using-util-reloaded:2'],
                [util.reloaded, orphan.reloaded, using_util.reloaded])
            self.assertEqual('using-util-reloaded:2 - util-reloaded:2', using_util.using())

            # Remove file - nothing happens
            remove(fp_orphan)
            yield zleep(0.02)   # Allow DirectoryWatcher some reactor time

            util, orphan, using_util = d.getModule('util'), d.getModule('orphan'), d.getModule('using-util')
            self.assertNotEqual(None, orphan)
            self.assertEqual(
                ['util-reloaded:2',
                 'orphan-reloaded:2',
                 'using-util-reloaded:2'],
                [util.reloaded, orphan.reloaded, using_util.reloaded])

            # Modify util - reload **and** remove of deleted happens
            with open(fp_util, 'w') as f:
                f.write(util_contents)
            yield zleep(0.02)   # Allow DirectoryWatcher some reactor time

            util, orphan, using_util = d.getModule('util'), d.getModule('orphan'), d.getModule('using-util')
            self.assertEqual(None, orphan)
            self.assertEqual(
                ['util-reloaded:3',
                 'using-util-reloaded:3'],
                [util.reloaded, using_util.reloaded])
            self.assertEqual('using-util-reloaded:3 - util-reloaded:3', using_util.using())

            # cleanup
            reactor().removeReader(sok=directoryWatcherReadFD)

        asProcess(test())

    def XtestBuiltins(self):
        reactor = Reactor()

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(headers={}, *args, **kwargs):
    yield str(True)
    yield str(False)
""")

        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\nTrueFalse', ''.join(result))

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(headers={}, *args, **kwargs):
    yield int('1')
    yield 2
""")

        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n12', ''.join(x for x in result))

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(headers={}, *args, **kwargs):
    yield escapeHtml('&<>"')
""")

        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n&amp;&lt;&gt;&quot;', ''.join(result))

        open(self.tempdir + '/file1.sf', 'w').write("""
def main(headers={}, *args, **kwargs):
    yield str(zip([1,2,3],['one','two','three']))
""")

        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        self.assertEqual('''HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n[(1, 'one'), (2, 'two'), (3, 'three')]''', ''.join(result))


    def XtestImportForeignModules(self):
        reactor = Reactor()

        open(self.tempdir + '/file1.sf', 'w').write("""
import sys

def main(headers={}, *args, **kwargs):
    yield str(sys)
""")

        d = DynamicHtml([self.tempdir], reactor=reactor, allowedModules=['sys'])
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'})
        resultText = ''.join(result)
        self.assertTrue("<module 'sys' (built-in)>" in resultText, resultText)

        open(self.tempdir + '/file1.sf', 'w').write("""
import sys

def main(headers={}, *args, **kwargs):
    yield sys.__doc__
""")

        reactor.step()
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/file1', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue('This module provides access to some objects' in result, result)

    def XtestPipelining(self):
        open(self.tempdir + '/pipe1.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield 'one'
    for data in pipe:
        yield data
    yield 'four'
""")
        open(self.tempdir + '/pipe2.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield 'two'
    yield 'three'
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/pipe1/pipe2')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('onetwothreefour', message)

    def XtestLongPipeLine(self):
        filenames = []
        for i in range(10):
            filename = 'pipe%s' % i
            filenames.append(filename)
            open(self.tempdir + '/' + filename + '.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield str(%s)
    for data in pipe:
        yield data
""" % i)

        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/' + '/'.join(filenames))
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('0123456789', message)


    def XtestPipelineError(self):
        open(self.tempdir + '/pipe1.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield 'one'
    for data in pipe:
        yield data
    yield 'four'
""")
        open(self.tempdir + '/pipe2.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield 'two'
    1/0
    yield 'three'

""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/pipe1/pipe2')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertTrue('integer division or modulo by zero' in message)

    def XtestYieldingEmptyPipe(self):
        open(self.tempdir + '/page.sf', 'w').write("""
def main(pipe=None, *args, **kwargs):
    yield "start"
    for data in pipe:
        yield data
    yield 'end'

""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/page')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('startend', message)

    def XtestPathTailDoesNotExist(self):
        open(self.tempdir + '/page.sf', 'w').write("""
def main(**kwargs):
    yield "nopipe"
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = d.handleRequest(scheme='http', netloc='host.nl', path='/page/doesnotexist')
        headers, message = ''.join(result).split('\r\n\r\n')
        self.assertEqual('nopipe', message)

    def XtestIndexPage(self):
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = asString(d.handleRequest(path='/'))
        headers, message = result.split('\r\n\r\n')
        self.assertEqual('File "" does not exist.', message)

        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor, indexPage='/page')
        result = asString(d.handleRequest(path='/'))
        headers, message = result.split('\r\n\r\n')
        self.assertEqual('HTTP/1.0 302 Found\r\nLocation: /page', headers)

        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor, indexPage='/page')
        result = asString(d.handleRequest(path='/', arguments={'a':['1']}))
        headers, message = result.split('\r\n\r\n')
        self.assertEqual('HTTP/1.0 302 Found\r\nLocation: /page?a=1', headers)

    def XtestSFExtension(self):
        open(self.tempdir + '/page1.sf', 'w').write("""
def main(*args, **kwargs):
    yield "page1"
""")
        open(self.tempdir + '/page2.sf', 'w').write("""
import page1
def main(*args, **kwargs):
    yield page1.main()
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/page2'))
        self.assertTrue('page1' in result, result)

    def XtestIgnoreNonSFExtensions(self):
        open(self.tempdir + '/page.otherextension.sf', 'w').write("""
def main(*args, **kwargs):
    yield "should not happen"
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = asString(d.handleRequest(scheme='http', netloc='host.nl', path='/page'))
        self.assertTrue('should not happen' not in result, result)

    def XtestHandlePOSTRequest(self):
        open(self.tempdir + '/page.sf', 'w').write(r"""
def main(Headers={}, Body=None, Method=None, *args, **kwargs):
    yield 'Content-Type: %s\n' % Headers.get('Content-Type')
    yield 'Body: %s\n' % Body
    yield 'Method: %s\n' % Method
"""
        )
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/page', arguments={}, RequestURI='http://host.nl/page', Method='POST', Body='label=value&otherlabel=value', Headers={'Content-Type':'application/x-www-form-urlencoded'}))

        self.assertTrue('Content-Type: application/x-www-form-urlencoded\nBody: label=value&otherlabel=value\nMethod: POST\n' in result, result)

    def XtestRedirect(self):
        open(self.tempdir + '/page.sf', 'w').write(r"""
def main(*args, **kwargs):
    yield http.redirect('/here')
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/page'))
        self.assertEqual('HTTP/1.0 302 Found\r\nLocation: /here\r\n\r\n', result)

    def XtestRedirectWithAdditionalHeaders(self):
        open(self.tempdir + '/page.sf', 'w').write(r"""
def main(*args, **kwargs):
    yield http.redirect('/here', additionalHeaders={'Pragma': 'no-cache', 'Expires': '0'})
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result = ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/page'))
        self.assertEqual('HTTP/1.0 302 Found\r\nExpires: 0\r\nLocation: /here\r\nPragma: no-cache\r\n\r\n', result)

    def XtestKeywordArgumentsArePassed(self):
        open(self.tempdir+'/afile.sf', 'w').write('def main(pipe, tag, *args, **kwargs): \n  yield str(kwargs)')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        result = ''.join(d.handleRequest(path='/afile', netloc='localhost', key='value', key2='value2'))
        header, body = result.split('\r\n\r\n')
        arguments = eval(body)
        self.assertEqual({
            'Headers':{},
            'arguments':{},
            'path':'/afile',
            'netloc':'localhost',
            'key':'value',
            'key2':'value2',
            'scheme':'',
            'query': ''}, eval(body))

    def createTwoPaths(self):
        path1 = join(self.tempdir, '1')
        path2 = join(self.tempdir, '2')
        makedirs(path1)
        makedirs(path2)
        return path1, path2

    def XtestMoreDirectories(self):
        path1, path2 = self.createTwoPaths()
        open(join(path2, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "page"')
        d = DynamicHtml([path1, path2], reactor=CallTrace('Reactor'))
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('page', body)

    def XtestImportFromFirstPath(self):
        path1, path2 = self.createTwoPaths()
        open(join(path2, 'page.sf'), 'w').write('import one\ndef main(*args,**kwargs):\n yield one.main(*args,**kwargs)')
        open(join(path1, 'one.sf'), 'w').write('def main(*args,**kwargs):\n yield "one"')
        d = DynamicHtml([path1, path2], reactor=CallTrace('Reactor'))
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)

    def XtestLoadTemplate(self):
        path1, path2 = self.createTwoPaths()
        open(join(path2, 'page.sf'), 'w').write("""
def main(*args,**kwargs):
  one = importTemplate("one")
  yield one.main(*args,**kwargs)
""")
        open(join(path1, 'one.sf'), 'w').write("""
def main(*args,**kwargs):
  yield "one"
""")
        d = DynamicHtml([path1, path2], reactor=CallTrace('Reactor'))
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)

    def XtestImportFromSecondPath(self):
        reactor = Reactor()
        path1, path2 = self.createTwoPaths()
        open(join(path2, 'one.sf'), 'w').write('def main(*args,**kwargs):\n yield "one"')
        open(join(path1, 'page.sf'), 'w').write('import one\ndef main(*args,**kwargs):\n yield one.main(*args,**kwargs)')
        d = DynamicHtml([path1, path2], reactor=reactor)
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)
        open(join(path2, 'one.sf'), 'w').write('def main(*args,**kwargs):\n yield "two"')
        reactor.step()
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('two', body)

    def XtestFirstDirectoryHasTheRightFile(self):
        path1, path2 = self.createTwoPaths()
        open(join(path1, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "one"')
        open(join(path2, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "two"')
        d = DynamicHtml([path1, path2], reactor=CallTrace('Reactor'))
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)

    def XtestFirstDirectoryHasTheRightFileButSecondFileChanges(self):
        reactor = Reactor()
        path1, path2 = self.createTwoPaths()
        open(join(path1, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "one"')
        open(join(path2, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "two"')
        d = DynamicHtml([path1, path2], reactor=reactor)
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)

        open(join(path2, 'page.sf'), 'w').write('def main(*args,**kwargs):\n yield "three"')
        reactor.step()
        result = ''.join(d.handleRequest(path='/page'))
        header, body = result.split('\r\n\r\n')
        self.assertEqual('one', body)

    def XtestOldApiRaisesWarning(self):
        try:
            d = DynamicHtml("aDirectory", reactor=CallTrace('Reactor'))
            self.fail()
        except TypeError as te:
            self.assertEqual("Usage: DynamicHtml([aDirectory, ...], ....)", str(te))

    def XtestAdditionalGlobals(self):
        open(self.tempdir+'/afile.sf', 'w').write('def main(*args, **kwargs): \n  yield something')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'), additionalGlobals={'something':'YES'})
        head,body = ''.join(d.handleRequest(path='/afile')).split('\r\n\r\n')
        self.assertEqual('YES', body)

    def XtestCanCreateClassesInTemplate(self):
        open(self.tempdir+'/afile.sf', 'w').write('''\
def main(*args, **kwargs):
    class A(object):
        def __init__(self):
            self.b = 'result'

    yield A().b''')
        d = DynamicHtml([self.tempdir], reactor=CallTrace('Reactor'))
        head, body = ''.join(d.handleRequest(path='/afile')).split('\r\n\r\n')
        self.assertEqual('result', body)

    def XtestChangingFileBeforeRetrievingFirstPage(self):
        reactor = Reactor()
        open(join(self.tempdir, 'one.sf'), 'w').write('def main(*args,**kwargs):\n yield "one"')
        open(join(self.tempdir, 'two.sf'), 'w').write('def main(*args,**kwargs):\n yield "two"')
        d = DynamicHtml([self.tempdir], reactor=reactor)
        open(join(self.tempdir, 'one.sf'), 'w').write('def main(*args,**kwargs):\n yield "one++"')
        reactor.step()
        header, body = ''.join(d.handleRequest(path='/two')).split('\r\n'*2)
        self.assertEqual('two', body)

    def XtestPassCallable(self):
        reactor = Reactor()
        tmplatename = join(self.tempdir, 'withcallable.sf')
        d = DynamicHtml([self.tempdir], reactor=reactor)
        open(tmplatename, 'w').write(
                "def main(*args, **kwargs):\n"
                "    def f():\n"
                "        pass\n"
                "    yield 'HTTP/1.0 200 OK\\r\\n\\r\\n'\n"
                "    yield f\n"
                "    yield 'text2'\n")
        reactor.step()
        r = list(d.handleRequest(path='/withcallable'))
        self.assertEqual("HTTP/1.0 200 OK\r\n\r\n", r[0])
        self.assertTrue(callable(r[1]), r[1])
        self.assertEqual("text2", r[2])

    def XtestPassYield(self):
        reactor = Reactor()
        tmplatename = join(self.tempdir, 'withyield.sf')
        d = DynamicHtml([self.tempdir], reactor=reactor)
        open(tmplatename, 'w').write(
                "def main(*args, **kwargs):\n"
                "    yield 'HTTP/1.0 200 OK\\r\\n\\r\\n'\n"
                "    yield Yield\n"
                "    yield 'text2'\n")
        reactor.step()
        r = list(d.handleRequest(path='/withyield'))
        self.assertEqual("HTTP/1.0 200 OK\r\n\r\n", r[0])
        self.assertTrue(Yield is r[1], r[1])
        self.assertEqual("text2", r[2])

    def XtestPassCallableAsFirstThing(self):
        reactor = Reactor()
        tmplatename = join(self.tempdir, 'withcallable.sf')
        d = DynamicHtml([self.tempdir], reactor=reactor)
        open(tmplatename, 'w').write(
                "def main(*args, **kwargs):\n"
                "    def f():\n"
                "        pass\n"
                "    yield f\n"
                "    yield f\n"
                "    yield 'this is no status line'\n"
                "    yield f\n"
                "    yield 'text2'\n")
        reactor.step()
        r = list(d.handleRequest(path='/withcallable'))
        self.assertTrue(callable(r[0]))
        self.assertTrue(callable(r[1]))
        self.assertEqual("HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n", r[2])
        self.assertEqual("this is no status line", r[3])
        self.assertTrue(callable(r[4]))
        self.assertEqual("text2", r[5])

    def XtestSetAttributeOnTemplateObjectNotAllowed(self):
        open(self.tempdir + '/two.sf', 'w').write(r"""

def main(*args, **kwargs):
    yield "Hoi"
""")
        open(self.tempdir + '/one.sf', 'w').write(r"""

import two
two.three = 3

def main(*args, **kwargs):
    yield "Hoi"
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        result =  ''.join(d.handleRequest(scheme='http', netloc='host.nl', path='/one', query='?query=something', fragments='#fragments', arguments={'query': 'something'}))
        self.assertTrue('AttributeError' in result, result)

    def XtestShouldExposeLoadedModulesForTestingPurposes(self):
        open(self.tempdir + '/one.sf', 'w').write(r"""
attr = 'attr'
def sync():
    return 'aye'
def asyncReturn():
    raise StopIteration('aye')
    yield
def observableDownward():
    yield observable.all.something('arg', kw='kw')
def main(*args, **kwargs):
    yield "Hoi"
""")
        open(self.tempdir + '/two.sf', 'w').write(r"""

import one

def parameterized(arg, *args, **kwargs):
    return arg, args, kwargs

def main(*args, **kwargs):
    yield one.observableDownward()
""")
        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor)
        t1 = CallTrace('t1')
        t2 = CallTrace('t2')
        d.addObserver(t1)
        d.addObserver(t2)
        one = d.getModule(name='one')
        two = d.getModule('two')

        self.assertEqual(None, d.getModule('does-not-exist'))

        self.assertEqual('attr', one.attr)
        self.assertEqual('aye', one.sync())
        try:
            g = compose(one.asyncReturn())
            next(g)
        except StopIteration as e:
            self.assertEqual(('aye',), e.args)
        else:
            self.fail()

        self.assertEqual([], t1.calledMethodNames())
        self.assertEqual([], t2.calledMethodNames())
        list(compose(one.observableDownward()))
        self.assertEqual(['something'], t1.calledMethodNames())
        self.assertEqual(['something'], t2.calledMethodNames())
        self.assertEqual(('arg',), t1.calledMethods[0].args)
        self.assertEqual({'kw': 'kw'}, t1.calledMethods[0].kwargs)

        self.assertEqual(('one', ('two',), {'th': 'ree'}), two.parameterized('one', 'two', th='ree'))

        t1.calledMethods.reset()
        t2.calledMethods.reset()
        list(compose(two.main()))
        self.assertEqual(['something'], t1.calledMethodNames())
        self.assertEqual(['something'], t2.calledMethodNames())
        self.assertEqual(('arg',), t2.calledMethods[0].args)
        self.assertEqual({'kw': 'kw'}, t2.calledMethods[0].kwargs)

    def XtestErrorHandlingCustomHook(self):
        tracebacks = []
        def error_handling_hook(traceback, *args, **kwargs):
            tracebacks.append((traceback, args, kwargs))

        reactor = Reactor()
        d = DynamicHtml([self.tempdir], reactor=reactor, errorHandlingHook=error_handling_hook)
        with open(join(self.tempdir, "page_with_error.sf"), 'w') as fp:
            fp.write("""
def main(*args, **kwargs):
    yield 1/0""")
        reactor.step()
        r = list(d.handleRequest(path='/page_with_error', some_kwargs="something"))
        self.assertEqual(1, len(tracebacks))
        t, a, k = tracebacks[0]
        self.assertEqual(('/page_with_error',), a)
        self.assertTrue('tag' in k, k)
        self.assertEqual("something", k['some_kwargs'])
