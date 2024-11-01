# Tutorial: Writing an Interpreter with PyPy
This is a clone of [a guest blog post by Andrew Brown](https://codespeak.net/pipermail/pypy-dev/2011q2/007128.html), originally posted to the pypy-dev mailing list. The master of this tutorial was originally hosted on [bitbucket](https://bitbucket.org/brownan/pypy-tutorial/), however, it is no longer available.

**Disclaimer**:
- This clone was created for educational purposes at [PRG-group](https://prg.is.titech.ac.jp/), Institute of Science Tokyo.

## Schedule
- Day 1: [Part 1](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#)
- Day 2: [Part 2](https://pypy.org/posts/2011/04/tutorial-part-2-adding-jit-8121732841568309472.html)
- Day 3, Day 4: Try adding something new features or reading [PyPy papers](https://doc.pypy.org/en/latest/extradoc.html)
  - Change the way you trace
  - Create a JIT for your own language

## Requirements
- Python 2
- RPython

## Note
- RPython is now located within [the PyPy repository](https://foss.heptapod.net/pypy/pypy).
  - `rpython` can be found at `./pypy-branch-default/rpython/bin/rpython` by default.
- Keep in mind that RPython is written in **Python 2**, even if it’s not directly mentioned in the tutorial.
  - If the `python` command in `$ python [rpython] example2.py` in your environment internally references Python 3, you may encounter a parsing error from RPython.
  - Switching Python versions is easy with [pyenv](https://github.com/pyenv/pyenv).
- If you succeed up to the end of [Part 1](https://pypy.org/posts/2011/04/tutorial-writing-interpreter-with-pypy-3785910476193156295.html#), you will get the output:

<img width="400" alt="mandel.png" src="https://github.com/prg-titech/pypy-tutorial-jp/blob/main/mandel.png">