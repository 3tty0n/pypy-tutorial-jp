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
    from rpython.rlib.jit import JitDriver, purefunction
except ImportError:
    class JitDriver(object):
        def __init__(self,**kw): pass
        def jit_merge_point(self,**kw): pass
        def can_enter_jit(self,**kw): pass
    def purefunction(f): return f

def get_location(pc, program, bracket_map):
    return "%s_%s_%s" % (
            program[:pc], program[pc], program[pc+1:]
            )

jitdriver = JitDriver(greens=['pc', 'program', 'bracket_map'], reds=['tape'],
        get_printable_location=get_location)

def optimizer(program):
    program = clearLoops(program)
    program_encoded = runLengthEncode(program)
    return program_encoded

def runLengthEncode(program):
    n = len(program)
    encoded = []
    l = 0
    while l < n:
        if program[l] in ('<', '>', '+', '-'):
            r = l+1
            while r < n and program[l] == program[r]:
                r += 1
            encoded.append((program[l], r-l))
            l = r
        else:
            encoded.append((program[l], 1))
            l += 1
        
    return encoded

def clearLoops(program):
    l = 0
    ans = []
    while l+2 < len(program):
        if (program[l] == '[') and (program[l+1] == '-') and (program[l+2] == ']'):
            ans.append('^')
            l += 3
        else:
            ans.append(program[l])
            l += 1
    ans.append(program[l])
    ans.append(program[l+1])
    return "".join(ans)

@purefunction
def get_matching_bracket(bracket_map, pc):
    return bracket_map[pc]

def mainloop(program, bracket_map):
    pc = 0
    tape = Tape()
    program_inst = []
    program_arg = []
    # for pair in program:
    #     program_inst.append(pair[0])
    #     program_arg.append(pair[1])

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program, bracket_map=bracket_map)
        
        op, num = program[pc]

        if op == ">":
            # for i in range(num):
            #     tape.advance()
            tape.rightShift(num)

        elif op == "<":
            # for i in range(num):
            #     tape.devance()
            tape.leftShift(num)

        elif op == "+":
            # for i in range(num):
            #     tape.inc()
            tape.add(num)

        elif op == "-":
            # for i in range(num):
            #     tape.dec()
            tape.sub(num)
        
        elif op == ".":
            # print
            os.write(1, chr(tape.get()))
        
        elif op == ",":
            # read from stdin
            tape.set(ord(os.read(0, 1)[0]))

        elif op == "[" and tape.get() == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)
            
        elif op == "]" and tape.get() != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)

        elif op == "^":
            tape.set(0)
        
        pc += 1

class Tape(object):
    def __init__(self):
        self.thetape = [0]
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
        if len(self.thetape) <= self.position:
            self.thetape.append(0)
    def devance(self):
        self.position -= 1
    
    def add(self, n):
        self.thetape[self.position] += n
    def sub(self, n):
        self.thetape[self.position] -= n
    
    def rightShift(self, n):
        self.position += n
        if len(self.thetape) <= self.position:
            self.thetape.extend( [0] * (self.position - len(self.thetape) + 1) )
    def leftShift(self, n):
        self.position -= n

def parse(program):
    parsed = []
    bracket_map = {}
    leftstack = []
    program = optimizer(program)

    pc = 0
    for op, num in program:
        if op in ('[', ']', '<', '>', '+', '-', ',', '.', '^'):
            parsed.append((op, num))

            if op == '[':
                leftstack.append(pc)
            elif op == ']':
                left = leftstack.pop()
                right = pc
                bracket_map[left] = right
                bracket_map[right] = left
            pc += 1

    # with open('parsed.txt', 'w') as o:
    #     for op, num in parsed:
    #         o.write("(" + op + " : " + str(num) + ")\n")
    return parsed, bracket_map

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