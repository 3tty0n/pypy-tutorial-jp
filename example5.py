"""
PyPy tutorial by Andrew Brown
example5.py - BF interpreter in RPython, translatable by PyPy, with JIT, and
              with a get_printable_location function and pure function wrapper
              for the dictionary lookup.

"""

import os
import sys

# So that you can still run this module under standard CPython, I add this
# import guard that creates a dummy class instead.
try:
    from rpython.rlib.jit import JitDriver, purefunction, elidable, promote
except ImportError:
    class JitDriver(object):
        def __init__(self,**kw): pass
        def jit_merge_point(self,**kw): pass
        def can_enter_jit(self,**kw): pass
    def purefunction(f): return f
    def promote(f): return f
    def elidable(f): return f

def get_location(pc, program, bracket_map):
    return "%s_%s_%s" % (
            program[pc-1], program[pc], program[pc+1]
            )

jitdriver = JitDriver(greens=['pc', 'program', 'bracket_map'], reds=['tape'],
        get_printable_location=get_location)

@purefunction
def get_matching_bracket(bracket_map, pc):
    return bracket_map[pc]

RIGHT = ord('>')
LEFT = ord('<')
PLUS = ord('+')
MINUS = ord('-')
DOT = ord('.')
COMMA = ord(',')
LBRACK = ord('[')
RBRACK = ord(']')

def mainloop(program, bracket_map):
    pc = 0
    tape = Tape()

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program,
                bracket_map=bracket_map)

        code = ord(program[pc])

        if code == RIGHT:
            tape.advance()

        elif code == LEFT:
            tape.devance()

        elif code == PLUS:
            tape.inc()

        elif code == MINUS:
            tape.dec()

        elif code == DOT:
            # print
            v = chr(tape.get())
            promote(v)
            os.write(1, v)

        elif code == COMMA:
            # read from stdin
            v = promote(ord(os.read(0, 1)[0]))
            tape.set(v)

        elif code == LBRACK and tape.get() == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)

        elif code == RBRACK and tape.get() != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)
            jitdriver.can_enter_jit(pc=pc, tape=tape, program=program,
                    bracket_map=bracket_map)

        pc += 1

class Tape(object):
    def __init__(self):
        self.thetape = [0] * 1024
        self.position = 0

    def get(self):
        return self.thetape[self.position]
    def set(self, val):
        self.thetape[self.position] = val
    def inc(self):
        self.thetape[self.position] += 1
    def dec(self):
        self.thetape[self.position] -= 1
    def advance(self):
        self.position += 1
        assert not len(self.thetape) <= self.position
    def devance(self):
        self.position -= 1

def parse(program):
    parsed = []
    bracket_map = {}
    leftstack = []

    pc = 0
    for char in program:
        if char in ('[', ']', '<', '>', '+', '-', ',', '.'):
            parsed.append(char)

            if char == '[':
                leftstack.append(pc)
            elif char == ']':
                left = leftstack.pop()
                right = pc
                bracket_map[left] = right
                bracket_map[right] = left
            pc += 1

    return "".join(parsed), bracket_map

def run(fp):
    program_contents = ""
    while True:
        read = os.read(fp, 4096)
        if len(read) == 0:
            break
        program_contents += read
    os.close(fp)
    program, bm = parse(program_contents)
    mainloop(program, bm)

def entry_point(argv):
    try:
        filename = argv[1]
    except IndexError:
        print "You must supply a filename"
        return 1

    run(os.open(filename, os.O_RDONLY, 0777))
    return 0

def target(*args):
    return entry_point, None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == "__main__":
    entry_point(sys.argv)
