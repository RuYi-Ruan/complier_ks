from enum import Enum
from dataclasses import dataclass
from typing import Union, Optional, Tuple, List


# 定义 Token 类型的枚举类
# 每个枚举成员都由两个部分组成：一个数值（reference）和一个描述字符串（display）
class TokenType(Enum):
    KEYWORD = (0, "KEYWORD")  # 关键字（如 int, return）
    IDENTIFIER = (1, "IDENTIFIER")  # 标识符（变量名、函数名等）
    INT_CONSTANT = (2, "INT_CONST")  # 整型常量（如 123, 0x1A）
    FLOAT_CONSTANT = (3, "FLOAT_CONST")  # 浮点常量（如 3.14, 1e10）
    STRING_LITERAL = (4, "STR_LITERAL")  # 字符串字面量（如 "hello"）
    OPERATOR = (5, "OPERATOR")  # 运算符（如 +, -, *=）
    DELIMITER = (6, "DELIMITER")  # 界符（如 {, }, ;）
    ERROR = (7, "ERROR")  # 错误标记（当符号不符合语法规则时使用）

    # 当创建枚举成员时，会调用 __new__ 方法来传入 reference 和 display 两个参数
    def __new__(cls, code, display):
        obj = object.__new__(cls)
        obj._value_ = code  # 将枚举成员的值设置为 reference
        obj.code = code  # 存储 reference
        obj.display = display  # 存储描述信息
        return obj

    @property
    def type_code(self):
        # 返回 token 的数值代码
        return self.code

    @property
    def type_name(self):
        # 返回 token 的描述名称
        return self.display


# 使用 dataclass 定义符号表条目数据结构
# 存储词法单元的信息，包括词素、类型、对应的值、所在行和列，以及可选的错误信息
@dataclass
class SymbolEntry:
    lexeme: str  # 词素（具体字符串内容）
    token_type: TokenType  # 词法单元的类型（如关键字、标识符、常量等）
    value: Union[int, float, str, None] = None  # 如果是常量，则存储其数值或字符串内容
    line: int = 0  # 源代码中的行号
    column: int = 0  # 源代码中的列号
    error_msg: Optional[str] = None  # 如果 token 有错误，则记录错误说明


