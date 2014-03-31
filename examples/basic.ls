main = (argc, argv) ->
  # basic arithmetic
  assert 1 - 1 == 0
  assert 1 + 1 == 2
  assert 1 < 2
  assert 2 > 1
  assert 1 + 2 * 3 == 7
  assert (1 + 2)*3 == 9
  assert 2^1^2 == 2
  assert (2^1)^2 == 4
  s1 =  "operator print works as a polymorphic unary operator"
  s2 = p s1
  assert s1 == s2

  # working with arrays
  arr = [1,2,3]

  # recursion
  inc = (val, howmuch) ->
    match
      howmuch > 0  => inc (val + 1), howmuch - 1
      _            => val
  assert (inc 0, 3) == 3

  # shell invocation
  filename = "/etc/resolv.conf"
  p "First three lines of {filename}:"
  p `head -n3 {filename}`

  # higher-order functions
  succ = (arg) -> arg + 1
  assert (succ succ 1) == 3
  assert succ . (succ 1) == 3
  #assert succ 0 $ succ $ succ = 3

  # control statements
  1 if 2 else 3

  match
    argc == 1  => p "I've got just 1 argument: {argv}"
    _          => p "I've got {argc} arguments: {argv}"
