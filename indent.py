from tokenizer import DENT
from log import Log
from copy import copy
from ast import Block, Expr
log = Log("indent")


def implicit_dents(tokens):
  tokens = copy(tokens)
  c = 0
  for i,t in enumerate(tokens):
    if isinstance(t, DENT):
      c = t.value
    elif hasattr(t, "sym") and t.sym in ["->", "=>"]:
      for t in tokens[i:]:
        if isinstance(t, DENT):
          if t.value > c:
            tokens.insert(i+1, DENT(t.value))
          break
  return tokens


def merge_dents(tokens):
  tokens = copy(tokens)
  i = 0
  while i < len(tokens)-1:
    if isinstance(tokens[i], DENT) and isinstance(tokens[i+1], DENT):
      del tokens[i]
    else:
      i += 1
  return tokens


def blocks(it, lvl=0):
  cur = lvl
  expr = Expr()
  blk = Block(expr)
  prefix = str(lvl)+" "*(lvl-1)
  for t in it:
    log.indent(prefix, "considering", t)
    if isinstance(t, DENT):
      cur = t.value
      if cur == lvl and expr:
        log.indent(prefix, "got newline, starting new expr")
        expr = Expr()
        blk.append(expr)
        continue
      elif cur > lvl:
        log.indent(prefix, ">>> calling nested block")
        r, cur = blocks(it, cur)
        log.indent(prefix, "<<< got %s from it with level %s" % (r, cur))
        expr.append(r)
        if cur == lvl:
          log.indent(prefix, "!!! starting new expression")
          expr = Expr()
          blk.append(expr)
    else:
      log.indent(prefix, "adding %s to expr %s" % (t,expr))
      expr.append(t)
    if cur < lvl:
        log.indent(prefix, "<== %s < %s: time to return" % (cur, lvl))
        return blk, cur
  return blk, lvl


def parse(tokens):
  tokens = implicit_dents(tokens)
  log.imp_dents("after adding implicit dents:\n", tokens)
  tokens = merge_dents(tokens)
  log.merge_dents("merging dents:\n", tokens)
  ast, _ = blocks(iter(tokens))
  log.blocks("after block parser:\n", ast)
  return ast