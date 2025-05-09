from enum import Enum
from dataclasses import dataclass
from typing import Union, Optional, Tuple, List


# ------------------------------------------------------------------
# 定义词法单元的类别，区分关键字、界符、运算符、字面量、标识符以及错误
# ------------------------------------------------------------------
class TokenCategory(Enum):
    KEYWORD = "KEYWORD"  # 关键字，例如 if, for, char 等
    DELIMITER = "DELIMITER"  # 界符，例如 {}、,、; 等
    OPERATOR = "OPERATOR"  # 运算符，例如 +, -, == 等
    LITERAL = "LITERAL"  # 字面量，例如数字、字符串等
    IDENTIFIER = "IDENTIFIER"  # 标识符，例如变量名
    ERROR = "ERROR"  # 错误类型，用于表示词法分析中识别出的错误
    PREPROCESSOR = "PREPROCESSOR"


# ------------------------------------------------------------------
# 定义 TokenType 枚举，细化各类词法单元，同时保留种别码、显示名称以及所属类别
# ------------------------------------------------------------------
class TokenType(Enum):
    # 预处理指令类型
    PREPROCESSOR = (305, "#", TokenCategory.PREPROCESSOR)

    # 关键字（种别码 101-113）
    CHAR = (101, "char", TokenCategory.KEYWORD)
    INT = (102, "int", TokenCategory.KEYWORD)
    FLOAT = (103, "float", TokenCategory.KEYWORD)
    BREAK = (104, "break", TokenCategory.KEYWORD)
    CONST = (105, "const", TokenCategory.KEYWORD)
    RETURN = (106, "return", TokenCategory.KEYWORD)
    VOID = (107, "void", TokenCategory.KEYWORD)
    CONTINUE = (108, "continue", TokenCategory.KEYWORD)
    DO = (109, "do", TokenCategory.KEYWORD)
    WHILE = (110, "while", TokenCategory.KEYWORD)
    IF = (111, "if", TokenCategory.KEYWORD)
    ELSE = (112, "else", TokenCategory.KEYWORD)
    FOR = (113, "for", TokenCategory.KEYWORD)
    BOOL = (114, "bool", TokenCategory.KEYWORD)
    DOUBLE = (115, "double", TokenCategory.KEYWORD)

    # 界符（种别码 301-304）
    LEFT_BRACE = (301, "{", TokenCategory.DELIMITER)
    RIGHT_BRACE = (302, "}", TokenCategory.DELIMITER)
    SEMICOLON = (303, ";", TokenCategory.DELIMITER)
    COMMA = (304, ",", TokenCategory.DELIMITER)

    # 运算符（种别码 201-219）
    LEFT_PAREN = (201, "(", TokenCategory.OPERATOR)
    RIGHT_PAREN = (202, ")", TokenCategory.OPERATOR)
    LEFT_BRACKET = (203, "[", TokenCategory.OPERATOR)
    RIGHT_BRACKET = (204, "]", TokenCategory.OPERATOR)
    NOT = (205, "!", TokenCategory.OPERATOR)
    STAR = (206, "*", TokenCategory.OPERATOR)
    DIV = (207, "/", TokenCategory.OPERATOR)
    MOD = (208, "%", TokenCategory.OPERATOR)
    PLUS = (209, "+", TokenCategory.OPERATOR)
    MINUS = (210, "-", TokenCategory.OPERATOR)
    LT = (211, "<", TokenCategory.OPERATOR)
    LE = (212, "<=", TokenCategory.OPERATOR)
    GT = (213, ">", TokenCategory.OPERATOR)
    GE = (214, ">=", TokenCategory.OPERATOR)
    EQ = (215, "==", TokenCategory.OPERATOR)
    NE = (216, "!=", TokenCategory.OPERATOR)
    AND = (217, "&&", TokenCategory.OPERATOR)
    OR = (218, "||", TokenCategory.OPERATOR)
    ASSIGN = (219, "=", TokenCategory.OPERATOR)
    AMPERSAND = (220, '&', TokenCategory.OPERATOR)
    BITWISE_OR = (221, '|', TokenCategory.OPERATOR)
    BITWISE_XOR = (222, '^', TokenCategory.OPERATOR)
    BITWISE_NOT = (223, '~', TokenCategory.OPERATOR)
    INCREMENT = (224, "++", TokenCategory.OPERATOR)
    DECREMENT = (225, "--", TokenCategory.OPERATOR)
    POINTER = (226, "->", TokenCategory.OPERATOR)
    SHIFT_LEFT = (227, "<<", TokenCategory.OPERATOR)
    SHIFT_RIGHT = (228, ">>", TokenCategory.OPERATOR)
    SHIFT_LEFT_ASSIGN = (229, "<<=", TokenCategory.OPERATOR)
    SHIFT_RIGHT_ASSIGN = (230, ">>=", TokenCategory.OPERATOR)
    ADD_ASSIGN = (231, "+=", TokenCategory.OPERATOR)
    SUB_ASSIGN = (232, "-=", TokenCategory.OPERATOR)
    MUL_ASSIGN = (233, "*=", TokenCategory.OPERATOR)
    DIV_ASSIGN = (234, "/=", TokenCategory.OPERATOR)
    MOD_ASSIGN = (235, "%=", TokenCategory.OPERATOR)

    # 字面量和标识符（种别码 400-800）
    INT_CONST = (400, "INT_CONST", TokenCategory.LITERAL)
    FLOAT_CONST = (800, "FLOAT_CONST", TokenCategory.LITERAL)
    STR_LITERAL = (600, "STR_LITERAL", TokenCategory.LITERAL)
    IDENTIFIER = (700, "IDENTIFIER", TokenCategory.IDENTIFIER)
    ERROR = (999, "ERROR", TokenCategory.ERROR)

    # 构造函数，用于初始化枚举成员，同时存储种别码、显示名称和所属类别
    def __new__(cls, code, display, category):
        obj = object.__new__(cls)
        obj._value_ = code  # 枚举成员的值为种别码
        obj.code = code  # 种别码
        obj.display = display  # 显示名称
        obj.category = category  # 所属类别
        return obj

    @property
    def type_code(self):
        """返回词法单元的种别码"""
        return self.code

    @property
    def type_name(self):
        """返回词法单元的显示名称"""
        return self.display


