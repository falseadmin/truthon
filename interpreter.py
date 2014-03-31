from ast import Node, ListNode, Unary, Binary, Leaf, rewrite
from collections import OrderedDict
from frame import Frame
from log import Log
import ast

from subprocess import check_output
import shlex
import re

log = Log("interpreter")
astMap = OrderedDict()


class replaces:
  """ Decorator to substitute nodes in AST. """
  def __init__(self, oldCls):
    self.oldCls = oldCls

  def __call__(self, newCls):
    astMap[self.oldCls] = newCls
    return newCls


def replace_nodes(node, depth):
    for oldCls, newCls in astMap.items():  #may be it should do newCls = asMap(type(node))??
      if isinstance(node, oldCls):
        log.replace("replacing %s (%s)" % (node, type(node)))
        if isinstance(node, Leaf):
          return newCls(node.value)
        return newCls(*node)
    return node

def isclass(smth):
  try:
    issubclass(smth, object)
    return True
  except TypeError:
    return False

##################
# BUILT-IN TYPES #
##################

class Type:
  args = None
  ret  = None

  def __init__(self, args, ret):
    # unpack args
    if isinstance(args, (list, tuple)):
      assert all(isclass(arg) or isinstance(arg, Type) for arg in args), \
        "args should a list of types (got %s)" % args
      args = [arg if not isinstance(arg, Type) else arg.ret for arg in args]
    elif isinstance(args, Type):
      args = args.ret
      assert isclass(args), "args should be a type, (got %s)" % args
    elif args is None:
      pass
    else:
      raise Exception("Unknown type %s"% args)
    # unpack ret
    if isinstance(ret, Type):
      ret = ret.ret
    assert isclass(ret), "ret should be a Type instance or class, (got %s)" % ret
    assert ret is not None, "ret cannot be None"
    # save attributes
    self.args = args
    self.ret  = ret

  def __repr__(self):
    if self.args or " ":
        return "(%s) -> %s" % (self.args, self.ret.__name__)

  def __eq__(self, other):
    return self.args == other.args and \
           self.ret  == other.ret


class Value(Leaf):
  type = None
  """ Base class for values. """

  def infer_type(self, frame):
    self.type = Type(None, self.__class__)
    return self.type

  def eval(self, frame):
    return self

  def Eq(self, other):
    return Bool(self.value == other.value)


@replaces(ast.Int)
class Int(Value):
  def __init__(self, value):
    super().__init__(int(value))

  def to_string(self, frame):
    return str(self.value)

  def to_int(self):
    return self.value

  def Add(self, right):
    return Int(self.value + right.value)

  def Eq(self, other):
    return Bool(self.value == other.value)

  def Less(self, other):
    return Bool(self.value < other.value)

  def More(self, other):
    return Bool(self.value > other.value)

  def Sub(self, other):
    return Int(self.value-other.value)

  def Mul(self, other):
    return Int(self.value*other.value)

  def Pow(self, other):
    return Int(self.value**other.value)


@replaces(ast.Str)
class Str(Value):
  def to_string(self, frame):
    string = self.value
    replace = {r'\n': '\n', r'\t': '\t'}
    varnames = re.findall("\{([a-zA-Z\.]+)\}", string, re.M)
    for name in varnames:
        value = Var(name).eval(frame).to_string(frame)
        string = string.replace("{%s}" % name, value)
    for k,v in replace.items():
      string = string.replace(k, v)
    return string


@replaces(ast.ShellCmd)
class ShellCmd(Str):
  def eval(self, frame):
    cmd = super().eval(frame).to_string(frame)
    raw = check_output(shlex.split(cmd))
    return Str(raw.decode())


@replaces(ast.Brackets)
class Array(ListNode):
  type = None

  def __init__(self, args):
    super().__init__(*args)

  def infer_type(self, frame):
    print("TODO: array does not support type inference yet")
    self.type = Type(None, self.__class__)
    return self.type

  def to_string(self, frame):
    values = [x.eval(frame).to_string(frame) for x in self]
    return '[' + ", ".join(values) + ']'

  def Subscript(self, idx):
    return self[idx.to_int()]

  def eval(self, frame):
    return self


class Bool(Value):
  def __bool__(self):
    return self.value

  def to_string(self, frame):
    return str(self.value)


@replaces(ast.RegEx)
class RegEx(Value):
  def RegMatch(self, string, frame):
    m = re.match(self.value, string.to_string(frame))
    if not m:
      return Bool(False)
    groupdict = m.groupdict()
    if groupdict:
      frame.update(groupdict)
    group = m.group()
    if group:
      return Str(group)
    return Bool(True)


