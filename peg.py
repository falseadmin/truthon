#!/usr/bin/env python3
import re


class NoMatch(Exception):
  pass


class Grammar:
  def __add__(self, other):
    if isinstance(self, ALL):
      self.things += [other]
      return self
    return ALL(self, other)

  def __or__(self, other):
    if isinstance(self, OR):
      self.things += [other]
      return self
    return OR(self, other)


class RE(Grammar):
  def __init__(self, pattern, token=str, passval=True):
    self.pattern_orig = pattern
    self.pattern = re.compile("\s*(%s)" % pattern)
    self.token   = token
    self.passval = passval

  def parse(self, text, pos=0):
    m = self.pattern.match(text[pos:])
    if not m:
      raise NoMatch("syntax error", text, pos)
    text = m.groups()[-1]
    newpos = pos+m.end()
    if self.passval:
      return self.token(text), newpos
    else:
      return self.token(), newpos

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s(\"%s\", %s)" % (cls, self.pattern_orig, self.token)


class SYMBOL(RE):
  def __init__(self, symbol, *args, **kwargs):
    super().__init__(re.escape(symbol), *args, passval=False, **kwargs)


########################
# HIGHER-ORDER PARSERS #
########################

class Composer(Grammar):
  def __init__(self, *things):
    self.things = list(things)

  def __repr__(self):
    cls  = self.__class__.__name__
    return "%s(%s)" % (cls, self.things)


class OR(Composer):
  """ First match wins
  """
  def parse(self, text, pos=0):
    for thing in self.things:
      try:
        return thing.parse(text, pos)
      except NoMatch:
        pass
    raise NoMatch("syntax error", text, pos)


class SOMEOF(Composer):
  def parse(self, text, pos=0):
    result = []
    while True:
      for thing in self.things:
        try:
          r, pos = thing.parse(text, pos)
          result += [r]
          break  # break is neccessary because it's a PEG parser and the order does matter
        except NoMatch:
          pass
      else:
        break
    if not result:
      raise NoMatch("syntax error", text, pos)
    return result, pos


class MAYBE(Composer):
  def parse(self, text, pos=0):
    oldpos = pos
    result = []
    try:
      for thing in self.things:
        r, pos = thing.parse(text, pos)
        result += [r]
    except NoMatch:
      return None, oldpos
    return result, pos


class ALL(Composer):
  def parse(self, text, pos=0):
    result = []
    for thing in self.things:
      r, pos = thing.parse(text, pos)
      result += [r]
    return result, pos


if __name__ == '__main__':
  INTCONST = RE(r'[-]{0,1}\d+')
  print(INTCONST.parse("-1"))