# 定义符号表，用于存储和查找各个词法单元（符号）
class SymbolTable:
    def __init__(self, size=1024, parent=None):
        self.size = size
        # 创建一个固定大小的哈希表，每个位置为一个列表，用于存放可能发生冲突的符号
        self.table = [[] for _ in range(size)]
        self.parent = parent  # 支持嵌套作用域（父符号表）
        self._init_keywords()  # 初始化时预加载 C 语言关键字

    def _init_keywords(self):
        # C 语言的关键字列表
        keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue',
            'default', 'do', 'double', 'else', 'enum', 'extern',
            'float', 'for', 'goto', 'if', 'int', 'long', 'register',
            'return', 'short', 'signed', 'sizeof', 'static', 'struct',
            'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while'
        ]
        # 将每个关键字插入符号表，标记其 token 类型为 KEYWORD
        for kw in keywords:
            self.insert(SymbolEntry(kw, TokenType.KEYWORD, line=0, column=0))

    def _hash(self, lexeme: str) -> int:
        # 使用 FNV-1a 算法计算字符串的哈希值
        hash_val = 2166136261
        for char in lexeme.encode('utf-8'):
            hash_val ^= char
            hash_val *= 16777619
        # 返回哈希值对表大小取模的结果
        return hash_val % self.size

    def insert(self, entry: SymbolEntry) -> None:
        # 将符号条目插入到符号表中
        index = self._hash(entry.lexeme)
        bucket = self.table[index]
        # 如果符号已经存在，则更新其信息
        for existing in bucket:
            if existing.lexeme == entry.lexeme:
                existing.token_type = entry.token_type
                existing.value = entry.value
                existing.error_msg = entry.error_msg
                return
        # 若不存在，则采用头插法插入新条目
        bucket.insert(0, entry)

    def lookup(self, lexeme: str) -> Optional[SymbolEntry]:
        # 在当前符号表中查找给定词素对应的条目
        index = self._hash(lexeme)
        for entry in self.table[index]:
            if entry.lexeme == lexeme:
                return entry
        # 如果当前符号表中未找到，并且存在父符号表，则递归查找父符号表
        if self.parent:
            return self.parent.lookup(lexeme)
        return None

    # ---------------------------
    # 以下为数字（整型和浮点型）格式验证函数
    # ---------------------------
    def validate_float(self, lex: str) -> bool:
        # 验证字符串是否为合法的浮点数格式
        pos = 0
        n = len(lex)
        # 可选的符号部分
        if pos < n and lex[pos] in '+-':
            pos += 1
        start_digits = pos
        # 检查整数部分是否存在数字
        while pos < n and lex[pos].isdigit():
            pos += 1
        if pos == start_digits:
            return False
        # 必须包含小数点
        if pos >= n or lex[pos] != '.':
            return False
        pos += 1
        start_frac = pos
        # 检查小数部分是否存在数字
        while pos < n and lex[pos].isdigit():
            pos += 1
        if pos == start_frac:
            return False
        # 可选的科学计数法部分
        if pos < n and lex[pos] in 'eE':
            pos += 1
            if pos < n and lex[pos] in '+-':
                pos += 1
            start_exp = pos
            while pos < n and lex[pos].isdigit():
                pos += 1
            if pos == start_exp:
                return False
        # 检查是否完全匹配到字符串末尾
        return pos == n

    def validate_int(self, lex: str) -> bool:
        # 验证字符串是否为合法的整数格式
        s = lex
        # 处理可能的前置符号
        if s and s[0] in '+-':
            s = s[1:]
        if not s:
            return False
        # 检查以 0 开头的情况（可能为八进制、十六进制、二进制）
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
                # 默认当作八进制数处理
                for c in s:
                    if c not in "01234567":
                        return False
                return True
        # 非零开头时，全部字符必须为数字
        return all(c.isdigit() for c in s)

    def process_constant(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        # 根据词素内容判断是浮点数还是整数，并进行相应处理
        if ('.' in lexeme or 'e' in lexeme.lower()):
            # 处理浮点数
            if self.validate_float(lexeme):
                try:
                    value = float(lexeme)
                    entry = SymbolEntry(lexeme, TokenType.FLOAT_CONSTANT, value, line, col)
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
                    # 判断进制类型
                    if s.startswith(('0x', '0X')):
                        base = 16
                    elif s.startswith(('0b', '0B')):
                        base = 2
                    elif s.startswith(('0o', '0O')):
                        base = 8
                    value = int(lexeme, base)
                    entry = SymbolEntry(lexeme, TokenType.INT_CONSTANT, value, line, col)
                except Exception:
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                        error_msg="整数转换错误")
            else:
                entry = SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                    error_msg="非法整数")
        # 将处理后的 token 插入符号表
        self.insert(entry)
        return entry

    def process_string_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        # 处理字符串字面量，要求以双引号包围，否则视为错误
        if len(lexeme) < 2 or lexeme[0] != '"' or lexeme[-1] != '"':
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="非法字符串字面量")
        try:
            # 对内部内容进行转义字符解析
            processed = bytes(lexeme[1:-1], 'utf-8').decode('unicode_escape')
            return SymbolEntry(lexeme, TokenType.STRING_LITERAL, processed, line, col)
        except Exception:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="字符串转义错误")

    def process_char_literal(self, lexeme: str, line: int, col: int) -> SymbolEntry:
        # 处理字符字面量，要求以单引号包围
        if len(lexeme) < 3 or lexeme[0] != "'" or lexeme[-1] != "'":
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="非法字符字面量")
        # 提取引号之间的内容
        char_content = lexeme[1:-1]
        if len(char_content) == 1:
            value = char_content
        elif char_content.startswith('\\'):
            try:
                # 解析转义字符
                value = bytes(char_content, 'utf-8').decode('unicode_escape')
                if len(value) != 1:
                    raise ValueError
            except Exception:
                return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                                   error_msg="非法字符转义")
        else:
            return SymbolEntry(lexeme, TokenType.ERROR, line=line, column=col,
                               error_msg="非法字符字面量")
        # 使用 ord() 得到字符对应的整数值
        return SymbolEntry(lexeme, TokenType.INT_CONSTANT, ord(value), line, col)