@replaces(ast.Id)
class Var(Leaf):
  type = None

  def infer_type(self, frame, lvalue=None):
    if self.type: return self.type  # short-circuit for recursive calls
    if lvalue:
      ref = lvalue
      frame[self.value] = ref
    else:
      ref = frame[self.value]
    self.type = ref.type
    return self.type

  def Assign(self, value, frame):
    # self.value actually holds the name
    frame[self.value] = value
    return value

  def eval(self, frame):
    try:
      return frame[self.value]
    except KeyError:
      raise Exception("unknown variable \"%s\"" % self.value)

  def __str__(self):
    return str(self.value)


class BinOp(Binary):
  same_type_operands = True
  type = None
  def infer_type(self, frame):
    ltype = self.left.infer_type(frame)
    rtype = self.right.infer_type(frame)
    assert ltype.ret == rtype.ret, \
      "left and right types should have the same type." \
      " Got \"%s\" and \"%s\" respectively." % (ltype, rtype)
    self.type = Type([ltype, rtype], ltype)
    return self.type

  def eval(self, frame):
    opname = self.__class__.__name__
    left = self.left.eval(frame)
    right = self.right.eval(frame)
    if self.same_type_operands and type(left) != type(right):
      raise Exception("%s:" \
      "left and right values should have the same type, " \
      "got\n %s \nand\n %s instead" % (self.__class__, left, right))
    assert hasattr(left, opname), \
      "%s (%s) does not support %s operation" % (left, type(left), opname)
    return getattr(left, opname)(right)


class BoolOp(BinOp):
  def infer_type(self, frame):
    super().infer_type(frame)
    self.type.ret = Bool
    return self.type


@replaces(ast.Lambda0)
class Func0(Node):
  fields = ['body']

  def infer_type(self, frame):
    body_t = self.body.infer_type(frame)
    self.type = Type(None, body_t)
    return self.type

  def Call(self, frame):
    return self.body.eval(frame)

  def eval(self, frame):
    return self


@replaces(ast.Lambda)
class Func(Node):
  fields = ['args', 'body']
  type = None

  def infer_type(self, frame):
    argtypes = []
    for arg in self.args:
      argtypes.append(arg.infer_type(frame))
    body_t = self.body.infer_type(frame)
    self.type = Type(argtypes, body_t)
    return self.type

  def Call(self, frame):
    return self.body.eval(frame)

  def eval(self, frame):
    return self


@replaces(ast.Block)
class Block(Node):
  type = None
  def infer_type(self, frame):
    for expr in self:
      self.type = expr.infer_type(frame)
    return self.type  # last expression in the block is it's type :)


  def eval(self, frame):
    r = None
    for e in self:
      r = e.eval(frame)
    return r


@replaces(ast.Print)
class Print(Unary):
  fields = ['arg']
  type = None
  def infer_type(self, frame):
    self.type = self.arg.infer_type(frame)
    return self.type

  def eval(self, frame):
    r = self.arg.eval(frame)
    print(r.to_string(frame))
    return r


@replaces(ast.Assert)
class Assert(Unary):
  type = None
  def infer_type(self, frame):
    self.type = self.arg.infer_type(frame)
    assert self.type.ret == Bool, \
      "Assert works only with boolean expressions"
    return self.type

  def eval(self, frame):
    r = self.arg.eval(frame)
    if not r:
      raise Exception("Assertion failed on %s" % self.arg)
    return r


@replaces(ast.RegMatch)
class RegMatch(BinOp):
  same_type_operands = False
  def __init__(self, left, right):
    if isinstance(left, (Str, ast.Str)):
      left, right = right, left
    super().__init__(left, right)

  def eval(self, frame):
    opname = self.__class__.__name__
    left = self.left.eval(frame)
    right = self.right.eval(frame)
    assert hasattr(left, opname), \
      "%s (%s) does not support %s operation" % (left, type(left), opname)
    return getattr(left, opname)(right, frame=frame)

@replaces(ast.Assign)
class Assign(BinOp):
  def infer_type(self, frame):
    assert isinstance(self.left, Var), \
      "can only assign to Var"
    right_t = self.right.infer_type(frame)
    self.type = self.left.infer_type(frame, lvalue=self.right)
    return self.type


  def eval(self, frame):
    value = self.right.eval(frame)
    # TODO: lvalue should be a valid ID
    self.left.Assign(value, frame)
    return value


@replaces(ast.Add)
class Add(BinOp): pass

@replaces(ast.Sub)
class Sub(BinOp): pass

@replaces(ast.Mul)
class Mul(BinOp): pass

@replaces(ast.Eq)
class Eq(BoolOp): pass

@replaces(ast.Less)
class Less(BoolOp): pass

