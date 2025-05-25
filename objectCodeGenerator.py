import json
from collections import defaultdict


def process_quads(file_path='./output/quads.txt'):
    inter_table = []
    temp_map = {}  # 用于映射 tN -> TN
    temp_counter = 1  # 从 T1 开始编号

    def get_temp(val):
        nonlocal temp_counter
        if isinstance(val, str) and val.startswith('t'):
            if val not in temp_map:
                temp_map[val] = f'T{temp_counter}'
                temp_counter += 1
            return temp_map[val]
        return val

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or ':' not in line:
                continue
            try:
                # 提取数字标签，生成 label 四元式
                lineno, content = line.split(':', 1)
                lineno = lineno.strip()
                inter_table.append(['label', '_', '_', lineno])

                # 处理四元式
                content = content.strip().strip('()')
                parts = [p.strip() for p in content.split(',')]
                parts = [get_temp(p) if p != '_' else '_' for p in parts]
                inter_table.append(parts)
            except Exception as e:
                print(f"Error parsing line: {line}\n{e}")

    return inter_table


class TargetCodeGenerator:
    def __init__(self, symtab_path='./output/symbol_table.json'):
        self.data_segment = set()
        self.temp_vars = set()
        self.output = []

        # 记录函数名和全局变量
        self.functions = set()
        self.variables = set()
        self._load_symbol_table(symtab_path)

        # 新增：从四元式收集的参数列表
        self.func_params = defaultdict(list)
        self.pending_call = None
        self.pending_count = 0

        self.current_function = None

        self.last_label = None

        self.pending_res = None

    def _load_symbol_table(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            symtab = json.load(f)
        for func in symtab.get('functions', []):
            if func.get('is_defined', False):
                self.functions.add(func['name'])
        for var in symtab.get('variables', []):
            self.variables.add(var['name'])

    def add_header(self):
        self.output.extend([
            'assume cs:code,ds:data,ss:stack,es:extended',
            '',
            'extended segment',
            '    db 1024 dup (0)',
            'extended ends',
            '',
            'stack segment',
            '    db 1024 dup (0)',
            'stack ends',
            '',
            'data segment',
            '    _buff_p db 256 dup (24h)',
            '    _buff_s db 256 dup (0)',
            "    _msg_p db 0ah, 'Output:', 0",
            "    _msg_s db 0ah, 'Input:', 0"
        ])
        for var in sorted(self.data_segment | self.temp_vars):
            self.output.append(f'    _{var} dw 0')
        self.output.append('data ends\n')

    def add_init_code(self):
        self.output.extend([
            'code segment',
            'start:',
            '    mov ax,extended',
            '    mov es,ax',
            '    mov ax,stack',
            '    mov ss,ax',
            '    mov sp,1024',
            '    mov bp,sp',
            '    mov ax,data',
            '    mov ds,ax',
            '    jmp F_main',
            ''
        ])

    def gen_quad(self, quad):
        op, arg1, arg2, res = quad

        if op == 'label':
            # 先输出 L<line>:
            self.last_label = res
            self.output.append(f'L{res}:')
            return

        # 1) 如果是函数定义四元式 (op 为函数名, arg1/arg2/res 都是 '_')
        if op in self.functions and arg1 == arg2 == res == '_':
            # 函数入口
            self.current_function = op
            self.output.append(f'F_{op}:')  # 再输出F_标签
            self.output.append('    push bp')
            self.output.append('    mov bp, sp')
            # 恢复从前面 para 收集到的参数
            params = self.func_params.get(op, [])
            for idx, pname in enumerate(params):
                offset = 4 + (len(params) - idx - 1) * 2
                self.data_segment.add(pname)
                self.output.append(f'    mov ax, ss:[bp+{offset}]')
                self.output.append(f'    mov ds:[_{pname}], ax')
            return

        # 2) 收集并生成 para/push
        if op == 'para':
            self.output.append(f'    mov ax, {self._val(arg1)}')
            self.output.append('    push ax')
            return

        if op == 'call' and arg1 not in ('read', 'write'):
            self.output.append(f'    call F_{arg1}')
            self.data_segment.add(res)
            self.output.append(f'    mov word ptr ds:[_{res}], ax')
            if arg2.isdigit() and int(arg2) > 0:
                self.output.append(f'    add sp, {int(arg2) * 2}')
            return

        # 赋值
        if op == '=':
            self.data_segment.add(res)
            self.output.append(f'    mov ax, {self._val(arg1)}')
            self.output.append(f'    mov {self._val(res)}, ax')
            return

        # 四则运算
        if op in ['+', '-', '*', '/']:
            self.temp_vars.add(res)
            if op == '+':
                if self.current_function == 'add':
                    # 在 add 函数中，直接使用栈上的参数
                    self.output.append('    mov ax, ss:[bp+6]')  # 第二个参数
                    self.output.append('    add ax, ss:[bp+4]')  # 第一个参数
                else:
                    self.output.append(f'    mov ax, {self._val(arg1)}')
                    self.output.append(f'    add ax, {self._val(arg2)}')
            elif op == '-':
                self.output.append(f'    mov ax, {self._val(arg1)}')
                self.output.append(f'    sub ax, {self._val(arg2)}')
            elif op == '*':
                self.output.append(f'    mov ax, {self._val(arg1)}')
                self.output.append('    imul word ptr ds:[_' + arg2 + ']')
            elif op == '/':
                self.output.append(f'    mov ax, {self._val(arg1)}')
                self.output.append('    cwd')
                self.output.append(f'    idiv {self._val(arg2)}')
            self.output.append(f'    mov {self._val(res)}, ax')
            return

        # 系统读写调用
        if op == 'call':
            if arg1 == 'read':
                self.output.append('    call _read')
                self.output.append(f'    mov {self._val(res)}, ax')
                if arg2.isdigit(): self.output.append(f'    add sp, {int(arg2) * 2}')
            elif arg1 == 'write':
                self.output.append('    call _write')
                if arg2.isdigit(): self.output.append(f'    add sp, {int(arg2) * 2}')
            return

        # 条件跳转
        if op in ['j<', 'j<=', 'j>', 'j>=', 'j==', 'j!=']:
            targets = {'j<': 'jl', 'j<=': 'jle', 'j>': 'jg', 'j>=': 'jge', 'j==': 'je', 'j!=': 'jne'}
            self.output.append(f'    mov ax, {self._val(arg1)}')
            self.output.append(f'    cmp ax, {self._val(arg2)}')
            self.output.append(f'    {targets[op]} L{res}')
            return

        # 无条件跳转
        if op == 'j':
            self.output.append(f'    jmp L{res}')
            return

        # 返回
        if op == 'ret':
            if arg1 and arg1 != '_':
                self.output.append(f'    mov ax, {self._val(arg1)}')
            self.output.append('    mov sp, bp')
            self.output.append('    pop bp')
            if self.current_function != 'main':
                self.output.append('    ret')
            else:
                self.output.append('    mov ah,4ch')
                self.output.append('    int 21h')
            return

        # 系统退出
        if op == 'sys' and self.current_function == 'main':
            self.output.append('    mov ah,4ch')
            self.output.append('    int 21h')
            return

        # 标签
        if op == 'label':
            self.output.append(f'L{res}:')

    def _val(self, v):
        if isinstance(v, (int,)) or (isinstance(v, str) and v.isdigit()):
            return str(v)
        return f'word ptr ds:[_{v}]'

    def add_library(self):
        self.output.extend([
            '\n; ----------------- READ PROCEDURE -----------------',
            '_read:',
            '    push bp',
            '    mov bp,sp',
            '    mov bx,offset _msg_s',
            '    call _print',
            '    mov bx,offset _buff_s',
            '    mov di,0',
            '_r_lp_1:',
            '    mov ah,1',
            '    int 21h',
            '    cmp al,0dh',
            '    je _r_brk_1',
            '    mov ds:[bx+di],al',
            '    inc di',
            '    jmp short _r_lp_1',
            '_r_brk_1:',
            '    mov ah,2',
            '    mov dl,0ah',
            '    int 21h',
            '    mov ax,0',
            '    mov si,0',
            '    mov cx,10',
            '_r_lp_2:',
            '    mov dl,ds:[bx+si]',
            '    cmp dl,30h',
            '    jb _r_brk_2',
            '    cmp dl,39h',
            '    ja _r_brk_2',
            '    sub dl,30h',
            '    mov ds:[bx+si],dl',
            '    mul cx',
            '    mov dl,ds:[bx+si]',
            '    mov dh,0',
            '    add ax,dx',
            '    inc si',
            '    jmp short _r_lp_2',
            '_r_brk_2:',
            '    mov cx,di',
            '    mov si,0',
            '_r_lp_3:',
            '    mov byte ptr ds:[bx+si],0',
            '    loop _r_lp_3',
            '    mov sp,bp',
            '    pop bp',
            '    ret',
            '',
            '; ----------------- WRITE PROCEDURE -----------------',
            '_write:',
            '    push bp',
            '    mov bp,sp',
            '    mov bx,offset _msg_p',
            '    call _print',
            '    mov ax,ss:[bp+4]',
            '    mov bx,10',
            '    mov cx,0',
            '_w_lp_1:',
            '    mov dx,0',
            '    div bx',
            '    push dx',
            '    inc cx',
            '    cmp ax,0',
            '    jne _w_lp_1',
            '    mov di,offset _buff_p',
            '_w_lp_2:',
            '    pop ax',
            '    add ax,30h',
            '    mov ds:[di],al',
            '    inc di',
            '    loop _w_lp_2',
            '    mov dx,offset _buff_p',
            '    mov ah,09h',
            '    int 21h',
            '    mov cx,di',
            '    sub cx,offset _buff_p',
            '    mov di,offset _buff_p',
            '_w_lp_3:',
            '    mov al,24h',
            '    mov ds:[di],al',
            '    inc di',
            '    loop _w_lp_3',
            '    mov ax,di',
            '    sub ax,offset _buff_p',
            '    mov sp,bp',
            '    pop bp',
            '    ret 2',
            '',
            '; ----------------- PRINT FUNCTION -----------------',
            '_print:',
            '    mov si,0',
            '    mov di,offset _buff_p',
            '_p_lp_1:',
            '    mov al,ds:[bx+si]',
            '    cmp al,0',
            '    je _p_brk_1',
            '    mov ds:[di],al',
            '    inc si',
            '    inc di',
            '    jmp short _p_lp_1',
            '_p_brk_1:',
            '    mov dx,offset _buff_p',
            '    mov ah,09h',
            '    int 21h',
            '    mov cx,si',
            '    mov di,offset _buff_p',
            '_p_lp_2:',
            '    mov al,24h',
            '    mov ds:[di],al',
            '    inc di',
            '    loop _p_lp_2',
            '    ret',
            '    mov ah,4ch',
            '    int 21h'
        ])

    def add_footer(self):
        self.output.append('code ends')
        self.output.append('end start')

    def generate(self, quads):
        # 先收集所有全局变量和临时变量
        for v in self.variables:
            self.data_segment.add(v)
        for op, a1, a2, res in quads:
            if isinstance(res, str) and res.startswith('T'):
                self.temp_vars.add(res)

        # 生成代码各部分
        self.add_header()
        self.add_init_code()
        for quad in quads:
            self.gen_quad(quad)
        self.add_library()
        self.add_footer()

    def save_to_file(self, file_path='./output/object_code.asm'):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.output))


if __name__ == '__main__':
    inter_table = process_quads()
    generator = TargetCodeGenerator()
    generator.generate(inter_table)
    generator.save_to_file()
