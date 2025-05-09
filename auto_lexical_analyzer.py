import ply.lex as lex
from practice.tokenType import TokenType, SymbolEntry

# ---------------------------------------------------
# 定义保留字对应的 TokenType
# ---------------------------------------------------
reserved = {
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
    'for': TokenType.FOR
}

# ---------------------------------------------------
# 定义所有 token 名称列表
# 注意：除了一些复杂的多字符运算符和字面量，其它的直接使用 TokenType 枚举中的名称。
# ---------------------------------------------------
tokens = [
    'COMMENT',
    'PREPROCESSOR',
    'FLOAT_CONST',
    'INT_CONST',
    'IDENTIFIER',
    'STR_LITERAL',
    'CHAR_LITERAL',

    # 多字符运算符
    'INCREMENT',
    'DECREMENT',
    'POINTER',
    'SHIFT_LEFT_ASSIGN',
    'SHIFT_RIGHT_ASSIGN',
    'ADD_ASSIGN',
    'SUB_ASSIGN',
    'MUL_ASSIGN',
    'DIV_ASSIGN',
    'MOD_ASSIGN',
    'SHIFT_LEFT',
    'SHIFT_RIGHT',
    'LE',
    'GE',
    'EQ',
    'NE',
    'AND',
    'OR',

    # 单字符运算符及界符
    'PLUS',
    'MINUS',
    'STAR',
    'DIV',
    'MOD',
    'NOT',
    'ASSIGN',
    'AMPERSAND',
    'BITWISE_OR',
    'BITWISE_XOR',
    'BITWISE_NOT',
    'LT',
    'GT',
    'LEFT_BRACE',
    'RIGHT_BRACE',
    'SEMICOLON',
    'COMMA',
    'LEFT_PAREN',
    'RIGHT_PAREN',
    'LEFT_BRACKET',
    'RIGHT_BRACKET'
] + [token_type.name for token_type in reserved.values()]
# 以上 tokens 列表中，由 reserved 字典补充了关键字的 token 名称，
# 因此在后续词法规则中，遇到标识符时可利用 reserved 进行转换。


def find_column(input_text, lexpos):
    """
    根据 lexpos （在源代码中的位置）来计算当前 token 所在的列号。
    先找到 lexpos 之前最后一次出现换行符的位置，再计算 token 距离该位置的字符数。
    """
    last_cr = input_text.rfind('\n', 0, lexpos)
    if last_cr < 0:
        last_cr = -1
    return lexpos - last_cr


# ---------------------------------------------------
# 下面定义词法分析器各个 token 的识别规则
# ---------------------------------------------------

# -------------------
# 1. 注释识别规则
# -------------------
def t_COMMENT(t):
    r'(/\*([^*]|\*+[^*/])*\*+/)|(//[^\n]*)'
    # 统计注释中的换行符
    t.lexer.lineno += t.value.count("\n")
    # 返回 None 表示忽略注释，不生成 token
    return None


def t_unclosed_comment(t):
    r'/\*([^*]|\*+[^*/])*'
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "多行注释未闭合"
    })
    # 跳过整个未闭合注释的内容
    t.lexer.skip(len(t.value))
    return None


# -------------------------------
# 2. 数值（整数及浮点数）处理规则
# -------------------------------

# 带前缀的整数处理（16进制、二进制和8进制）
def t_INT_CONST(t):
    r'[+-]?0[xX][0-9a-fA-F]+(?![0-9a-zA-Z])|[+-]?0[bB][01]+(?![0-9a-zA-Z])|[+-]?0[oO][0-7]+(?![0-9a-zA-Z])'
    s = t.value
    try:
        if s.lower().startswith("0x"):
            t.value = int(s, 16)
        elif s.lower().startswith("0b"):
            t.value = int(s, 2)
        elif s.lower().startswith("0o"):
            t.value = int(s, 8)
        return t
    except Exception:
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': s,
            'error_msg': "整数转换错误"
        })
        return None


