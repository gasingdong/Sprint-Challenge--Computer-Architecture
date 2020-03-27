"""CPU functionality."""

import sys

HALT = 0b00000001
LDI = 0b10000010
PRN = 0b01000111
NOP = 0b00000000
MULT = 0b10100010
POP = 0b01000110
PUSH = 0b01000101
CALL = 0b01010000
RET = 0b00010001
ADD = 0b10100000
CMP = 0b10100111
JMP = 0b01010100
JEQ = 0b01010101
JNE = 0b01010110
AND = 0b10101000
XOR = 0b10101011
OR = 0b10101010
NOT = 0b01101001
SHL = 0b10101100
SHR = 0b10101101
MOD = 0b10100100

SP = 7


class ALU:
    """ALU class."""

    def __init__(self, parent_cpu):
        self.cpu = parent_cpu
        self.branchtable = {}
        self.add_branch(AND, self.and_op)
        self.add_branch(XOR, self.xor)
        self.add_branch(OR, self.or_op)
        self.add_branch(NOT, self.not_op)
        self.add_branch(SHL, self.shl)
        self.add_branch(SHR, self.shr)
        self.add_branch(MOD, self.mod)
        self.add_branch(MULT, self.mult)
        self.add_branch(ADD, self.add)
        self.add_branch(CMP, self.cmp_op)

    def add_branch(self, opcode, handler):
        self.branchtable[opcode] = handler

    def mod(self, reg_a, reg_b):
        num = self.cpu.reg[reg_b]
        if num == 0:
            raise Exception("Unsupported ALU operation - division by zero")
        else:
            self.cpu.reg[reg_a] = self.cpu.reg[reg_a] % num

    def shl(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = self.cpu.reg[reg_a] << self.cpu.reg[reg_b]

    def shr(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = self.cpu.reg[reg_a] >> self.cpu.reg[reg_b]

    def not_op(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = ~self.cpu.reg[reg_a] & ((1 << 8) - 1)

    def or_op(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = self.cpu.reg[reg_a] | self.cpu.reg[reg_b]

    def xor(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = self.cpu.reg[reg_a] ^ self.cpu.reg[reg_b]

    def and_op(self, reg_a, reg_b):
        self.cpu.reg[reg_a] = self.cpu.reg[reg_a] & self.cpu.reg[reg_b]

    def add(self, reg_a, reg_b):
        self.cpu.reg[reg_a] += self.cpu.reg[reg_b]

    def mult(self, reg_a, reg_b):
        self.cpu.reg[reg_a] *= self.cpu.reg[reg_b]

    def cmp_op(self, reg_a, reg_b):
        num1 = self.cpu.reg[reg_a]
        num2 = self.cpu.reg[reg_b]
        if num1 == num2:
            self.cpu.fl = 0b00000001
        elif num1 < num2:
            self.cpu.fl = 0b00000100
        elif num1 > num2:
            self.cpu.fl = 0b00000010

    def run(self, opcode, reg_a, reg_b):
        if opcode in self.branchtable:
            return self.branchtable[opcode](reg_a, reg_b)
        else:
            raise Exception("Unsupported ALU operation")


class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        self.reg = [0] * 8
        self.reg[SP] = 0xF4
        self.ram = [0] * 256
        self.pc = 0
        self.fl = 0
        self.branchtable = {}
        self.add_branch(HALT, self.halt)
        self.add_branch(LDI, self.ldi)
        self.add_branch(PRN, self.prn)
        self.add_branch(NOP, self.nop)
        self.add_branch(POP, self.pop)
        self.add_branch(PUSH, self.push)
        self.add_branch(CALL, self.call)
        self.add_branch(RET, self.ret)
        self.add_branch(JMP, self.jmp)
        self.add_branch(JEQ, self.jeq)
        self.add_branch(JNE, self.jne)
        self.alu_ops = {AND, XOR, OR, NOT, SHL, SHR, MOD, MULT, ADD, CMP}
        self.alu = ALU(self)

    def add_branch(self, opcode, handler):
        self.branchtable[opcode] = handler

    def jeq(self):
        if self.fl == 1:
            self.jmp()
        else:
            self.pc += self.increment(JMP)

    def jne(self):
        if self.fl != 1:
            self.jmp()
        else:
            self.pc += self.increment(JNE)

    def jmp(self):
        self.pc = self.reg[self.ram_read(self.pc + 1)]

    def call(self):
        self.reg[SP] -= 1
        self.ram_write(self.reg[SP], self.pc + 2)
        num = self.ram_read(self.pc + 1)
        self.pc = self.reg[num]

    def ret(self):
        self.pc = self.ram_read(self.reg[SP])
        self.reg[SP] += 1

    def pop(self):
        reg_index = self.ram_read(self.pc + 1)
        num = self.ram_read(self.reg[SP])
        self.reg[reg_index] = num
        self.reg[SP] += 1

    def push(self):
        reg_index = self.ram_read(self.pc + 1)
        num = self.reg[reg_index]
        self.reg[SP] -= 1
        self.ram_write(self.reg[SP], num)

    def halt(self):
        return True

    def ldi(self):
        reg_index = self.ram_read(self.pc + 1)
        num = self.ram_read(self.pc + 2)
        self.reg[reg_index] = num

    def prn(self):
        reg_index = self.ram_read(self.pc + 1)
        print(self.reg[reg_index])

    def nop(self):
        pass

    def run_alu(self, opcode):
        return self.alu.run(opcode, self.ram_read(self.pc + 1),
                            self.ram_read(self.pc + 2))

    def load(self, file):
        """Load a program into memory."""
        address = 0
        program = []

        with open(file) as f:
            for line in f:
                line = line.partition('#')[0]
                line = line.rstrip()
                if line:
                    program.append(int(str.encode(line), 2))

        for instruction in program:
            self.ram[address] = instruction
            address += 1

    def ram_read(self, index):
        return self.ram[index]

    def ram_write(self, index, num):
        self.ram[index] = num

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.pc,
            # self.fl,
            # self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

        print()

    def sets_pc(self, opcode):
        return (opcode >> 4 & 1)

    def increment(self, opcode):
        return (opcode >> 6 & 0b11) + 1

    def run(self):
        """Run the CPU."""
        stop = False
        self.pc = 0
        while not stop:
            command = self.ram_read(self.pc)
            if command in self.alu_ops:
                stop = self.run_alu(command)
            elif command in self.branchtable:
                stop = self.branchtable[command]()
            else:
                print(f"Unknown instruction: {command}")
                sys.exit(1)
            if not self.sets_pc(command):
                self.pc += self.increment(command)
