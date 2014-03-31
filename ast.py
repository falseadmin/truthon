#!/usr/bin/env python3

from pratt import prefix, infix, infix_r, postfix, brackets, \
  subscript, nullary, ifelse, symap, parse as pratt_parse, expr
from log import Log
log = Log('ast')

rewrite_funcs = []
def rewrites(f):
  rewrite_funcs.append(f)
  return f


#############
# TEMPLATES #
#############

class Node(list):
  """
  Base class for most syntax elements. It is a subclass of
  list to support iteration over its elements. It also
  supports access to the elements through attributes. Names
  of attributes to be specified in class.fields.
  """
  fields = []

  def __init__(self, *args):
    if self.fields and len(args) != len(self.fields):
      raise Exception("Number of arguments mismatch defined fields")
    super().__init__(args)

  def __getattr__(self, name):
    if not self.fields or name not in self.fields:
      raise AttributeError("Unknown attribute \"%s\" for %s (%s)" % (name, type(self), self.fields))
    idx = self.fields.index(name)
    return self[idx]

  def __setattr__(self, name, value):
    if name in dir(self.__class__):
      super().__setattr__(name, value)
    elif name in self.fields:
      idx = self.fields.index(name)
      self[idx] = value
    else:
      raise AttributeError("Unknown attribute \"%s\" for %s (%s)" % (name, type(self), self.fields))


  def __dir__(self):
    if self.fields:
      return self.fields
    else:
      return super().__dir__()

  def __repr__(self):
    cls = self.__class__.__name__
    if self.fields:
      args = ", ".join("%s=%s"%(name, getattr(self,name)) for name in self.fields)
    else:
      args = ", ".join(map(str, self))
    return "%s(%s)" % (cls, args)


class ListNode(Node):
  """ Represents a node that is just a list of something. """
  fields = None

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s(%s)" % (cls, ", ".join(map(str,self)))


class Leaf:
  """ Base class for AST elements that do not support
      iteration over them.
  """
  lbp = 0
  def __init__(self, value=None):
    assert not hasattr(self, 'fields'), \
      "Leaf subclass cannot have fields attribute (it's not a Node)"
    self.value = value
    super().__init__()

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s(%s)" % (cls, self.value)

  def nud(self):
    return self


class Unary(Node):
  """ Base class for unary operators. """
  fields = ['arg']


class Binary(Node):
  """ Base class for binary operators. """
  fields = ['left', 'right']


class Expr(Node):
  """ Base class for expressions. """
  def __repr__(self):
    return "Expr(%s)" % ", ".join(str(s) for s in self)


class Block(Node):
  """ A block of one or more expressions. """
  def nud(self):
    return self



##############
# Data Types #
##############

class Comment(Leaf): pass
class Str(Leaf):  pass
class ShellCmd(Leaf):  pass
class RegEx(Leaf):  pass
class Int(Leaf):  pass
class Id(Leaf):  pass


###########
# SPECIAL #
###########

@prefix('p ', 0)
class Print(Unary): pass

@prefix('assert', 0)
class Assert(Unary): pass

@nullary('_')
class AlwaysTrue(Leaf): pass

@nullary('return')
class Return(Leaf):  pass


#########
# UNARY #
#########

@prefix('-', 100)
class Minus(Unary): pass

@prefix('+', 100)
class Plus(Unary): pass

@prefix('match', 1)
class Match(Node): pass

@prefix('->', 1)
class Lambda0(Unary): pass

@postfix('!', 3)
class Call0(Unary): pass


##########
# BINARY #
##########

@infix_r(' . ', 11)  #TODO: wrong priority
class ComposeR(Binary): pass

@infix('$', 11)      #TODO: wrong priority
class ComposerL(Binary): pass

@infix('->', 3)
class Lambda(Binary):
  fields = ['args', 'body']

@infix('=>', 4)
class IfThen(Binary):
  fields = ['iff', 'then']

@infix_r('=', 2)
class Assign(Binary): pass