# 识别非法数字（例如非法的进制表示、非法的数字组合、错误的指数形式等）
def t_INVALID_NUMBER(t):
    r'''
        [+-]?0[xX][0-9a-fA-F]*[g-zG-Z][0-9a-zA-Z]* |  # 非法的十六进制数字（包含g-z）
        [+-]?0[xX] |                                    # 无效的十六进制前缀
        [+-]?(\d+[a-zA-Z]+) |                           # 数字后跟字母（如123abc）
        [+-]?0[0-9]*[89][0-9]* |                        # 八进制数中包含8或9
        ([+-]?[0-9]+\.[0-9]+\.[0-9]+) |                 # 多个小数点（如1.2.3）
        ([+-]?0[0-9]+\.[0-9]+) |                        # 前导零后跟小数点（如00.123）
        ([+-]?[0-9]+\.[0-9]+[eE][+-]?[0-9]+[+-][0-9]+) |# 错误的指数形式（如1e3+4）
        ([+-]?[0-9]+\.[0-9]+[eE][^0-9+-]) |             # 指数部分含有非数字字符
        ([+-]?0\d+\.\d+[eE][+-]?\d+) |                  # 前导零浮点数指数错误（如012.3e4）
        ([+-]?0\d+\.\d+[eE]) |                          # 指数不完整（如012.3e）
        ([+-]?0\d+\.\d+[eE][+-])                        # 指数符号不完整（如012.3e+）
    '''
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "非法数字"
    })
    t.lexer.skip(len(t.value))
    return None


# 浮点数规则，匹配形如 1.23, .456, 1.2e3 等形式
def t_FLOAT_CONST(t):
    r'[+-]?((([1-9][0-9]*\.[0-9]*)|(\.[0-9]+))([eE][+-]?[0-9]+)?|[1-9][0-9]*[eE][+-]?[0-9]+)(?![0-9.eE+-])'
    try:
        t.value = float(t.value)
        return t
    except Exception:
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "非法数字"
        })
        return None


# 数字以 0 开头的情况（特殊处理不带前缀的数字）
def t_INT_CONST_NO_PREFIX(t):
    r'[+-]?0[0-9]+(?=[^0-9A-Za-z]|$)'
    s = t.value
    sign = 1
    num = s
    if s[0] in '+-':
        if s[0] == '-':
            sign = -1
        num = s[1:]
    # 如果数字仅为 "0"，直接返回合法数字
    if num == "0":
        t.value = 0
        t.type = "INT_CONST"
        return t

    # 判断如何处理：
    # 如果第二个字符不为 '0'，认为是合法的八进制字面量（需要所有字符都在 '0'-'7' 范围内）
    if num[1] != '0':
        if all(ch in "01234567" for ch in num):
            try:
                t.value = sign * int(num, 8)
                t.type = "INT_CONST"
                return t
            except Exception:
                t.lexer.errors.append({
                    'line': t.lineno,
                    'column': find_column(t.lexer.lexdata, t.lexpos),
                    'lexeme': s,
                    'error_msg': "整数转换错误"
                })
                return None
        else:
            t.lexer.errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': s,
                'error_msg': "非法八进制数字"
            })
            t.lexer.skip(len(s))
            return None
    else:
        # 如果第二个字符为 '0'，认为前导 0 多余，按要求不予接收，报错
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': s,
            'error_msg': "非法八进制数字：不允许多余的前导零"
        })
        t.lexer.skip(len(s))
        return None




# 处理普通的十进制整数
def t_DECIMAL_INT(t):
    r'[+-]?[1-9]\d*(?=[^0-9A-Za-z]|$)|0(?=[^0-9A-Za-z]|$)'
    try:
        t.value = int(t.value)
    except Exception:
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "整数转换错误"
        })
        return None

    t.type = "INT_CONST"
    return t


# ----------------------
# 3. 字符串和字符字面量
# ----------------------

# 字符串字面量，支持转义字符（要求字符串必须以双引号开始和结束）
def t_STR_LITERAL(t):
    r'"([^\\\n]|(\\.))*"'
    # 检查是否闭合
    if t.value[-1] != '"':
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符串字面量未闭合"
        })
        return None

    try:
        # 对字符串内部内容进行转义处理
        content = t.value[1:-1]
        decoded = bytes(content, "utf-8").decode("unicode_escape")
        # 此处保存带引号的完整字符串，也可以只保存实际内容
        t.value = '"' + decoded + '"'
        return t
    except Exception:
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符串转义错误"
        })
        return None


# 字符字面量，必须以单引号包围，并且内部仅允许单个字符或合法的转义序列
def t_CHAR_LITERAL(t):
    r'\'([^\\\n]|(\\.))*\''
    # 检查是否闭合
    if len(t.value) < 2 or t.value[-1] != "'":
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符字面量未闭合"
        })
        return None

    content = t.value[1:-1]
    try:
        decoded = bytes(content, "utf-8").decode("unicode_escape")
        # 字符字面量只允许单个字符，否则报错
        if len(decoded) != 1:
            t.lexer.errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': t.value,
                'error_msg': "字符字面量只能包含一个字符"
            })
            return None
        # 将字符转换为其对应的整数（ASCII码）
        t.value = ord(decoded)
    except Exception:
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "非法字符转义"
        })
        return None
    return t


