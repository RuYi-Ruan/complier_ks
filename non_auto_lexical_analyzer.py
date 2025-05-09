import copy
from typing import List, Tuple
from practice.tokenType import SymbolTable, SymbolEntry, TokenType, TokenCategory


class Lexer:
    def __init__(self):
        self.symbol_table = SymbolTable()  # 用于存储和管理词法单元
        self.current_line = 1             # 当前处理的行号
        self.current_col = 1              # 当前处理的列号
        self.tokens: List[SymbolEntry] = []  # 存放识别出的有效 token
        self.errors: List[SymbolEntry] = []  # 存放识别过程中出现的错误 token

        # 允许出现在运算符中的字符集合和合法运算符列表
        self.allowed_operator_chars = set("+-*/%=&|^<>!~")
        self.allowed_operators = {
            "++", "--", "->", "<<", ">>", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "%=",
            "&&", "||", "<<=", ">>=", "+", "-", "*", "/", "%", "=", "&", "|", "^", "<", ">", "!", "~"
        }
        # 运算符映射：将运算符字符串映射到TokenType中的具体成员
        self.operator_mapping = {
            "++": TokenType.INCREMENT,
            "--": TokenType.DECREMENT,
            "->": TokenType.POINTER,
            "<<": TokenType.SHIFT_LEFT,
            ">>": TokenType.SHIFT_RIGHT,
            "<=": TokenType.LE,
            ">=": TokenType.GE,
            "==": TokenType.EQ,
            "!=": TokenType.NE,
            "+=": TokenType.ADD_ASSIGN,
            "-=": TokenType.SUB_ASSIGN,
            "*=": TokenType.MUL_ASSIGN,
            "/=": TokenType.DIV_ASSIGN,
            "%=": TokenType.MOD_ASSIGN,
            "&&": TokenType.AND,
            "||": TokenType.OR,
            "<<=": TokenType.SHIFT_LEFT_ASSIGN,
            ">>=": TokenType.SHIFT_RIGHT_ASSIGN,
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.DIV,
            "%": TokenType.MOD,
            "=": TokenType.ASSIGN,
            "&": TokenType.AMPERSAND,
            "|": TokenType.BITWISE_OR,
            "^": TokenType.BITWISE_XOR,
            "!": TokenType.NOT,
            "~": TokenType.BITWISE_NOT,
            "<": TokenType.LT,
            ">": TokenType.GT,
        }
        # 分隔符映射：将分隔符字符映射到TokenType中相应的具体类型
        self.delimiter_mapping = {
            '{': TokenType.LEFT_BRACE,
            '}': TokenType.RIGHT_BRACE,
            '(': TokenType.LEFT_PAREN,
            ')': TokenType.RIGHT_PAREN,
            '[': TokenType.LEFT_BRACKET,
            ']': TokenType.RIGHT_BRACKET,
            ',': TokenType.COMMA,
            ';': TokenType.SEMICOLON,
        }
        # 分隔符字符集合
        self.delimiters = set(self.delimiter_mapping.keys())
        # 允许的预处理指令集合
        self.allowed_directives = {'include', 'define', 'undef', 'ifdef', 'ifndef', 'endif', 'pragma'}

    def _read_until_break(self, code: str, i: int, n: int) -> Tuple[str, int]:
        """
        辅助函数：从索引 i 开始，读取连续的字符，
        直到遇到空白字符（空格、制表符、换行）或注释起始标志（'//' 或 '/*'）时停止读取。
        返回读取的子串和新的索引值。
        """
        lex = ""
        while i < n:
            # 如果遇到空白字符，则停止读取
            if code[i].isspace():
                break
            # 如果遇到注释的起始标志，则停止读取
            if code[i] == '/' and i + 1 < n and (code[i + 1] == '/' or code[i + 1] == '*'):
                break
            lex += code[i]
            i += 1
        return lex, i

    def tokenize(self, code: str) -> Tuple[List[SymbolEntry], List[SymbolEntry]]:
        # 分隔符匹配用的栈，存储元组 (左分隔符字符, 在 tokens 列表中的索引)
        delimiter_stack = []
        # 定义分组左分隔符和右分隔符集合
        group_openings = {'{', '[', '('}
        group_closings = {'}', ']', ')'}
        # 定义左分隔符对应的匹配右分隔符
        matching = {'{': '}', '[': ']', '(': ')'}

        i = 0
        n = len(code)
        while i < n:
            ch = code[i]
            start_line = self.current_line
            start_col = self.current_col

            # 处理空格和制表符
            if ch in ' \t':
                i += 1
                self.current_col += 1
                continue

            # 处理换行符
            if ch == '\n':
                i += 1
                self.current_line += 1
                self.current_col = 1
                continue

            # 处理单行注释（以 // 开头）
            if ch == '/' and i + 1 < n and code[i + 1] == '/':
                i += 2
                self.current_col += 2
                while i < n and code[i] != '\n':
                    i += 1
                    self.current_col += 1
                continue

            # 处理多行注释（以 /* 开始，以 */ 结束）
            if ch == '/' and i + 1 < n and code[i + 1] == '*':
                start_comment_line = self.current_line
                start_comment_col = self.current_col
                lexeme = code[i:i + 2]  # 保存 "/*"
                i += 2
                self.current_col += 2
                closed = False
                while i < n:
                    if code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        lexeme += "*/"
                        i += 2
                        self.current_col += 2
                        closed = True
                        break
                    if code[i] == '\n':
                        lexeme += '\n'
                        i += 1
                        self.current_line += 1
                        self.current_col = 1
                    else:
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                if not closed:
                    entry = SymbolEntry(
                        lexeme, TokenType.ERROR,
                        line=start_comment_line, column=start_comment_col,
                        error_msg="注释未闭合"
                    )
                    self.errors.append(entry)
                continue

            # 处理字符串字面量（以双引号开始和结束）
            if ch == '"':
                lexeme = ch
                i += 1
                self.current_col += 1
                closed = False
                while i < n:
                    if code[i] == '"' and (len(lexeme) == 1 or lexeme[-1] != '\\'):
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                        closed = True
                        break
                    if code[i] == '\n':
                        break
                    lexeme += code[i]
                    i += 1
                    self.current_col += 1
                entry = self.symbol_table.process_string_literal(lexeme, start_line, start_col)
                if entry.token_type == TokenType.ERROR:
                    self.errors.append(entry)
                else:
                    self.tokens.append(entry)
                continue

            # 处理字符字面量（以单引号开始和结束）
            if ch == "'":
                lexeme = ch
                i += 1
                self.current_col += 1
                closed = False
                while i < n:
                    if code[i] == "'" and (len(lexeme) == 1 or lexeme[-1] != '\\'):
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                        closed = True
                        break
                    if code[i] == '\n':
                        break
                    lexeme += code[i]
                    i += 1
                    self.current_col += 1
                entry = self.symbol_table.process_char_literal(lexeme, start_line, start_col)
                if entry.token_type == TokenType.ERROR:
                    self.errors.append(entry)
                else:
                    self.tokens.append(entry)
                continue

            # 处理数字（包括整型和浮点型）
            if ch.isdigit():
                lexeme = ""
                if ch in '+-':
                    lexeme += ch
                    i += 1
                    self.current_col += 1
                    if i >= n or not code[i].isdigit():
                        entry = SymbolEntry(
                            lexeme, TokenType.ERROR,
                            line=start_line, column=start_col,
                            error_msg="非法数字"
                        )
                        self.errors.append(entry)
                        continue
                # 判断是否为十六进制、二进制或八进制数
                if i + 1 < n and code[i] == '0' and code[i + 1] in 'xXbBoO':
                    lexeme += code[i] + code[i + 1]
                    i += 2
                    self.current_col += 2
                    while i < n and code[i].isalnum():
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                else:
                    # 检测是否有连续的小数点
                    dot_encountered = False
                    while i < n:
                        c = code[i]
                        if c.isdigit():
                            lexeme += c
                            i += 1
                            self.current_col += 1
                        elif c == '.':
                            if dot_encountered:
                                # 遇到第二个小数点后，调用封装函数，读取后续字符（直到遇到空白或注释）
                                extra, i = self._read_until_break(code, i, n)
                                lexeme += extra
                                self.current_col += len(extra)
                                break
                            dot_encountered = True
                            lexeme += c
                            i += 1
                            self.current_col += 1
                        elif c in 'eE':
                            lexeme += c
                            i += 1
                            self.current_col += 1
                            if i < n and code[i] in '+-':
                                lexeme += code[i]
                                i += 1
                                self.current_col += 1
                            while i < n and code[i].isdigit():
                                lexeme += code[i]
                                i += 1
                                self.current_col += 1
                            break
                        else:
                            break
                entry = self.symbol_table.process_constant(lexeme, start_line, start_col)
                if entry.token_type == TokenType.ERROR:
                    self.errors.append(entry)
                else:
                    self.tokens.append(entry)
                continue

            # 处理标识符(是否以字母和下划线开头)和关键字
            if ch.isalpha() or ch == '_':
                lexeme = ""
                # 获取完整词素
                while i < n and (code[i].isalnum() or code[i] == '_'):
                    lexeme += code[i]
                    i += 1
                    self.current_col += 1
                # 查找是否为关键字（在符号表中已经预置了关键字）
                sym = self.symbol_table.lookup(lexeme)
                if sym:
                    entry = SymbolEntry(lexeme, sym.token_type, line=start_line, column=start_col)
                else:
                    entry = SymbolEntry(lexeme, TokenType.IDENTIFIER, line=start_line, column=start_col)
                self.tokens.append(entry)
                continue

            # 处理运算符
            if ch in self.allowed_operator_chars:
                # 从当前位置开始，取出所有连续的运算符字符
                j = i
                while j < n and code[j] in self.allowed_operator_chars:
                    j += 1
                op_seq = code[i:j]  # 得到连续的运算符字符串
                # 判断整个连续字符串是否为合法的运算符
                if op_seq in self.allowed_operators:
                    lexeme = op_seq
                    i = j  # 更新索引到连续运算符之后
                    self.current_col += len(lexeme)  # 更新当前列号
                    token_type = self.operator_mapping.get(lexeme, TokenType.ASSIGN)
                    entry = SymbolEntry(lexeme, token_type, line=start_line, column=start_col)
                    self.tokens.append(entry)
                else:
                    lexeme = op_seq
                    i = j  # 更新索引到连续运算符之后
                    self.current_col += len(lexeme)
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=start_line, column=start_col,
                                        error_msg="非法运算符")
                    self.errors.append(entry)
                continue

            # 处理分隔符
            if ch in self.delimiters:
                # —— 1. 左分组符 入栈 ——
                if ch in group_openings:
                    token_type = self.delimiter_mapping[ch]
                    entry = SymbolEntry(ch, token_type,
                                        line=start_line, column=start_col)
                    self.tokens.append(entry)
                    delimiter_stack.append((ch, len(self.tokens) - 1))
                # —— 2. 右分组符 —— 尝试配对
                elif ch in group_closings:
                    # 首先弹出所有不能匹配当前右分组符的“未闭合左符号”
                    while delimiter_stack and matching[delimiter_stack[-1][0]] != ch:
                        open_char, open_idx = delimiter_stack.pop()
                        # 进行深拷贝，避免修改影响到tokens中的元素
                        tok_err = copy.deepcopy(self.tokens[open_idx])
                        tok_err.token_type = TokenType.ERROR
                        tok_err.error_msg = "未闭合的分隔符"
                        self.errors.append(tok_err)
                    # 如果找到匹配的左分组符，就正常将它出栈；否则当前右分组符报错
                    if delimiter_stack and matching[delimiter_stack[-1][0]] == ch:
                        delimiter_stack.pop()
                        token_type = self.delimiter_mapping[ch]
                        entry = SymbolEntry(ch, token_type,
                                            line=start_line, column=start_col)
                        self.tokens.append(entry)
                    else:
                        entry = SymbolEntry(ch, TokenType.ERROR,
                                            line=start_line, column=start_col,
                                            error_msg="未匹配的右分隔符")
                        self.errors.append(entry)
                # —— 3. 普通分隔符 —— 直接入 tokens
                else:
                    # 这里处理 ; , 等
                    token_type = self.delimiter_mapping[ch]
                    entry = SymbolEntry(ch, token_type,
                                        line=start_line, column=start_col)
                    self.tokens.append(entry)

                i += 1
                self.current_col += 1
                continue


            # 处理预处理指令（以 '#' 开始）
            if ch == '#':
                start_line = self.current_line
                start_col = self.current_col
                lexeme = "#"  # 预处理指令的词素以 '#' 开始
                i += 1
                self.current_col += 1

                # 调用封装的辅助函数读取预处理指令的关键字部分
                extra, i = self._read_until_break(code, i, n)
                lexeme += extra
                self.current_col += len(extra)

                # 取出 '#' 后面连续的字母作为关键字
                raw = lexeme[1:]
                directive_word = ""

                for c in raw:
                    if c.isalpha():
                        directive_word += c
                    else:
                        break

                if directive_word not in self.allowed_directives:
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=start_line, column=start_col,
                                        error_msg="非法预处理指令")
                    self.errors.append(entry)
                else:
                    entry = SymbolEntry(lexeme, TokenType.PREPROCESSOR, line=start_line, column=start_col)
                    self.tokens.append(entry)
                continue

            # 其它字符，视为错误
            entry = SymbolEntry(ch, TokenType.ERROR, line=start_line, column=start_col,
                                error_msg="非法字符")
            self.errors.append(entry)
            i += 1
            self.current_col += 1

        # 遍历栈中剩余未匹配的左分隔符，标记为错误
        for open_char, token_index in delimiter_stack:
            # 更新对应 token 为错误状态
            token = self.tokens[token_index]
            token.token_type = TokenType.ERROR
            token.error_msg = "未闭合的分隔符"
            # 同时记录到错误列表中
            self.errors.append(token)

        return self.tokens, self.errors


# ---------------------------
# 示例调用及测试
# ---------------------------
if __name__ == "__main__":
    code_sample = r'''i+1'''
    lexer = Lexer()
    tokens, errors = lexer.tokenize(code_sample)
    print("Tokens:")
    for token in tokens:
        print(f"{token.line}:{token.column} '{token.lexeme}' -> {token.token_type.category.value}")
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"{error.line}:{error.column} '{error.lexeme}' -> {error.error_msg}")
