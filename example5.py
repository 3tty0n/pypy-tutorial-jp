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
    from rpython.rlib.jit import JitDriver, purefunction, elidable, promote, unroll_safe, hint, promote_string
    from rpython.rlib.objectmodel import always_inline
except ImportError:
    class JitDriver(object):
        def __init__(self,**kw): pass
        def jit_merge_point(self,**kw): pass
        def can_enter_jit(self,**kw): pass
    def purefunction(f): return f
    def promote(f): return f
    def elidable(f): return f
    def promote_string(f): return f
    def always_inline(f): return f


def get_location(pc, program, bracket_map):
    return "%s_%s_%s" % (
            #program[:pc], program[pc], program[pc+1:]
            program[pc-1], program[pc], program[pc+1]
            )

jitdriver = JitDriver(greens=['pc', 'program', 'bracket_map'], reds=['position', 'thetape'],
                      get_printable_location=get_location)

@elidable
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
    thetape = [0] * 1024
    position = 0

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, thetape=thetape, position=position, program=program,
                bracket_map=bracket_map)

        code = promote(ord(program[pc]))

        if code == RIGHT:
            # tape.advance()
            position += 1
            assert position < len(thetape)

        elif code == LEFT:
            # tape.devance()
            position -= 1
            assert position >= 0

        elif code == PLUS:
            # tape.inc()
            thetape[position] += 1

        elif code == MINUS:
            # tape.dec()
            thetape[position] -= 1

        elif code == DOT:
            # print
            v = promote(chr(thetape[position]))
            os.write(1, v)

        elif code == COMMA:
            # read from stdin
            v = promote(ord(os.read(0, 1)[0]))
            if v != 0:
                thetape[position] = v

        elif code == LBRACK and thetape[position] == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)

        elif code == RBRACK and thetape[position] != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)
            jitdriver.can_enter_jit(pc=pc, thetape=thetape, position=position, program=program,
                    bracket_map=bracket_map)

        pc += 1


@unroll_safe
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