# ----------------------
# 4. 预处理指令（例如 #include 等）
# ----------------------
def t_PREPROCESSOR(t):
    r'\#[^\n]*'
    # 如果预处理指令中包含注释，则去除注释部分（例如 "#include //注释"）
    if '//' in t.value:
        t.value = t.value.split('//')[0].rstrip()
    return t


# ----------------------
# 5. 标识符和关键字
# ----------------------
def t_IDENTIFIER(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    # 利用 reserved 字典判定是否为关键字
    t.type = reserved.get(t.value, 'IDENTIFIER')
    if isinstance(t.type, TokenType):  # 如果为关键字则取其名称
        t.type = t.type.name
    return t


# ----------------------
# 6. 运算符规则（多字符运算符优先于单字符运算符）
# ----------------------
def t_INVALID_OPERATOR(t):
    r'>=='
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "非法运算符"
    })
    t.lexer.skip(len(t.value))
    return None


def t_INCREMENT(t):
    r'\+\+'
    return t


def t_DECREMENT(t):
    r'--'
    return t


def t_POINTER(t):
    r'->'
    return t


def t_SHIFT_LEFT_ASSIGN(t):
    r'<<='
    return t


def t_SHIFT_RIGHT_ASSIGN(t):
    r'>>='
    return t


def t_ADD_ASSIGN(t):
    r'\+='
    return t


def t_SUB_ASSIGN(t):
    r'-='
    return t


def t_MUL_ASSIGN(t):
    r'\*='
    return t


def t_DIV_ASSIGN(t):
    r'/='
    return t


def t_MOD_ASSIGN(t):
    r'%='
    return t


def t_SHIFT_LEFT(t):
    r'<<'
    return t


def t_SHIFT_RIGHT(t):
    r'>>'
    return t


def t_LE(t):
    r'<='
    return t


def t_GE(t):
    r'>='
    return t


def t_EQ(t):
    r'=='
    return t


def t_NE(t):
    r'!='
    return t


def t_AND(t):
    r'&&'
    return t


def t_OR(t):
    r'\|\|'
    return t


# ---------------------------
# 7. 单字符运算符和界符规则
# ---------------------------
t_PLUS = r'\+'
t_MINUS = r'-'
t_STAR = r'\*'
t_DIV = r'/'
t_MOD = r'%'
t_NOT = r'!'
t_ASSIGN = r'='
t_AMPERSAND = r'&'
t_BITWISE_OR = r'\|'
t_BITWISE_XOR = r'\^'
t_BITWISE_NOT = r'~'
t_LT = r'<'
t_GT = r'>'
t_LEFT_BRACE = r'\{'
t_RIGHT_BRACE = r'\}'
t_SEMICOLON = r';'
t_COMMA = r','
t_LEFT_PAREN = r'\('
t_RIGHT_PAREN = r'\)'
t_LEFT_BRACKET = r'\['
t_RIGHT_BRACKET = r'\]'


# ---------------------------
# 8. 换行和忽略空白字符
# ---------------------------
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# 忽略空格、制表符、回车符
t_ignore = " \t\r"


# ---------------------------
# 9. 错误处理规则
# ---------------------------
def t_error(t):
    # 如果当前字符处于注释区域内，则跳过，不处理错误
    if (t.lexer.lexdata.rfind('/*', 0, t.lexpos) > t.lexer.lexdata.rfind('*/', 0, t.lexpos) or
        t.lexer.lexdata.rfind('//', 0, t.lexpos) > t.lexer.lexdata.rfind('\n', 0, t.lexpos)):
        t.lexer.skip(1)
        return

    # 添加错误记录，并跳过当前字符
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value[0],
        'error_msg': "非法字符"
    })
    t.lexer.skip(1)


