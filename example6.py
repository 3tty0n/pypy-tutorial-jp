"""
PyPy tutorial by Andrew Brown
example6.py - BF interpreter in RPython with aggressive JIT optimizations

Optimizations applied:
1. @elidable decorator for pure functions (bracket_map lookups)
2. @unroll_safe for functions with bounded loops
3. promote() hint to turn runtime values into compile-time constants
4. Virtualizables for the Tape object to avoid heap allocation
5. Fixed-size tape array to enable better array optimizations
6. loop_invariant hint for values that don't change in loops

"""

import os
import sys

try:
    from rpython.rlib.jit import JitDriver, elidable, unroll_safe, promote, promote_string
    from rpython.rlib.jit import hint, set_param, we_are_jitted
except ImportError:
    class JitDriver(object):
        def __init__(self,**kw): pass
        def jit_merge_point(self,**kw): pass
        def can_enter_jit(self,**kw): pass
    def elidable(f): return f
    def unroll_safe(f): return f
    def promote(x): return x
    def promote_string(x): return x
    def hint(x, **kw): return x
    def set_param(driver, name, value): pass
    def we_are_jitted(): return False

try:
    from rpython.rlib.rarithmetic import ovfcheck
except ImportError:
    def ovfcheck(x): return x

# Use virtualizables to tell the JIT that 'tape' can be virtualized
# This avoids heap allocation for the tape in compiled traces
try:
    from rpython.rlib.jit import JitDriver
    jitdriver = JitDriver(
        greens=['pc', 'program', 'bracket_map'],
        reds=['tape'],
        virtualizables=['tape'],
        get_printable_location=lambda pc, program, bracket_map: "%s_%s_%s" % (
            program[pc-1] if pc > 0 else ' ',
            program[pc],
            program[pc+1] if pc + 1 < len(program) else ' '
        )
    )
except:
    jitdriver = JitDriver(
        greens=['pc', 'program', 'bracket_map'],
        reds=['tape'],
        get_printable_location=lambda pc, program, bracket_map: "%s_%s_%s" % (
            program[pc-1] if pc > 0 else ' ',
            program[pc],
            program[pc+1] if pc + 1 < len(program) else ' '
        )
    )


@elidable
def get_bracket_target(bracket_map, pc):
    return bracket_map.get(pc, -1)


class Tape(object):
    """
    Tape with _virtualizable_ hint for better JIT optimization.
    Note: We only virtualize 'position' and 'thetape', not 'thetape[*]'.
    """
    _immutable_fields_ = ['size']
    _virtualizable_ = ['position', 'thetape']

    def __init__(self):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.size = 30000
        self.thetape = [0] * self.size  # Standard BF tape size
        self.position = 0

    def get(self):
        pos = self.position
        assert 0 <= pos < self.size
        return self.thetape[pos]

    def set(self, val):
        pos = self.position
        assert 0 <= pos < self.size
        self.thetape[pos] = val

    def inc(self):
        pos = self.position
        assert 0 <= pos < self.size
        self.thetape[pos] += 1

    def dec(self):
        pos = self.position
        assert 0 <= pos < self.size
        self.thetape[pos] -= 1

    def advance(self):
        self.position += 1
        assert 0 <= self.position < self.size

    def devance(self):
        self.position -= 1
        assert 0 <= self.position < self.size


def mainloop(program, bracket_map):
    pc = 0
    tape = Tape()

    # Promote program to a constant - it never changes during execution
    program = promote_string(program)

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program,
                bracket_map=bracket_map)

        code = program[pc]

        if code == ">":
            tape.advance()

        elif code == "<":
            tape.devance()

        elif code == "+":
            tape.inc()

        elif code == "-":
            tape.dec()

        elif code == ".":
            os.write(1, chr(tape.get()))

        elif code == ",":
            tape.set(ord(os.read(0, 1)[0]))

        elif code == "[":
            if tape.get() == 0:
                # Use elidable function for bracket lookup
                pc = get_bracket_target(bracket_map, pc)

        elif code == "]":
            if tape.get() != 0:
                # Backward jump - use elidable lookup
                pc = get_bracket_target(bracket_map, pc)
                # Tell JIT this is a loop back-edge
                jitdriver.can_enter_jit(pc=pc, tape=tape, program=program,
                        bracket_map=bracket_map)

        pc += 1


@unroll_safe
def parse(program):
    """
    @unroll_safe tells the JIT it's safe to unroll loops in this function,
    even though it contains a loop. This is safe because parse() is only
    called once before the main loop.
    """
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
