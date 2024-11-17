"""
PyPy tutorial by Andrew Brown
example5.py - BF interpreter in RPython, translatable by PyPy, with JIT, and
              with a get_printable_location function and pure function wrapper
              for the dictionary lookup.

"""

import time
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

def get_location(pc, program, bracket_map, multiple_memory):
    return "%s_%s_%s" % (
            program[:pc], program[pc], program[pc+1:]
            )

jitdriver = JitDriver(greens=['pc', 'program', 'bracket_map', 'multiple_memory'], reds=['tape'],
        get_printable_location=get_location)

@purefunction
def get_matching_bracket(bracket_map, pc):
    return bracket_map[pc]

def mainloop(program, bracket_map, multiple_memory):
    pc = 0
    tape = Tape()
    i = 0
    
    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program,
                bracket_map=bracket_map, multiple_memory = multiple_memory)

        code, count = program[pc]

        if code == ">":
            tape.advance(count)

        elif code == "<":
            tape.devance(count)

        elif code == "+":
            tape.inc(count)

        elif code == "-":
            tape.dec(count)
        
        elif code == ".":
            # print
            os.write(1, chr(tape.get()))
        
        elif code == ",":
            # read from stdin
            tape.set(ord(os.read(0, 1)[0]))

        elif code == "[" and tape.get() == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)
            
        elif code == "]" and tape.get() != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)

        elif code == "^":
            tape.clean()

        elif code == "=":
            tape.copy(count, multiple_memory[pc])

        pc += 1

class Tape(object):
    def __init__(self):
        self.thetape = [0]
        self.position = 0

    def get(self):
        return self.thetape[self.position]
    def set(self, val):
        self.thetape[self.position] = val
    def inc(self, count):
        self.thetape[self.position] += count
    def dec(self, count):
        self.thetape[self.position] -= count
    def advance(self, count):
        self.position += count
        if self.position >= len(self.thetape):
            self.thetape.extend([0] * (self.position - len(self.thetape) + 1))
    def devance(self, count):
        self.position -= count
    def clean(self):
        self.set(0)
    def copy(self, count, val):
        if self.position + count  >= len(self.thetape):
            self.thetape.extend([0] * (self.position + count - len(self.thetape) + 1))
        self.thetape[self.position + count] += self.thetape[self.position] * val

def parse(program):
    parsed = []
    bracket_map = {}
    multiple_memory = {}
    leftstack = []
    pc = 0
    i = 0

    while i < len(program):
        while i < len(program):
            move = 0
            char = program[i]
            count = 1
            if char in ('[', ']', '<', '>', '+', '-', ',', '.'):
                if char in ('<', '>', '+', '-'):
                    while i + 1 < len(program) and (program[i + 1] == char or program[i + 1] not in ('[', ']', '<', '>', '+', '-', ',', '.')):
                        if program[i + 1] == char:
                            count += 1
                        i += 1

                elif char in ('[' , ']'):
                    if program[i:i+3] == '[-]':
                        char = '^'
                        i += 2
                    elif program[i:i+2] == '[-':
                        j = i + 1
                        while j + 1 < len(program) and program[j + 1] not in ('[', ']', ',', '.'):
                            if program[j + 1] == '>':
                                move += 1
                            elif program[j + 1] == '<':
                                move -= 1
                            j += 1
                        if program[j:j+2] in ('<]', '>]') and move == 0:
                            i += 2
                            break
                        else: 
                            leftstack.append(pc)
                    elif char == '[':
                        leftstack.append(pc)
                    elif char == ']':
                        left = leftstack.pop()
                        right = pc
                        bracket_map[left] = right
                        bracket_map[right] = left
                
                parsed.append((char,count))
                pc += 1
            i += 1

        move = 0

        while i < len(program):
            char = program[i]
            count = 1
            if char in ('[', ']', '<', '>', '+', '-', ',', '.'):
                if char == '<':
                    move -= 1
                    while i + 1 < len(program) and (program[i + 1] == char or program[i + 1] not in ('[', ']', '<', '>', '+', '-', ',', '.')):
                        if program[i + 1] == char:
                            count += 1
                            move -= 1
                        i += 1
                    parsed.append(('=', move))
                    pc += 1

                if char == '>':   
                    move += 1
                    while i + 1 < len(program) and (program[i + 1] == char or program[i + 1] not in ('[', ']', '<', '>', '+', '-', ',', '.')):
                        if program[i + 1] == char:
                            count += 1
                            move += 1
                        i += 1
                    parsed.append(('=', move))
                    pc += 1

                elif char in ('+', '-'):
                    while i + 1 < len(program) and (program[i + 1] == char or program[i + 1] not in ('[', ']', '<', '>', '+', '-', ',', '.')):
                        if program[i + 1] == char:
                            count += 1
                        i += 1
                    if char == '+':
                        multiple_memory[pc - 1] = count
                    else:
                        multiple_memory[pc - 1] = -count

                elif char == ']':
                    parsed[-1] = (('^', 0))
                    i += 1
                    break

            i += 1

    return parsed, bracket_map, multiple_memory

def run(fp):
    program_contents = ""
    while True:
        read = os.read(fp, 4096)
        if len(read) == 0:
            break
        program_contents += read
    os.close(fp)
    program, bm, multiple_memory = parse(program_contents)
    #print(program)
    #print(bm)
    #print(multiple_memory)
    mainloop(program, bm, multiple_memory)

def entry_point(argv):
    try:
        filename = argv[1]
    except IndexError:
        print "You must supply a filename"
        return 1
    
    start_time = time.time()
    
    run(os.open(filename, os.O_RDONLY, 0777))

    end_time = time.time()
    print("Execution time:", end_time - start_time, "seconds")
    return 0

def target(*args):
    return entry_point, None
    
def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == "__main__":
    entry_point(sys.argv)
