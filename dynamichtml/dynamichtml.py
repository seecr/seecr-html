from glob import glob
from os.path import join, isfile, isdir, dirname, basename, abspath
from os import walk as dirwalk
from sys import exc_info
from traceback import format_exc
from cgi import parse_qs
from urlparse import urlsplit

from pyinotify import EventsCodes

from cgi import escape as escapeHtml
from xml.sax.saxutils import escape as escapeXml
from amara.binderytools import bind_stream
from time import time
from urllib import urlencode
from math import ceil

from meresco.framework import Observable, decorate, compose
from cq2utils.wrappers import wrapp
from cq2utils import DirectoryWatcher

class Module:
    def __init__(self, moduleGlobals):
        self.__dict__ = moduleGlobals
class DynamicHtmlException(Exception):
    pass

class DynamicHtml(Observable):

    def __init__(self, directory, reactor=None, prefix = '', allowedModules=[], indexPage='', verbose=False):
        Observable.__init__(self)
        self._globals = None
        self._verbose = verbose
        self._directory = directory
        self._prefix = prefix
        self._indexPage = indexPage
        self._allowedModules = allowedModules
        self._modules = {}
        self._loadModuleFromPaths()
        self._initMonitoringForFileChanges(reactor)

    def _loadModuleFromPaths(self):
        for path in glob(self._directory + '/*.sf'):
            self.loadModuleFromPath(path)

    def _initMonitoringForFileChanges(self, reactor):
        directoryWatcher = DirectoryWatcher(
            self._directory,
            self._notifyHandler,
            CreateFile=True, ModifyFile=True, MoveInFile=True)
        reactor.addReader(directoryWatcher, directoryWatcher)

    def _notifyHandler(self, event):
        self.loadModuleFromPath(join(self._directory, event.name))

    def loadModuleFromPath(self, path):
        moduleName = basename(path)[:-len('.sf')]
        moduleGlobals = self.createGlobals()
        createdLocals = {}
        try:
            execfile(path, moduleGlobals, createdLocals)
        except Exception, e:
            s = escapeHtml(format_exc())
            createdLocals['main'] = lambda *args, **kwargs: (x for x in ['<pre>', s, '</pre>'])
        moduleGlobals.update(createdLocals)
        newModule = Module(moduleGlobals)
        self._replaceModuleReferencesInOtherModules(moduleName, newModule)
        self._modules[moduleName] = newModule

    def _replaceModuleReferencesInOtherModules(self, moduleName, newModule):
        for module in self._modules.values():
            if moduleName in module.__dict__:
                module.__dict__[moduleName] = newModule

    def __import__(self, moduleName, globals=None, locals=None, fromlist=None):
        if moduleName in self._allowedModules:
             moduleObject = __import__(moduleName)
        else:
            if not moduleName in self._modules:
                filename = moduleName.replace('.', '/') + '.sf'
                self.loadModuleFromPath(join(self._directory, filename))
            moduleObject = self._modules[moduleName]
        return moduleObject

    def _createMainGenerator(self, path, headers, arguments, **kwargs):
        i = path.find('/')
        if i < 1:
            name = path
            nextGenerator =  (i for i in [])
        else:
            name = path[:i]
            nextGenerator = self._createMainGenerator(path[i+1:], headers, arguments, **kwargs)
        if not name in self._modules:
            raise DynamicHtmlException('File %s does not exist.' % path)
        main = self._modules[name].main
        return main(headers=headers, arguments=arguments, pipe=nextGenerator, **kwargs)

    def handleRequest(self, RequestURI=None, Headers=None, *args, **kwargs):
        scheme, netloc, path, query, fragments = urlsplit(RequestURI)
        arguments = parse_qs(query)
        return self.handleHttpRequest(scheme, netloc, path, query, fragments, arguments, headers=Headers, **kwargs)

    def handleHttpRequest(self, scheme, netloc, path, query='', fragments='', arguments={}, headers={}, **kwargs):
        path = path[len(self._prefix):]
        if path == '/' and self._indexPage:
            path = self._indexPage
        try:
            generators = self._createMainGenerator(path[1:], headers, arguments, **kwargs)
            contentType = 'text/html'
            if path.endswith('.xml'):
                contentType = 'text/xml'
            yield 'HTTP/1.0 200 Ok\r\nContent-Type: %s; charset=utf-8\r\n\r\n' % contentType
            for line in compose(generators):
                yield line
        except DynamicHtmlException, e:
            yield 'HTTP/1.0 404 File not found\r\nContent-Type: text/html; charset=utf-8\r\n\r\n' + str(e)
        except Exception:
            s = format_exc() #cannot be inlined
            yield "<pre>"
            yield escapeHtml(s)
            yield "</pre>"

    def createGlobals(self):
        return {
            '__builtins__': {
                '__import__': self.__import__,
                # standard Python stuff
                'str': str,
                'int': int,
                'float': float,
                'len': len,
                'False': False,
                'True': True,
                'min': min,
                'max': max,
                'ceil': ceil,
                'unicode': unicode,
                'range': range,
                'enumerate': enumerate,
                'map': map,
                'sorted': sorted,
                'cmp': cmp,
                'dict': dict,
                'set': set,

                # observable stuff
                'any': self.any,
                'all': self.all,
                'do': self.do,

                # commonly used/needed methods
                'escapeHtml': escapeHtml,
                'escapeXml': escapeXml,
                'bind_stream': lambda x:wrapp(bind_stream(x)),
                'time': time,
                'urlencode': lambda x: urlencode(x, doseq=True),
                'decorate': decorate,
                'dirwalk': dirwalk,
                'dirname': dirname,
                'basename': basename,
                'parse_qs': parse_qs
            }
        }
