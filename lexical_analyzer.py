import re
from enum import Enum
from dataclasses import dataclass
from typing import Union, Optional, Tuple, List
import logging

# 错误信息
INVALID_NUMBER = "无效整数"
UNCLOSED_STRING = "未闭合字符串"
UNCLOSED_CHAR = "未闭合字符"
INVALID_IDENTIFIER = "无效标识符"
UNKNOWN_TOKEN = "无效词素"

# 定义 Token 类型的枚举类
class TokenType(Enum):
    KEYWORD = (0, "KEYWORD")  # 关键字（如 int, return）
    IDENTIFIER = (1, "IDENTIFIER")  # 标识符（变量名、函数名等）
    INT_CONSTANT = (2, "INT_CONST")  # 整型常量（如 123, 0x1A）
    FLOAT_CONSTANT = (3, "FLOAT_CONST")  # 浮点常量（如 3.14, 1e10）
    STRING_LITERAL = (4, "STR_LITERAL")  # 字符串字面量（如 "hello"）
    OPERATOR = (5, "OPERATOR")  # 运算符（如 +, -, *=）
    DELIMITER = (6, "DELIMITER")  # 界符（如 {, }, ;）
    ERROR = (7, "ERROR")  # 错误标记（不符合语法的符号）

    def __new__(cls, code, display):
        obj = object.__new__(cls)
        obj._value_ = code  # 将枚举的值设置为 reference
        obj.code = code
        obj.display = display
        return obj

    @property
    def type_code(self):
        return self.code

    @property
    def type_name(self):
        return self.display


# 符号表条目数据结构，存储词法单元信息
@dataclass
class SymbolEntry:
    lexeme: str              # 词素（具体的字符串内容）
    token_type: TokenType    # 词法单元的类型
    value: Union[int, float, str, None] = None  # 存储的值（用于常量）
    line: int = 0            # 行号
    column: int = 0          # 列号
    error_msg: Optional[str] = None  # 错误说明（当 token_type 为 ERROR 时使用）