# 词法分析器类
class Lexer:
    def __init__(self):
        self.symbol_table = SymbolTable()  # 用于存储和管理词法单元
        self.current_line = 1  # 当前处理的行号
        self.current_col = 1  # 当前处理的列号
        self.tokens: List[SymbolEntry] = []  # 存放识别出的有效 token
        self.errors: List[SymbolEntry] = []  # 存放识别过程中出现的错误 token

    def tokenize(self, code: str) -> Tuple[List[SymbolEntry], List[SymbolEntry]]:
        i = 0
        n = len(code)
        # 允许出现在运算符中的字符集合
        allowed_operator_chars = set("+-*/%=&|^<>!~")
        # 预定义所有合法的运算符字符串
        allowed_operators = {
            "++", "--", "->", "<<", ">>", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "%=",
            "&&", "||", "<<=", ">>=", "+", "-", "*", "/", "%", "=", "&", "|", "^", "<", ">", "!", "~"
        }
        # 分隔符字符集合
        delimiters = "{}()[].,;:#"

        # 开始遍历源代码
        while i < n:
            ch = code[i]
            start_line = self.current_line
            start_col = self.current_col

            # 处理空格和制表符：跳过这些无意义的字符
            if ch in ' \t':
                i += 1
                self.current_col += 1
                continue

            # 处理换行符：更新行号，重置列号
            if ch == '\n':
                i += 1
                self.current_line += 1
                self.current_col = 1
                continue

            # 处理单行注释（以 // 开头）
            if ch == '/' and i + 1 < n and code[i + 1] == '/':
                i += 2
                self.current_col += 2
                # 跳过注释行，直到遇到换行符
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
                # 循环查找注释结束符 "*/"
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
                    # 注释未闭合，记录为错误 token
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=start_comment_line, column=start_comment_col,
                                        error_msg="多行注释未闭合")
                    self.errors.append(entry)
                continue

            # 处理字符串字面量（以双引号开始和结束）
            if ch == '"':
                lexeme = ch
                i += 1
                self.current_col += 1
                closed = False
                # 循环收集字符串中的字符
                while i < n:
                    # 如果遇到未转义的双引号，则结束字符串字面量
                    if code[i] == '"' and (len(lexeme) == 1 or lexeme[-1] != '\\'):
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                        closed = True
                        break
                    # 如果遇到换行符，提前结束字符串收集
                    if code[i] == '\n':
                        break
                    lexeme += code[i]
                    i += 1
                    self.current_col += 1
                # 交由符号表处理字符串字面量是否合法
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
                # 交由符号表处理字符字面量是否合法
                entry = self.symbol_table.process_char_literal(lexeme, start_line, start_col)
                if entry.token_type == TokenType.ERROR:
                    self.errors.append(entry)
                else:
                    self.tokens.append(entry)
                continue

            # 处理数字（包括整型和浮点型）
            if ch.isdigit() or (ch in '+-' and i + 1 < n and code[i + 1].isdigit()):
                lexeme = ""
                error_flag = False
                # 如果数字以 + 或 - 开头，则先加入词素
                if ch in '+-':
                    lexeme += ch
                    i += 1
                    self.current_col += 1
                    if i >= n or not code[i].isdigit():
                        entry = SymbolEntry(lexeme, TokenType.ERROR, line=start_line, column=start_col,
                                            error_msg="非法数字")
                        self.errors.append(entry)
                        continue
                # 判断是否为十六进制、二进制或八进制数（以 0 开头并跟随 x/X, b/B, o/O）
                if i + 1 < n and code[i] == '0' and code[i + 1] in 'xXbBoO':
                    lexeme += code[i] + code[i + 1]
                    i += 2
                    self.current_col += 2
                    while i < n and code[i].isalnum():
                        lexeme += code[i]
                        i += 1
                        self.current_col += 1
                else:
                    dot_encountered = False
                    # 循环处理数字及可能的小数点、指数部分
                    while i < n:
                        c = code[i]
                        if c.isdigit():
                            lexeme += c
                            i += 1
                            self.current_col += 1
                        elif c == '.':
                            if dot_encountered:
                                error_flag = True  # 如果第二次遇到小数点则出错
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
                            exp_digits_start = i
                            while i < n and code[i].isdigit():
                                lexeme += code[i]
                                i += 1
                                self.current_col += 1
                            if i == exp_digits_start:
                                error_flag = True  # 指数部分没有数字则出错
                            break
                        else:
                            break
                    # 即使 error_flag 为 True，后续仍由验证函数检测格式是否正确
                # 交由符号表处理数字常量
                entry = self.symbol_table.process_constant(lexeme, start_line, start_col)
                if entry.token_type == TokenType.ERROR:
                    self.errors.append(entry)
                else:
                    self.tokens.append(entry)
                continue

            # 处理标识符和关键字（以字母或下划线开始）
            if ch.isalpha() or ch == '_':
                lexeme = ""
                while i < n and (code[i].isalnum() or code[i] == '_'):
                    lexeme += code[i]
                    i += 1
                    self.current_col += 1
                # 先查符号表，判断是否是预定义的关键字
                sym = self.symbol_table.lookup(lexeme)
                if sym and sym.token_type == TokenType.KEYWORD:
                    entry = SymbolEntry(lexeme, TokenType.KEYWORD, line=start_line, column=start_col)
                else:
                    entry = SymbolEntry(lexeme, TokenType.IDENTIFIER, line=start_line, column=start_col)
                self.tokens.append(entry)
                continue

            # 处理运算符：尝试匹配最长的合法运算符
            if ch in allowed_operator_chars:
                max_len = min(3, n - i)  # 限制运算符最大长度为 3
                found = None
                for l in range(max_len, 0, -1):
                    candidate = code[i:i + l]
                    if candidate in allowed_operators:
                        found = candidate
                        break
                if found is not None:
                    lexeme = found
                    i += len(found)
                    self.current_col += len(found)
                    entry = SymbolEntry(lexeme, TokenType.OPERATOR, line=start_line, column=start_col)
                    self.tokens.append(entry)
                else:
                    # 如果未匹配到合法运算符，则将连续的运算符字符视为错误
                    j = i
                    while j < n and code[j] in allowed_operator_chars:
                        j += 1
                    lexeme = code[i:j]
                    i = j
                    self.current_col += len(lexeme)
                    entry = SymbolEntry(lexeme, TokenType.ERROR, line=start_line, column=start_col,
                                        error_msg="非法运算符")
                    self.errors.append(entry)
                continue

            # 处理分隔符：单个字符的分隔符
            if ch in delimiters:
                lexeme = ch
                i += 1
                self.current_col += 1
                entry = SymbolEntry(lexeme, TokenType.DELIMITER, line=start_line, column=start_col)
                self.tokens.append(entry)
                continue

            # 其它字符：如果无法识别则记录为错误 token
            entry = SymbolEntry(ch, TokenType.ERROR, line=start_line, column=start_col,
                                error_msg="非法字符")
            self.errors.append(entry)
            i += 1
            self.current_col += 1

        # 返回所有识别出的 token 和错误 token 列表
        return self.tokens, self.errors


