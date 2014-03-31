from peg import RE, SOMEOF, OR, SYMBOL, NoMatch
from ast import symap, Id, Int, Str, ShellCmd, RegEx, Comment
from log import Log

log = Log("tokenizer")

# CONSTANTS
FLOATCONST = RE(r'\d+\.\d*')
INTCONST   = RE(r'\d+', Int)
STRCONST   = RE(r'"(.*)"', Str)
SHELLCMD   = RE(r'`(.*)`', ShellCmd)
REGEX      = RE(r'/(.*)/', RegEx)
CONST = FLOATCONST | INTCONST | STRCONST | SHELLCMD | REGEX

# COMMENTS
SHELLCOMMENT = RE(r'\#.*', Comment)
CPPCOMMENT   = RE(r'//.*', Comment)
CCOMMENT     = RE(r'/\*.*?\*/', Comment)
COMMENT = SHELLCOMMENT | CCOMMENT | CPPCOMMENT

# TODO: add this to PROG
# END is like ENDL (end of line)
# but allows trailing comments
EOL = RE(r'$')  # end of line
END = EOL | (COMMENT+EOL)

# IDENTIFIER (FUNCTION NAMES, VARIABLES, ETC)
ID = RE(r'[A-Za-z_][a-zA-Z0-9_]*', Id)

# put longest operators first because for PEG first match wins
operators = []
for sym in sorted(symap.keys(), key=len, reverse=True):
  operators += [SYMBOL(sym, symap[sym])]
OPERATOR = OR(*operators)
PROGRAM = SOMEOF(COMMENT, CONST, OPERATOR, ID) #+ END


class DENT:
  def __init__(self, lvl):
    self.value = lvl

  def __repr__(self):
    return "DENT:%s" % self.value


def get_indent(s):
  """Get current indent in symbols""" #TODO: Check that indent is in spaces, not tabs
  depth = 0
  for depth, c in enumerate(s):
    if not c.isspace():
      break
  return depth


def tokenize(raw):
  tokens = []
  for i,l in enumerate(raw.splitlines(), 1):
    if not l:
      continue
    tokens += [DENT(get_indent(l))]
    try:
      ts, pos = PROGRAM.parse(l)
    except NoMatch:
      raise Exception("cannot parse string:\n%s"%l)
    if len(l) != pos:
      if pos > 5: ptr = "here {}┘".format("─"*(pos-4))
      else:       ptr = " "*(pos+1) + "└─── error is somewhere here"
      msg = "{msg}:\n\"{text}\"\n{ptr}\n" \
            .format(msg="Cannot parse line %s"%i, text=l, ptr=ptr)
      raise Exception(msg)
    tokens += ts

  log("after tokenizer:\n", tokens)
  return tokens