class SymbolTable:
    def __init__(self, size=1024, parent=None):
        """
        初始化符号表，默认大小为 1024，并支持作用域链（父作用域）。
        使用哈希桶数组存储符号条目。
        """
        self.size = size
        self.table = [[] for _ in range(size)]  # 创建哈希桶数组，每个桶是一个列表
        self.parent = parent  # 记录父作用域，用于作用域链查找
        self._init_keywords()  # 预加载 C 语言关键字

    def _init_keywords(self):
        """预先将 C 语言的关键字插入符号表，方便后续词法分析。"""
        keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue',
            'default', 'do', 'double', 'else', 'enum', 'extern',
            'float', 'for', 'goto', 'if', 'int', 'long', 'register',
            'return', 'short', 'signed', 'sizeof', 'static', 'struct',
            'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while'
        ]
        for kw in keywords:
            self.insert(SymbolEntry(
                lexeme=kw,
                token_type=TokenType.KEYWORD,
                line=0,
                column=0
            ))

    def _hash(self, lexeme: str) -> int:
        """
        计算字符串的哈希值，使用 FNV-1a 哈希算法。
        该算法在编译器和散列数据结构中常用于高效的字符串哈希计算。
        """
        hash_val = 2166136261  # 初始哈希值
        for char in lexeme.encode('utf-8'):  # 逐字节处理字符串
            hash_val ^= char  # 进行异或运算
            hash_val *= 16777619  # 乘上一个大素数，提高哈希分布均匀性
        return hash_val % self.size  # 取模保证哈希值在符号表范围内

    def insert(self, entry: SymbolEntry) -> None:
        """
        将符号插入符号表，如果已存在则更新。
        使用头插法（插入到列表开头）提高插入效率。
        """
        index = self._hash(entry.lexeme)  # 计算哈希索引
        bucket = self.table[index]  # 获取哈希桶

        # 检查是否已有该符号
        for existing in bucket:
            if existing.lexeme == entry.lexeme:
                # 如果符号已存在，则更新其 token 类型和值
                existing.token_type = entry.token_type
                existing.value = entry.value
                return

        # 若符号不存在，则插入新条目
        self.table[index].insert(0, entry)

    def lookup(self, lexeme: str) -> Optional[SymbolEntry]:
        """
        查找符号是否存在，若当前作用域找不到，则递归查找父作用域。
        """
        index = self._hash(lexeme)  # 计算哈希索引
        for entry in self.table[index]:  # 遍历哈希桶
            if entry.lexeme == lexeme:
                return entry  # 找到并返回符号信息

        # 如果当前作用域没有该符号，继续在父作用域中查找
        if self.parent:
            return self.parent.lookup(lexeme)

        return None  # 找不到返回 None

    def process_constant(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理整数和浮点数常量，自动识别数据类型，并插入符号表。
        如果格式非法，则标记为错误。
        """
        valid_float = r'^[+\-]?(?:\d+\.\d+|\.\d+)(?:[eE][+\-]?\d+)?$'
        valid_int = r'^[+\-]?(0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|[1-9]\d*|0)$'

        if re.fullmatch(valid_float, lexeme):
            try:
                value = float(lexeme)
                entry = SymbolEntry(lexeme, TokenType.FLOAT_CONSTANT, value, line, col)
            except (ValueError, OverflowError):
                entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)
        elif re.fullmatch(valid_int, lexeme):
            try:
                if lexeme.startswith(('0x', '0X')):
                    base = 16
                elif lexeme.startswith(('0b', '0B')):
                    base = 2
                elif lexeme.startswith(('0o', '0O')):
                    base = 8
                else:
                    base = 10
                value = int(lexeme, base)
                entry = SymbolEntry(lexeme, TokenType.INT_CONSTANT, value, line, col)
            except (ValueError, OverflowError):
                entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)
        else:
            # 整体不符合合法格式，直接标记为 ERROR，而不是拆分
            entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)

        self.insert(entry)
        return entry

    def process_string_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理字符串字面量，检测格式是否正确，并解析转义字符。
        """
        # 检查字符串是否以双引号开头和结尾
        if len(lexeme) < 2 or not (lexeme.startswith('"') and lexeme.endswith('"')):
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)

        try:
            # 检测非法转义字符（例如 \q、\y）
            if re.search(r'\\[^ntbrf\'"\\xuU]', lexeme):  # 仅允许合法转义字符
                return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)

            # 解析合法转义字符
            processed = bytes(lexeme[1:-1], 'utf-8').decode('unicode_escape')

            return SymbolEntry(lexeme, TokenType.STRING_LITERAL, processed, line, col)

        except UnicodeDecodeError:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)  # 处理解码错误

    def process_char_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理字符字面量，检测格式是否正确，并解析转义字符。
        """
        # 检查字符是否以单引号开头和结尾，并且长度为3（如 'a'）或4（如 '\n'）
        if len(lexeme) < 3 or not (lexeme.startswith("'") and lexeme.endswith("'")):
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)

        char_content = lexeme[1:-1]
        # 处理转义字符
        if len(char_content) == 1:
            # 普通字符，如 'a'
            value = char_content
        elif char_content.startswith('\\'):
            # 转义字符，如 '\n', '\\'
            try:
                value = bytes(char_content, 'utf-8').decode('unicode_escape')
                if len(value) != 1:
                    raise ValueError
            except (UnicodeDecodeError, ValueError):
                return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)
        else:
            # 非法字符字面量，如 'ab'
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col)

        return SymbolEntry(lexeme, TokenType.INT_CONSTANT, ord(value), line, col)


class Lexer:
    def __init__(self):
        # 初始化词法分析器对象
        self.symbol_table = SymbolTable()  # 用于存储符号表
        self.current_line = 1  # 当前行号
        self.current_col = 1  # 当前列号
        self.tokens = []  # 存储所有的有效token
        self.errors = []  # 存储所有的错误信息

    def tokenize(self, code: str) -> Tuple[List[SymbolEntry], List[SymbolEntry]]:
        # 词法分析方法，接收源代码字符串，返回token列表和错误列表
        logging.debug(f"开始词法分析：{code}")

        NUM_PATTERN = r'[+\-]?(?:0[xX][0-9a-fA-F]+[0-9A-Za-z]*|[0-9][0-9A-Za-z\.]*)'

        token_specs = [
            # 注释必须放在最前面
            ('MULTILINE_COMMENT', r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'),
            ('COMMENT', r'//.*'),
            ('CHAR', r"'([^'\\]|\\.)'"),
            ('STRING', r'"([^"\\]|\\.)*"'),
            # 数字规则（统一捕获合法与非法数字）
            ('NUM', NUM_PATTERN),
            ('KEYWORD',
             r'\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|int|long|register|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while)\b'),
            ('OPERATOR', r'''
                \+\+|--|->|            # ++, --, ->
                <<=|>>=|<<|>>|         # 位操作
                <=|>=|==|!=|           # 比较运算符
                \+=|-=|\*=|/=|%=|      # 复合赋值
                &&|\|\||               # 逻辑运算符
                [+\-*/%=&|^<>!~]       # 基础运算符
            ''', re.VERBOSE),
            ('DELIMITER', r'[{}()[\].,;:#]'),
            ('ID', r'[a-zA-Z_]\w*'),
            ('SKIP', r'[ \t]+'),
            ('NEWLINE', r'\n'),
            ('ERROR', r'.'),
        ]

        # 将所有token的正则表达式合并成一个大的正则表达式
        parts = []
        for spec in token_specs:
            if len(spec) == 2:
                name, pattern = spec
            elif len(spec) == 3:
                name, pattern, flag = spec
                # 如果 flag 是 re.VERBOSE，则使用内联标志包装模式
                if flag == re.VERBOSE:
                    pattern = f"(?x:{pattern})"
            else:
                raise ValueError("Token spec 格式错误")
            parts.append(f"(?P<{name}>{pattern})")
        tok_regex = "|".join(parts)

        line_start_pos = 0  # 当前行的起始位置

        # 使用re.finditer()遍历源代码，查找所有符合token规则的部分
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup  # 当前匹配到的token类型
            value = mo.group()  # 当前匹配到的token值
            start_pos = mo.start()  # 当前token的起始位置

            # 计算当前token的列号
            while True:
                line_end = code.rfind('\n', 0, start_pos)
                if line_end == -1:
                    col = start_pos - line_start_pos + 1  # 没有换行符，列号就是当前位置
                    break
                else:
                    line_start_pos = line_end + 1  # 更新行起始位置
                    col = start_pos - line_start_pos + 1  # 计算列号
                    break

            # 处理跳过的空格
            if kind == 'SKIP':
                self.current_col += len(value)  # 更新列号
                continue

            # 处理换行符，更新行号和列号
            elif kind == 'NEWLINE':
                self.current_line += 1  # 换行时行号加1
                self.current_col = 1  # 重置列号为1
                line_start_pos = mo.end()  # 更新行的起始位置
                continue

            # 根据不同的token类型，处理不同的操作
            if kind == 'COMMENT':
                self.current_col += len(value)
                continue
            elif kind == 'MULTILINE_COMMENT':
                newline_count = value.count('\n')
                self.current_line += newline_count
                if newline_count == 0:
                    self.current_col += len(value)
                else:
                    last_newline_pos = value.rfind('\n')
                    chars_after = len(value) - last_newline_pos - 1
                    self.current_col = chars_after + 1
                continue
            elif kind == 'STRING':
                # 处理字符串常量
                entry = self.symbol_table.process_string_literal(value, self.current_line, col)
            elif kind == 'CHAR':
                entry = self.symbol_table.process_char_literal(value, self.current_line, col)
            elif kind == 'NUM':
                entry = self.symbol_table.process_constant(value, self.current_line, col)
            elif kind == 'KEYWORD':
                # 处理关键字
                entry = SymbolEntry(value, TokenType.KEYWORD, line=self.current_line, column=col)
            elif kind == 'ID':
                # 处理标识符
                entry = SymbolEntry(value, TokenType.IDENTIFIER, line=self.current_line, column=col)
            elif kind == 'OPERATOR':
                # 处理运算符
                entry = SymbolEntry(value, TokenType.OPERATOR, line=self.current_line, column=col)
            elif kind == 'DELIMITER':
                # 处理分隔符
                entry = SymbolEntry(value, TokenType.DELIMITER, line=self.current_line, column=col)
            else:
                # 处理错误（无法识别的字符）
                entry = SymbolEntry(value, TokenType.ERROR, line=self.current_line, column=col)

            # 将有效的token加入到tokens列表，不合法的token加入到errors列表
            if entry.token_type == TokenType.ERROR:
                self.errors.append(entry)
            else:
                self.tokens.append(entry)

            self.current_col += len(value)  # 更新列号

        return self.tokens, self.errors  # 返回有效的token和错误的token列表