# ---------------------------
# 示例调用及测试
# ---------------------------
if __name__ == "__main__":
    code_sample = r'''
/*这是实验一的测试用例，
//大家把测试界面截图放到实验报告测试文件中*/
@xy      //测试非法字符
#include     //测试字符
abc  _ab    //测试标识符
12             //测试正常十进制整数
12a           //测试异常十进制整数
1.2             //测试浮点数
1.2.3          //测试异常浮点数
1.2e2+3    //测试正常浮点数
05.234e3   //测试异常浮点数
0.12           //测试正常浮点数
00.12e+4  //测试浮点数
0x34          //测试正常16进制数
0x3g          //测试异常16进制数
0912         //测试异常8进制数
0712         //测试8进制数
0020        //测试异常8进制数
01110       //测试二进制数，选做
0211        //测试二进制数，选做
+     ++     +=     >==3  //测试双运算符
char a='x';   //测试异常字符常量
 b = 'b;         //测试异常字符常量
string d="12;     //测试异常字符串常量
c = "acc";    //测试正常字符串常量

bool d = true;
void main()
{
	int a=0,  b[3={1,2,3};    //测试括号配对，词法阶段可以不报错
	for(int t=0;t<4;t++    //测试括号配对，词法阶段可以不报错
/*这个程序快结束了       //测试注释不闭合
}
    '''
    lexer = Lexer()
    tokens, errors = lexer.tokenize(code_sample)
    print("Tokens:")
    for token in tokens:
        print(f"{token.line}:{token.column} '{token.lexeme}' -> {token.token_type.type_name}")
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"{error.line}:{error.column} '{error.lexeme}' -> {error.error_msg}")