@infix_r('@', 5)
class Call(Binary): pass

@infix_r('==', 10)
class Eq(Binary): pass

@infix('=~', 10)
class RegMatch(Binary): pass

@infix('<', 10)
class Less(Binary): pass

@infix('>', 10)
class More(Binary): pass

@infix('+', 20)
class Add(Binary): pass

@infix('-', 20)
class Sub(Binary): pass

@infix('*', 30)
class Mul(Binary): pass

@infix_r('^', 40)
class Pow(Binary): pass

@brackets('(',')')
class Parens(ListNode): pass

@brackets('[',']')
class Brackets(Unary): pass

@subscript('[', ']', -1000)
class Subscript(Binary): pass

@infix(',', 5)
class Comma(ListNode):
  """ Parses comma-separated values. It flattens the list,
      e.g., Comma(1, Comma(2, 3)) transformed into Comma(1, 2, 3).
  """
  def __init__(self, left, right):
    values = []
    if isinstance(left, Comma):
      values += left + [right]
    else:
      values = [left, right]
    super().__init__(*values)


class Var(Leaf):
  def __str__(self):
    return "%s(\"%s\")" % (self.__class__.__name__, self.value)

@ifelse(lbp=2)
class IfElse(Node):
  fields = ['iff', 'then', 'otherwise']


#######################
# AST TRANSFORMATIONS #
#######################

def rewrite(tree, f, d=0, **kwargs):
  """ Generic function to transform AST. It reqursively
      applies function to all elements of the tree.
  """
  if d==0: tree = f(tree, d, **kwargs)  # TODO: is this a dirty hack?
  for i,n in enumerate(tree):
      if isinstance(n, Node):
        n = rewrite(n, f, d+1, **kwargs)
      tree[i] = f(n, d, **kwargs)
  return tree


@rewrites
def implicit_calls(expr, depth):
  """ Adds "implicit" calls. E.g., expression "a b c" will
      be parsed as "a(b(c))". This is done by inserting
      explicit call operator.
  """
  if not isinstance(expr, Expr):
    return expr
  if len(expr) < 2:
    return expr
  result = Expr()
  prev, nxt = None, None
  for i,nxt in enumerate(expr):
    if isinstance(prev, Id) and \
    (isinstance(nxt, (Int,Id)) or nxt.sym =='('):
      result.append(symap['@']())
    result.append(nxt)
    prev = nxt
  return result


@rewrites
def precedence(node, depth):
  """ Parses operator precedence """
  if not isinstance(node, Expr):
    return node
  return pratt_parse(node)


@rewrites
def func_args(func, depth):
  """ Parses function arguments. """
  if not isinstance(func, Lambda):
    return func
  assert len(func.args) == 1, \
    "function arguments should be in parentheses and separated by commas"
  args = func.args[0]
  assert isinstance(args, (Comma, Id)), \
    "function argument can be a single ID or some IDs separated by commas"
  if isinstance(args, Id):
    args = [args]
  args = ListNode(*[Id(name.value) for name in args])
  func.args = args
  return func


# @rewrites
def array_csv(array, depth):
  if not isinstance(array, Brackets):
    return array
  if isinstance(array.value, Comma):
    return Brackets(array.value)
  return array


@rewrites
def call_args(call, depth):
  if not isinstance(call, Call):
    return call
  if isinstance(call.right, Comma):
    return Call(call.left, Brackets(call.right))
  return call


def pretty_print(ast, lvl=0):
  """ Prints AST in a more or less readable form """
  prefix = " "*lvl
  for e in ast:
    if isinstance(e, Node):
      print(prefix, type(e).__name__)
      pretty_print(e, lvl+1)
    else:
      print(prefix, e)
  if lvl == 0:
    print()


def parse(ast):
  """ Parses tokens into ast. """
  ast = rewrite(ast, func_args)
  for f in rewrite_funcs:
    log.rewrite("aplying", f.__name__)
    ast = rewrite(ast, f)
  return ast