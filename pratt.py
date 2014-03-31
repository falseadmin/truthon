#!/usr/bin/env python3

"""
Pratt-like parser.
Inspired by http://effbot.org/zone/simple-top-down-parsing.htm
"""

from itertools import chain
symap = {}


def symbol(sym, lbp=0):
  try:
    Sym = symap[sym]
  except KeyError:
    class Sym: pass
    Sym.__name__ = Sym.__qualname__ = "Sym('%s')" % sym
    Sym.__repr__ = lambda _: "Sym('%s')" % sym
    Sym.sym = sym
    Sym.lbp = lbp
    symap[sym] = Sym
  else:
    Sym.lbp = max(lbp, Sym.lbp)
  return Sym


class prefix:
  def __init__(self, sym, rbp):
    self.sym = sym
    self.rbp = rbp

  def __call__(self, cls):
    rbp = self.rbp
    def nud(self):
      return cls(expr(rbp))
    symbol(self.sym).nud = nud
    return cls


class infix:
  def __init__(self, sym, lbp):
    self.sym = sym
    self.lbp = lbp

  def __call__(self, cls):
    def led(self, left):
      return cls(left, expr(self.lbp))
    symbol(self.sym, self.lbp).led = led
    return cls


class infix_r:
  def __init__(self, sym, lbp):
    self.sym = sym
    self.lbp = lbp

  def __call__(self, cls):
    def led(self, left):
      return cls(left, expr(self.lbp-1))
    symbol(self.sym, self.lbp).led = led
    return cls


class postfix:
  def __init__(self, sym, lbp):
    self.sym = sym
    self.lbp = lbp

  def __call__(self, cls):
    def led(self, left):
      return cls(left)
    symbol(self.sym, self.lbp).led = led
    return cls


class nullary:
  """a zero-arg operator (== keyword)"""
  def __init__(self, sym):
    self.sym = sym

  def __call__(self, cls):
    def nud(self):
      return cls(self.sym)
    symbol(self.sym).nud = nud
    return cls


class brackets:
  def __init__(self, open, close):
    self.open = open
    self.close = close

  def __call__(self, cls):
    open = self.open
    close = self.close
    def nud(self):
      e = expr()
      advance(close)
      return cls(e)
    symbol(open).nud = nud
    symbol(close)
    return cls


class subscript:
  """ Postfix subscriptions, e.g., array[1]. """
  def __init__(self, *args):
    if len(args) == 2:   # no close tag defined
      self.open, self.lbp = args
      self.close = None
    elif len(args) == 3: # there is a close tag
      self.open, self.close, self.lbp = args

  def __call__(self, cls):
    open  = self.open
    close = self.close
    lbp   = self.lbp
    def led(self, left):
      right = expr()
      if close:
        advance(close)
      return cls(left, right)
    symbol(open, lbp=1000).led = led
    symbol(close)
    return cls


class ifelse:
  """ Ternary operator with a slightly strange syntax VALUE if COND else VALUE"""
  def __init__(self, lbp):
    self.lbp = lbp

  def __call__(self, cls):
    def led(self, left):
      then = left
      iff = expr()
      advance("else")
      otherwise = expr()
      return cls(iff, then, otherwise)
    symbol("if", lbp=self.lbp).led = led
    symbol("else")
    return cls


class END:
  """ A guard at the end of expression. """
  lbp = 0
  def __repr__(self):
    return "END"


###################
# PRATT MACHINERY #
###################

def shift():
  global nxt, e
  return nxt, next(e)


def advance(sym=None):
  global cur, nxt
  cur, nxt = shift()
  if sym and cur.sym != sym:
      raise SyntaxError("Expected %r" % sym)


def expr(rbp=0):
  global cur, nxt
  cur, nxt = shift()
  left = cur.nud()
  while rbp < nxt.lbp:
    cur, nxt = shift()
    left = cur.led(left)
  return left


def parse(tokens):
  global cur, nxt, e
  assert symap, "No operators registered." \
    "Please define at least one operator decorated with infix()/prefix()/etc"
  cur = nxt = None
  e = chain(tokens, [END])
  cur, nxt = shift()
  result = expr()
  # sanity check
  try:
    next(e)
    raise Exception("not all tokens was parsed: either there is " \
                    "a grammar error or problem with operators")
  except StopIteration:
    pass
  return result
