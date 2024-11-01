# Tutorial: Writing an Interpreter with PyPy

# Schedule
- Day 1: [Part 1](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#)
- Day 2: [Part 2](https://pypy.org/posts/2011/04/tutorial-part-2-adding-jit-8121732841568309472.html)
- Day 3, Day 4: Try adding something new features or reading [PyPy papers](https://doc.pypy.org/en/latest/extradoc.html)
  - Change the way you trace
  - Create a JIT for your own language

# Note
- RPython is now in the PyPy repository. → https://foss.heptapod.net/pypy/pypy
  - RPython can be found at ./[branch name, probably pypy-branch-default by default]/rpython/bin/rpython.
- Keep in mind that RPython is written in *Python 2*, even if it’s not directly mentioned in the tutorial.
  - If the `python` command in `$ python [rpython] example2.py` in your environment internally references Python 3, you may encounter a parsing error from RPython.
  - Switching Python versions is easy with [pyenv](https://github.com/pyenv/pyenv).
- If you succeed up to the end of Part 1, you should see output: ![https://github.com/hibara/TestRepository/blob/master/image/test.png]