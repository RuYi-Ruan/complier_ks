import re


def parse_quads(quads_file):
    quads = []
    pattern = r"^(\d+): \(([^,]+), ([^,]+), ([^,]+), ([^\)]+)\)"
    with open(quads_file, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(pattern, line.strip())
            if m:
                idx, op, a1, a2, res = m.groups()
                quads.append((int(idx), op, a1.strip(), a2.strip(), res.strip()))
    return quads


class CodeGenerator8086:
    def __init__(self, quads):
        self.quads = quads
        self.var_offsets = {}
        self.next_offset = 2  # bp-2 for first var
        self.labels = {}
        self.code = []
        self.temp_prefix = 't'

    def alloc(self, name):
        if name not in self.var_offsets:
            self.var_offsets[name] = self.next_offset
            self.next_offset += 2
        return self.var_offsets[name]

    def label_for(self, idx):
        label = f"L{idx}"
        self.labels[idx] = label
        return label

    def emit(self, instr):
        self.code.append(instr)

    def generate(self):
        # Emit function prologue for main
        self.emit('main:')
        self.emit('    push bp')
        self.emit('    mov bp, sp')
        # reserve space
        total = len(self.quads) * 2  # rough, adjust later
        self.emit(f'    sub sp, {self.next_offset}')

        # scan for labels
        for idx, op, a1, a2, res in self.quads:
            if op.startswith('j') or op == 'jmp':
                self.labels[idx] = f"L{idx}"

        # generate code
        for idx, op, a1, a2, res in self.quads:
            # label
            if idx in self.labels:
                self.emit(f'{self.labels[idx]}:')
            if op == '=':
                # (=, a1, -, res)
                offset = self.alloc(res)
                if a1.isdigit():
                    self.emit(f'    mov ax, {a1}')
                else:
                    off1 = self.alloc(a1)
                    self.emit(f'    mov ax, [bp-{off1}]')
                self.emit(f'    mov [bp-{offset}], ax')
            elif op in ['+', '-', '*', '/']:
                off1 = self.alloc(a1)
                self.emit(f'    mov ax, [bp-{off1}]')
                if a2.isdigit():
                    self.emit(f'    {"add" if op == "+" else op} ax, {a2}')
                else:
                    off2 = self.alloc(a2)
                    self.emit(f'    {"add" if op == "+" else op} ax, [bp-{off2}]')
                offr = self.alloc(res)
                self.emit(f'    mov [bp-{offr}], ax')
            elif op.startswith('j') and op != 'jmp':
                # relational jump
                cond = op[1:]
                off1 = self.alloc(a1)
                if a2.isdigit():
                    self.emit(f'    mov ax, [bp-{off1}]')
                    self.emit(f'    cmp ax, {a2}')
                else:
                    off2 = self.alloc(a2)
                    self.emit(f'    mov ax, [bp-{off1}]')
                    self.emit(f'    cmp ax, [bp-{off2}]')
                target = self.label_for(int(res))
                jmp_instr = {
                    '<': 'jl', '>': 'jg', '<=': 'jle', '>=': 'jge', '==': 'je', '!=': 'jne'
                }[cond]
                self.emit(f'    {jmp_instr} {target}')
            elif op == 'jmp':
                target = self.label_for(int(res))
                self.emit(f'    jmp {target}')
            elif op == 'call':
                # assume return in ax
                # args already pushed
                self.emit(f'    call {a1}')
                # clean up
                n = int(a2)
                if n > 0:
                    self.emit(f'    add sp, {2 * n}')
                offr = self.alloc(res)
                self.emit(f'    mov [bp-{offr}], ax')
            elif op == 'param':
                # param a1
                off1 = self.alloc(a1)
                self.emit(f'    push word ptr [bp-{off1}]')
            elif op == 'return':
                if a1 != '-':
                    off1 = self.alloc(a1)
                    self.emit(f'    mov ax, [bp-{off1}]')
                self.emit('    mov sp, bp')
                self.emit('    pop bp')
                self.emit('    ret')
            elif op == 'sys':
                self.emit('    mov ax, 4C00h')
                self.emit('    int 21h')
        return '\n'.join(self.code)


if __name__ == '__main__':
    quads = parse_quads('./output/quads.txt')
    cg = CodeGenerator8086(quads)
    asm = cg.generate()
    with open('./output/output.asm', 'w') as f:
        f.write('DATA segment\n')
        f.write('DATA ends\n')
        f.write('CODE segment\n')
        f.write(asm)
        f.write('\nCODE ends\nend main')
