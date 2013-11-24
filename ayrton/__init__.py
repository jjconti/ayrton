# -*- coding: utf-8 -*-

# (c) 2013 Marcos Dione <mdione@grulic.org.ar>

# This file is part of ayrton.
#
# ayrton is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ayrton is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ayrton.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import importlib
import builtins
import pickle
import ast
from ast import fix_missing_locations, alias, ImportFrom
import traceback

# things that have to be defined before importing ayton.execute :(
# singleton
runner= None

from ayrton.castt import CrazyASTTransformer
from ayrton.execute import o, Command, Capture, CommandFailed

__version__= '0.3'

class Environment (object):
    def __init__ (self, globals=None, locals=None, **kwargs):
        super ().__init__ ()

        if globals is None:
            self.globals= {}
        else:
            self.globals= globals

        if locals is None:
            self.locals= {}
        else:
            self.locals= locals

        self.python_builtins= builtins.__dict__.copy ()
        self.ayrton_builtins= {}
        polute (self.ayrton_builtins)
        self.os_environ= os.environ.copy ()

        # now polute the locals with kwargs
        for k, v in kwargs.items ():
            # BUG: this sucks
            if k=='argv':
                self.ayrton_builtins['argv']= v
            else:
                self.locals[k]= v

    def __getitem__ (self, k):
        strikes= 0
        for d in (self.locals, self.globals, self.os_environ,
                  self.python_builtins, self.ayrton_builtins):
            try:
                ans= d[k]
                # found, don't search anymore (just in case you could find it
                # somewhere else)
                break
            except KeyError:
                strikes+= 1

        if strikes==5:
            # the name was not found in any of the dicts
            # create a command for it
            # ans= Command (k)
            # print (k)
            raise KeyError (k)

        return ans

    def __setitem__ (self, k, v):
        self.locals[k]= v

    def __delitem__ (self, k):
        del self.locals[k]

    def __iter__ (self):
        return self.locals.__iter__ ()

    def __str__ (self):
        return str ([ self.globals, self.locals, self.os_environ ])

class Ayrton (object):
    def __init__ (self, script=None, file=None, tree=None, globals=None,
                  locals=None, **kwargs):
        if script is None and file is not None:
            # it's a pity that compile() does not accept a file as input
            # so we could avoid reading the whole file
            script= open (file).read ()
        else:
            file= 'arg_to_main'

        self.environ= Environment (globals, locals, **kwargs)


        if tree is None:
            tree= ast.parse (script)
            # ImportFrom(module='bar', names=[alias(name='baz', asname=None)], level=0)
            node= ImportFrom (module='ayrton.execute',
                              names=[alias (name='Command', asname=None)],
                              level=0)
            node.lineno= 0
            node.col_offset= 0
            ast.fix_missing_locations (node)
            tree.body.insert (0, node)
            tree= CrazyASTTransformer(self.environ).visit (tree)

        self.options= {}
        # print (ast.dump (tree))
        self.source= compile (tree, file, 'exec')

    def run (self):
        exec (self.source, self.environ.globals, self.environ)

def polute (d):
    # these functions will be loaded from each module and put in the globals
    # tuples (src, dst) renames function src to dst
    builtins= {
        'os': [ ('getcwd', 'pwd'), 'uname', 'listdir', ],
        'os.path': [ 'abspath', 'basename', 'commonprefix', 'dirname',  ],
        'time': [ 'sleep', ],
        'sys': [ 'argv', 'exit' ],

        'ayrton.file_test': [ '_a', '_b', '_c', '_d', '_e', '_f', '_g', '_h',
                              '_k', '_p', '_r', '_s', '_u', '_w', '_x', '_L',
                              '_N', '_S', '_nt', '_ot' ],
        'ayrton.expansion': [ 'bash', ],
        'ayrton.functions': [ 'cd', 'export', 'option', 'remote', 'run',
                               'shift', 'source', 'unset', ],
        'ayrton.execute': [ 'o', 'Capture', 'CommandFailed', 'CommandNotFound', ],
        }

    for module, functions in builtins.items ():
        m= importlib.import_module (module)
        for function in functions:
            if type (function)==tuple:
                src, dst= function
            else:
                src= function
                dst= function

            d[dst]= getattr (m, src)

    # now the IO files
    for std in ('stdin', 'stdout', 'stderr'):
        d[std]= getattr (sys, std).buffer

def run (tree, globals, locals):
    global runner
    runner= Ayrton (tree=tree, globals=globals, locals=locals)
    runner.run ()

def main (script=None, file=None, **kwargs):
    global runner
    runner= Ayrton (script=script, file=file, **kwargs)
    runner.run ()
