Deadscript
==========

My experiments with compilers.


How it works
------------

  1. Indent parsing

     Parses source into tree with scopes defined
     by indentation (python-like).

  1. Grammar parsing

     Build abstract syntax tree over the previous tree.
     It's a ``top-down'' parser. No any semantic analysis yet,
     the tree is 1 to 1 match the original program.

  1. Semantic analysis

     Find functions, loops, branches and other main building
     blocks.

  1. Type inference

     The compiler tries guess the types of variables.

  1. Sanity check

     Checks that, e.g., main() has correct arguments and so on.

  1. Code generation

     AST traversing and generation of ``llvm intermediate representation''.

  1. Compilation
     Invoce llvm to build the program.



Design Goals
------------

What do computer programs? They provide a sequency of transformatins
to you data in way to get the meaningful output. The goal of a
computer language is to support writing such transformations


1. Be safe, compact and friendly
1. Static typing
1. ML-like syntax (inspired by LiveScript)
1. Public/Protected/Private attributes of the classes
1. Built-in regexp support
1. Built-in shell commands invocation
1. Function overloading
1. Custom operators
1. Garbage collection
1. Will alarm on useless statements (like forget to call function)
1. Substitute vars in strings: "Hello, {username}!"
1. UTF8 strings
1. Assigments in if-clause (but it should evaluate to bool <- safety measure)
1. Support comments:
    shell-style # blah
    cpp // here is the comment
    C /* Hi! */
1. All programs can be opened as libraries
1. No header files needed, everything is in elf (possibly in compressed format).
1. Keep it simple (to learn, to read, to extend)
1. Error-resistant coding
1. Minimize number of keywords and namespace pollution


FILES
-----

1. dead.py     -- just launcher of all stuff
1. peg.py      -- PEG parser that allows to define grammar in a bnf-like way
1. pratt.py    -- Pratt parser, used to parse expressions
1. tokenizer.py -- split input into tokens, uses PEG
1. ast.py      -- abstract syntax tree and rewrite tools
1. codegen.py  -- a small helper script to write correctly-indented code


Other
-----

The normal assumtion is that memory allocation will never fail.
This is because most of programs anyway don't know how to deal with these errors.
If a program must not silently fail there is a method to provisionally allocate
required amount of memory.


Why static:
  Just today I found typing bugs in pypeg and modgrammar. I see typing
  problems almost every day in many programs and libraries!

Why methods instead of functions:
  Python's namespaces highly polluted with abs, len, sum, all, vars,
  min/max, next, list, id, to, dict, etc...

Terminology
-----------

  1. Parser (definitions are from https://siod.svn.codeplex.com/svn/winsiod/pratt.scm, A simple Pratt-Parser for SIOD: 2-FEB-90, George Carrette, GJC@PARADIGM.COM):
    1. NUD -- NUll left Denotation (op has nothing to its left (prefix))
    1. LED -- LEft Denotation      (op has something to left (postfix or infix))
    1. LBP -- Left Binding Power  (the stickiness to the left)
    1. RBP -- Right Binding Power (the stickiness to the right)


Other project names
-------------------

1. Brainduck (busy)
1. Concrete mixer


References
----------

### Simple top-level parsing

1. http://en.wikipedia.org/wiki/Parsing_expression_grammar

### Expression parsing (with precedence)

1. http://journal.stuffwithstuff.com/2011/03/19/pratt-parsers-expression-parsing-made-easy/
1. http://effbot.org/zone/simple-top-down-parsing.htm

Useful Links
============

1. http://roscidus.com/blog/blog/2013/06/20/replacing-python-round-2/#syntax
1. http://en.wikipedia.org/wiki/Linear_type_system


Types
=====

Str
Int
Bool
Tuple
Array