# ------------------------------------------------------------------
# 定义词法分析中的符号项（token）的数据结构
# ------------------------------------------------------------------
@dataclass
class SymbolEntry:
    lexeme: str  # 词素，即源代码中的字符串
    token_type: TokenType  # 词法单元类型，使用上面的 TokenType 枚举
    value: Union[int, float, str, None] = None  # 常量的值，若适用时转换后的值
    line: int = 0  # 所在行号
    column: int = 0  # 所在列号
    error_msg: Optional[str] = None  # 若识别出错误时，存放错误信息


# ------------------------------------------------------------------
# 定义符号表，用于存储关键字、标识符以及常量等信息，
# 并提供插入、查找以及常量的格式验证等功能
# ------------------------------------------------------------------
class SymbolTable:
    def __init__(self, size=1024, parent=None):
        self.size = size
        # 使用一个固定大小的散列表，每个槽位存放一个列表（冲突处理采用链地址法）
        self.table = [[] for _ in range(size)]
        self.parent = parent  # 若存在父符号表，可用于嵌套作用域查找
        self._init_keywords()  # 初始化预定义的关键字

    def _init_keywords(self):
        """初始化关键字，将关键字预先插入符号表"""
        keywords = {
            'char': TokenType.CHAR,
            'int': TokenType.INT,
            'float': TokenType.FLOAT,
            'break': TokenType.BREAK,
            'const': TokenType.CONST,
            'return': TokenType.RETURN,
            'void': TokenType.VOID,
            'continue': TokenType.CONTINUE,
            'do': TokenType.DO,
            'while': TokenType.WHILE,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'for': TokenType.FOR,
            'bool': TokenType.BOOL,
            'double': TokenType.DOUBLE,
        }
        for kw, token_type in keywords.items():
            # 对于每个关键字，创建一个 SymbolEntry 对象并插入符号表
            self.insert(SymbolEntry(kw, token_type, line=0, column=0))

    def _hash(self, lexeme: str) -> int:
        """
        对词素进行哈希计算，返回对应的槽位索引
        使用 FNV-1a 哈希算法对字符串进行哈希计算
        """
        hash_val = 2166136261
        for char in lexeme.encode('utf-8'):
            hash_val ^= char
            hash_val *= 16777619
        return hash_val % self.size

    def insert(self, entry: SymbolEntry) -> None:
        """
        将符号项插入符号表中
        若符号表中已存在同样的词素，则更新其 token_type、value 和 error_msg
        """
        index = self._hash(entry.lexeme)
        bucket = self.table[index]
        for existing in bucket:
            if existing.lexeme == entry.lexeme:
                existing.token_type = entry.token_type
                existing.value = entry.value
                existing.error_msg = entry.error_msg
                return
        bucket.insert(0, entry)  # 插入到链表的头部

    def lookup(self, lexeme: str) -> Optional[SymbolEntry]:
        """
        根据词素查找符号表中是否已经存在该符号项
        如果存在则返回，否则在父符号表中查找或返回 None
        """
        index = self._hash(lexeme)
        for entry in self.table[index]:
            if entry.lexeme == lexeme:
                return entry
        if self.parent:
            return self.parent.lookup(lexeme)
        return None

    # -------------------------------------------------------------
    # 以下为数字格式验证以及常量处理函数
    # -------------------------------------------------------------

    def validate_float(self, lex: str) -> bool:
        """
        验证浮点数的格式是否合法
        格式要求：
          - 可选的正负号
          - 至少一位数字
          - 小数点
          - 小数点后至少一位数字
          - 可选的指数部分（e 或 E 后跟可选的正负号和数字）
        """
        pos = 0
        n = len(lex)
        if pos < n and lex[pos] in '+-':  # 检查可选正负号
            pos += 1
        start_digits = pos
        # 检验整数位数
        while pos < n and lex[pos].isdigit():
            pos += 1
        # 整数部分至少需要一位数字
        if pos == start_digits:
            return False
        # 验证一个浮点数字符串中是否包含必要的小数点部分
        if pos >= n or lex[pos] != '.':
            return False

        pos += 1
        start_frac = pos
        # 小数部分至少需要一位数字
        while pos < n and lex[pos].isdigit():
            pos += 1
        if pos == start_frac:
            return False

        # 检查指数部分
        if pos < n and lex[pos] in 'eE':
            pos += 1
            if pos < n and lex[pos] in '+-':  # 可选的正负号
                pos += 1
            start_exp = pos
            # 如果e后无数字则不合法
            while pos < n and lex[pos].isdigit():
                pos += 1
            if pos == start_exp:
                return False
        return pos == n  # 格式合法时，pos应当刚好到达字符串末尾

    def validate_int(self, lex: str) -> bool:
        """
        验证整数的格式是否合法
        支持：
          - 十进制整数
          - 以 0 开头的八进制整数
          - 十六进制数（以 0x 或 0X 开头）
          - 二进制数（以 0b 或 0B 开头）
          - 八进制数（以 0o 或 0O 开头）
        """
        s = lex
        if s and s[0] in '+-':
            s = s[1:]
        if not s:
            return False
        if s[0] == '0' and len(s) > 1:
            if s.startswith("0x") or s.startswith("0X"):
                if len(s) <= 2:
                    return False
                for c in s[2:]:
                    if c not in "0123456789abcdefABCDEF":
                        return False
                return True
            elif s.startswith("0b") or s.startswith("0B"):
                if len(s) <= 2:
                    return False
                for c in s[2:]:
                    if c not in "01":
                        return False
                return True
            elif s.startswith("0o") or s.startswith("0O"):
                if len(s) <= 2:
                    return False
                for c in s[2:]:
                    if c not in "01234567":
                        return False
                return True
            else:
                # 若不是特殊进制，则认为为八进制
                for c in s:
                    if c not in "01234567":
                        return False
                return True
        # 若不以 0 开头，则必须全部为十进制数字
        return all(c.isdigit() for c in s)

    def process_constant(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理常量（整数或浮点数）
        根据词素中的内容选择调用 validate_float 或 validate_int，并转换成相应的数值
        若格式不正确，则返回错误的 SymbolEntry
        """
        if ('.' in lexeme or 'e' in lexeme.lower()):
            # 处理浮点数
            if self.validate_float(lexeme):
                try:
                    value = float(lexeme)
                    entry = SymbolEntry(lexeme, TokenType.FLOAT_CONST, value, line, col)
                except Exception:
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                        error_msg="浮点数转换错误")
            else:
                entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                    error_msg="非法浮点数")
        else:
            # 处理整数
            if self.validate_int(lexeme):
                try:
                    base = 10
                    s = lexeme
                    if s[0] in '+-':
                        s = s[1:]
                    if s.startswith(('0x', '0X')):
                        base = 16
                    elif s.startswith(('0b', '0B')):
                        base = 2
                    elif s.startswith(('0o', '0O')):
                        base = 8
                    value = int(lexeme, base)
                    entry = SymbolEntry(lexeme, TokenType.INT_CONST, value, line, col)
                except Exception:
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                        error_msg="整数转换错误")
            else:
                entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                    error_msg="非法整数")
        # 将常量插入符号表，并返回对应的 SymbolEntry
        self.insert(entry)
        return entry

    def process_string_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理字符串字面量
        要求字符串以双引号开始和结束，并尝试对内部转义序列进行转换
        若不符合要求，则返回错误的 SymbolEntry
        """
        # 判断字符串是否闭合：长度至少为2，且首尾必须是双引号
        if len(lexeme) < 2 or lexeme[0] != '"' or lexeme[-1] != '"':
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="字符串字面量未闭合")
        try:
            # 对字符串内部的转义字符进行处理
            processed = bytes(lexeme[1:-1], 'utf-8').decode('unicode_escape')
            return SymbolEntry(lexeme, TokenType.STR_LITERAL, processed, line, col)
        except Exception:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="字符串转义错误")

    def process_char_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        """
        处理字符字面量
        要求字符以单引号开始和结束，并且内部只能包含一个字符或合法的转义字符
        如果不符合要求，则返回错误的 SymbolEntry
        """
        # 判断字符字面量是否闭合
        if len(lexeme) < 2 or lexeme[0] != "'" or lexeme[-1] != "'":
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="字符字面量未闭合")
        # 提取字符内容（去掉首尾的单引号）
        char_content = lexeme[1:-1]
        if len(char_content) == 0:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="空字符字面量")
        # 若字符内容只有一个字符，则直接取值
        if len(char_content) == 1:
            value = char_content
        elif char_content.startswith('\\'):
            # 处理转义字符，如果转换后的字符长度不为1，则出错
            try:
                value = bytes(char_content, 'utf-8').decode('unicode_escape')
                if len(value) != 1:
                    raise ValueError
            except Exception:
                return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                   error_msg="非法字符转义")
        else:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="非法字符字面量")
        # 将字符转换为其 ASCII 码值，存储为整数常量
        return SymbolEntry(lexeme, TokenType.INT_CONST, ord(value), line, col)