# ---------------------------------------------------
# 10. 词法分析器封装为 Lexer 类
# ---------------------------------------------------
class Lexer:
    def __init__(self):
        # 创建 ply.lex 词法解析器
        self.lexer = lex.lex()
        # 初始化存放错误信息的列表
        self.lexer.errors = []

    def tokenize(self, code):
        """
        对传入的源代码进行词法分析，返回 token 列表和错误信息列表。
        其中，token 为 SymbolEntry 对象，记录了词素、TokenType、行号、列号以及转换后的值等信息。
        """
        self.lexer.input(code)
        tokens_list = []
        # 每次分析前清空错误列表
        self.lexer.errors = []

        while True:
            try:
                tok = self.lexer.token()
                print(tok)
                if not tok:
                    break

                # 根据解析出的 tok.type（字符串形式），查找 TokenType 枚举对象
                if tok.type in TokenType.__members__:
                    token_type = TokenType[tok.type]
                else:
                    token_type = TokenType.ERROR

                # 创建 SymbolEntry 对象记录 token 信息
                entry = SymbolEntry(
                    lexeme=str(tok.value),
                    token_type=token_type,
                    value=tok.value,
                    line=tok.lineno,
                    column=find_column(code, tok.lexpos)
                )
                tokens_list.append(entry)
            except Exception as e:
                # 捕获词法分析过程中出现的异常，加入错误信息
                error_entry = SymbolEntry(
                    lexeme=str(tok.value) if hasattr(tok, 'value') else '',
                    token_type=TokenType.ERROR,
                    line=tok.lineno if hasattr(tok, 'lineno') else 0,
                    column=find_column(code, tok.lexpos) if hasattr(tok, 'lexpos') else 0,
                    error_msg=str(e)
                )
                self.lexer.errors.append({
                    'line': error_entry.line,
                    'column': error_entry.column,
                    'lexeme': error_entry.lexeme,
                    'error_msg': error_entry.error_msg
                })

        # 将 lexer 中的错误转换为 SymbolEntry 对象列表
        errors = []
        for err in self.lexer.errors:
            error_entry = SymbolEntry(
                lexeme=err['lexeme'],
                token_type=TokenType.ERROR,
                line=err['line'],
                column=err['column'],
                error_msg=err['error_msg']
            )
            errors.append(error_entry)

        return tokens_list, errors


# ---------------------------------------------------
# 11. 主程序：用于运行测试并输出词法分析器生成的 token 与错误信息
# ---------------------------------------------------
if __name__ == '__main__':
    # 创建词法分析器实例
    lexer = Lexer()

    # 示例代码，包含了各种测试用例，既有合法的，也有故意出错的情况
    code_sample = r'''
    /*这是实验一的
测试用例*/
//大家把测试界面截图放文件中
abc
12
1.2
12a
15.
1.5.0
1.2e2+3
00.234e3
0x34
0x3g
0912
++
+=
>==3
char b = 'b';
string c = "acc";
bool d = true;
//以下是词法分析器的完整测试
int main()
{
	int n, days1, days2, count = 0;
	char input1[11];
	int alldays;
	int num1, num2;
	scanf("%d", &n);
	getchar();
	int year[3] = { 0 };
	for (int i = 0; i < n; i++)
	{
		memset(year, 0, sizeof(year));
		gets(input1);
		convert(input1, year);
		days2 = diffdays(year[0], year[1], year[2]);
		gets(input1);
		memset(year, 0, sizeof(year));
		convert(input1, year);
		days1 = diffdays(year[0], year[1], year[2]);
		alldays = days1 - days2;
		int temp = diffdays(2018, 12, 8);
		num1 = (days1 - temp) % 7;
		num2 = (days2 - temp) % 7;
		if (num1 == 0 && num2 == 0)
		{
			printf("%d\n", alldays / 7 + 1);
			continue;
		}
		if (temp < days2)
		{
			if (num1 != 0)
				alldays -= num1;
			if (num2 != 0)
				alldays -= (7 - num2);
			count += 1;
		}
		else if (temp > days2&&temp < days1)
		{
			if (num1 != 0)
				alldays -= num1;
			if (num2 != 0)
				alldays -= num2;
			count += 1;
		}
		else if (temp > days1)
		{
			if (num1 != 0)
				alldays -= (7 - num1);
			if (num2 != 0)
				alldays -= num2;
			count += 1;
		}
		else if (temp == days1 || temp == days2)
			count++;
		printf("%d\n", alldays / 7 + count);
	}
}
    '''

    # 执行词法分析
    tokens_list, errors = lexer.tokenize(code_sample)
    # 输出 token 结果，显示行号、列号、词素以及对应的 token 类型（类别和种别码）
    print("Tokens:")
    for token in tokens_list:
        print(f"{token.line}:{token.column} '{token.lexeme}' -> {token.token_type.category.value}({token.token_type.code})")

    # 输出错误信息
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"{error.line}:{error.column} '{error.lexeme}' -> {error.error_msg}")