@replaces(ast.More)
class More(BoolOp): pass

@replaces(ast.Pow)
class Pow(BinOp): pass

@replaces(ast.Subscript)
class Subscript(BinOp):
  same_type_operands = False


@replaces(ast.Parens)
class Parens(Unary):
  type = None
  def infer_type(self, frame):
    self.type = self.arg.infer_type(frame)
    return self.type

  def eval(self, frame):
    return self.arg.eval(frame)


@replaces(ast.IfThen)
class IfThen(ast.IfThen):
  def infer_type(self, frame):
    iff_t  = self.iff.infer_type(frame)
    print(iff_t)
    assert iff_t.ret == Bool
    self.type = self.then.infer_type(frame)
    return self.type

  def eval(self, frame):
    if self.iff.eval(frame):  # this should return Bool
      return True, self.then.eval(frame)
    return False, 0


@replaces(ast.IfElse)
class IfElse(ast.IfElse):
  type = None
  def infer_type(self, frame):
    assert self.iff.infer_type(frame).ret == Bool
    then_type = self.then.infer_type(frame)
    else_type = self.otherwise.infer_type(frame)
    assert then_type == else_type
    self.type = Type(Bool, else_type)
    return self.type

  def eval(self, frame):
    if self.iff.eval(frame):
      return self.then.eval(frame)
    return self.otherwise.eval(frame)


@replaces(ast.Match)
class Match(Unary):
  def infer_type(self, frame):
    for expr in self.arg:
      expr_t = expr.infer_type(frame)
      # TODO: check that all expressions have the same type
    self.type = expr_t

  def eval(self, frame):
    for expr in self.arg:
      assert isinstance(expr, IfThen), \
        "Child nodes of match operator can" \
        "only be instances of IfThen"
      match, result = expr.eval(frame)
      if match:
        return result


###########
# SPECIAL #
###########

class ReturnException(Exception):  pass

@replaces(ast.Return)
class Return(Leaf):
  def eval(self, frame):
    raise ReturnException


@replaces(ast.AlwaysTrue)
class AlwaysTrue(Value):
  def Bool(self, frame):
    return Bool(True)


@replaces(ast.Comment)
class Comment(Value):
  def eval(self, frame):
    pass


########
# CALL #
########

@replaces(ast.Call0)
class Call0(Unary):
  def infer_type(self, frame):
    self.type = self.arg.infer_type(frame)
    return self.type

  def eval(self, frame):
    with frame as newframe:
      func = self.arg.eval(newframe)
      return func.Call(newframe)


@replaces(ast.Call)
class Call(Binary):
  fields = ['func', 'args']
  def eval(self, frame):
    with frame as newframe:
      func = self.func.eval(frame)
      args = self.args.eval(frame)
      if isinstance(args, (Value, Var)):
        """ this is just to be able to iterate over func
            args
        """
        args = [args]
      assert len(func.args) == len(args)
      for k, v in zip(func.args, args):
        v =v.eval(frame)  # TODO: Why need extra eval??
        if isinstance(v, ast.Int): v = Int(v.value) # dirty hack to overcome parser bug
        newframe[k.value] = v
      return func.Call(newframe)


def fix_main_signature(main):
  """ Force main() to return Int. """
  if main.type.ret == Int:
    return
  main.type.ret = Int
  body = main.body
  if not isinstance(body, Block):
    body = Block(body)
  body.append(Int(0))
  main.body = body


##########################
# Higher-Order Functions #
##########################

@replaces(ast.ComposeR)
class ComposeR(Binary):
  def eval(self, frame):
    right = self.right.eval(frame)
    left = self.left.eval(frame)
    return Call(left, right).eval(frame)



def run(ast, args=['<progname>'], check_types=False):
  ast = rewrite(ast, replace_nodes)
  log.final_ast("the final AST is:\n", ast)

  frame = Frame()
  ast.eval(frame)
  log.topframe("the top frame is\n", frame)

  if 'main' not in frame:
    print("no main function defined, exiting")
    return 0

  # type inference
  if check_types:
    with frame as newframe:
      newframe['argc'] = Int(len(args))
      newframe['argv'] = Array(map(Str, args))
      main = newframe['main']
      main.infer_type(newframe)
      if main.type.ret != Int:
        # print("main() should return Int but got %s" % main.type.ret)
        # print("so it will be fixed to return 0")
        fix_main_signature(main)


  with frame as newframe:
    newframe['argc'] = Int(len(args))
    newframe['argv'] = Array(map(Str, args))
    r = newframe['main'].Call(newframe)

  if isinstance(r, Int):
    return r.to_int()
  else:
    return 0
