import ply.lex as lex
import re

# ---------------------------------------------------
# 定义 token 类型及辅助信息
# ---------------------------------------------------
reserved = {
    'char': 'CHAR',
    'int': 'INT',
    'float': 'FLOAT',
    'break': 'BREAK',
    'const': 'CONST',
    'return': 'RETURN',
    'void': 'VOID',
    'continue': 'CONTINUE',
    'do': 'DO',
    'while': 'WHILE',
    'if': 'IF',
    'else': 'ELSE',
    'for': 'FOR'
}

tokens = [
             'PREPROCESSOR',
             'IDENTIFIER',
             'INT_CONST',
             'FLOAT_CONST',
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
             'LT',  # 小于号
             'GT',  # 大于号
             'LEFT_BRACE',
             'RIGHT_BRACE',
             'SEMICOLON',
             'COMMA',
             'LEFT_PAREN',
             'RIGHT_PAREN',
             'LEFT_BRACKET',
             'RIGHT_BRACKET',
         ] + list(reserved.values())

token_info = {
    'PREPROCESSOR': ('KEYWORD', 305),
    'CHAR': ('KEYWORD', 101),
    'INT': ('KEYWORD', 102),
    'FLOAT': ('KEYWORD', 103),
    'BREAK': ('KEYWORD', 104),
    'CONST': ('KEYWORD', 105),
    'RETURN': ('KEYWORD', 106),
    'VOID': ('KEYWORD', 107),
    'CONTINUE': ('KEYWORD', 108),
    'DO': ('KEYWORD', 109),
    'WHILE': ('KEYWORD', 110),
    'IF': ('KEYWORD', 111),
    'ELSE': ('KEYWORD', 112),
    'FOR': ('KEYWORD', 113),
    'LEFT_BRACE': ('DELIMITER', 301),
    'RIGHT_BRACE': ('DELIMITER', 302),
    'SEMICOLON': ('DELIMITER', 303),
    'COMMA': ('DELIMITER', 304),
    'LEFT_PAREN': ('OPERATOR', 201),
    'RIGHT_PAREN': ('OPERATOR', 202),
    'LEFT_BRACKET': ('OPERATOR', 203),
    'RIGHT_BRACKET': ('OPERATOR', 204),
    'LT': ('OPERATOR', 211),
    'GT': ('OPERATOR', 213),
    'NOT': ('OPERATOR', 205),
    'STAR': ('OPERATOR', 206),
    'DIV': ('OPERATOR', 207),
    'MOD': ('OPERATOR', 208),
    'PLUS': ('OPERATOR', 209),
    'MINUS': ('OPERATOR', 210),
    'LE': ('OPERATOR', 212),
    'GE': ('OPERATOR', 214),
    'EQ': ('OPERATOR', 215),
    'NE': ('OPERATOR', 216),
    'AND': ('OPERATOR', 217),
    'OR': ('OPERATOR', 218),
    'ASSIGN': ('OPERATOR', 219),
    'AMPERSAND': ('OPERATOR', 220),
    'BITWISE_OR': ('OPERATOR', 221),
    'BITWISE_XOR': ('OPERATOR', 222),
    'BITWISE_NOT': ('OPERATOR', 223),
    'INCREMENT': ('OPERATOR', 224),
    'DECREMENT': ('OPERATOR', 225),
    'POINTER': ('OPERATOR', 226),
    'SHIFT_LEFT': ('OPERATOR', 227),
    'SHIFT_RIGHT': ('OPERATOR', 228),
    'SHIFT_LEFT_ASSIGN': ('OPERATOR', 229),
    'SHIFT_RIGHT_ASSIGN': ('OPERATOR', 230),
    'ADD_ASSIGN': ('OPERATOR', 231),
    'SUB_ASSIGN': ('OPERATOR', 232),
    'MUL_ASSIGN': ('OPERATOR', 233),
    'DIV_ASSIGN': ('OPERATOR', 234),
    'MOD_ASSIGN': ('OPERATOR', 235),
    'INT_CONST': ('LITERAL', 400),
    'FLOAT_CONST': ('LITERAL', 800),
    'STR_LITERAL': ('LITERAL', 600),
    'CHAR_LITERAL': ('LITERAL', 400),
    'IDENTIFIER': ('IDENTIFIER', 700)
}


def find_column(input_text, lexpos):
    last_cr = input_text.rfind('\n', 0, lexpos)
    if last_cr < 0:
        last_cr = -1
    return lexpos - last_cr


# ---------------------------------------------------
# 数字常量规则
# ---------------------------------------------------
# (1) 带前缀的整数（0x, 0b, 0o）
def t_INT_CONST(t):
    r'[+-]?0[xX][0-9a-fA-F]+|[+-]?0[bB][01]+|[+-]?0[oO][0-7]+'
    s = t.value
    try:
        if s.lower().startswith("0x"):
            t.value = int(s, 16)
        elif s.lower().startswith("0b"):
            t.value = int(s, 2)
        elif s.lower().startswith("0o"):
            t.value = int(s, 8)
    except Exception:
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': s,
            'error_msg': "整数转换错误"
        })
        return None
    return t


# (2) 浮点数规则（合法浮点数后面必须是边界）
def t_FLOAT_CONST(t):
    r'[+-]?((([0-9]+\.[0-9]*)|(\.[0-9]+))([eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+)(?![0-9.eE])'
    try:
        t.value = float(t.value)
    except Exception:
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "浮点数转换错误"
        })
        return None
    return t


# (3) 捕获以数字开头但后接非法字符（如 "12a"）或异常浮点数
def t_INVALID_NUMBER(t):
    r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?[A-Za-z]+|[+-]?\d+\.\d+\.\d+|[+-]?0\d+\.\d+[eE][+-]?\d+'
    errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "异常十进制数"
    })
    t.lexer.skip(len(t.value))
    return None


# (4) 没有前缀、以 0 开头的数字（长度>1）
def t_INT_CONST_NO_PREFIX(t):
    r'[+-]?0[0-9]+(?=[^0-9A-Za-z]|$)'
    s = t.value
    sign = 1
    num = s
    if s[0] in '+-':
        if s[0] == '-': sign = -1
        num = s[1:]
    # 如果num全为 "0" 则合法
    if num == "0":
        t.value = 0
        t.type = "INT_CONST"
        return t
    # 如果全为0和1，则视为合法二进制
    if all(ch in "01" for ch in num):
        try:
            t.value = sign * int(num, 2)
            t.type = "INT_CONST"
            return t
        except Exception:
            errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': s,
                'error_msg': "二进制转换错误"
            })
            return None
    # 如果以"00"开头，则报异常8进制数
    if num.startswith("00"):
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': s,
            'error_msg': "异常8进制数"
        })
        t.lexer.skip(len(s))
        return None
    # 如果第二个字符为 '7' 且所有字符均在 "01234567" 内，则合法八进制
    if len(num) >= 2 and num[1] == '7' and all(ch in "01234567" for ch in num):
        try:
            t.value = sign * int(num, 8)
            t.type = "INT_CONST"
            return t
        except Exception:
            errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': s,
                'error_msg': "八进制转换错误"
            })
            return None
    # 否则，报异常二进制数
    errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': s,
        'error_msg': "异常二进制数"
    })
    t.lexer.skip(len(s))
    return None


# (5) 普通十进制整数（不以 0 开头或单独 0）
def t_DECIMAL_INT(t):
    r'[+-]?[1-9]\d*(?=[^0-9A-Za-z]|$)|0(?=[^0-9A-Za-z]|$)'
    try:
        t.value = int(t.value)
    except Exception:
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "整数转换错误"
        })
        return None

    t.type = "INT_CONST"
    return t


# ---------------------------------------------------
# 运算符规则
# ---------------------------------------------------
def t_INVALID_OPERATOR(t):
    r'>=='
    errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "异常运算符"
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


# 单字符运算符和界符
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


# ---------------------------------------------------
# 字符串与字符规则
# ---------------------------------------------------
def t_STR_LITERAL(t):
    r'"([^\\\n]|(\\.))*"'
    if t.value[-1] != '"':
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符串字面量未闭合"
        })
        return None

    try:
        # 去掉首尾的引号，处理转义字符，然后重新加上引号
        content = t.value[1:-1]
        decoded = bytes(content, "utf-8").decode("unicode_escape")
        t.value = '"' + decoded + '"'
        return t
    except Exception:
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符串转义错误"
        })
        return None


def t_CHAR_LITERAL(t):
    r'\'([^\\\n]|(\\.))*\''
    if len(t.value) < 2 or t.value[-1] != "'":
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符字面量未闭合"
        })
        return None

    content = t.value[1:-1]
    try:
        decoded = bytes(content, "utf-8").decode("unicode_escape")
        if len(decoded) != 1:
            errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': t.value,
                'error_msg': "字符字面量只能包含一个字符"
            })
            return None
        t.value = ord(decoded)
    except Exception:
        errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "非法字符转义"
        })
        return None
    return t


# ---------------------------------------------------
# 注释规则
# ---------------------------------------------------
def t_comment_singleline(t):
    r'//.*'
    pass


def t_comment(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count("\n")
    # 忽略闭合的注释


def t_unclosed_comment(t):
    r'/\*(.|\n)*'
    errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "多行注释未闭合"
    })
    t.lexer.skip(len(t.value))
    return None


# ---------------------------------------------------
# 预处理指令与标识符
# ---------------------------------------------------
def t_PREPROCESSOR(t):
    r'\#[^\n]*'
    if '//' in t.value:
        t.value = t.value.split('//')[0].rstrip()
    return t


def t_IDENTIFIER(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')
    return t


# ---------------------------------------------------
# 换行与忽略
# ---------------------------------------------------
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


t_ignore = " \t\r"

errors = []


def t_error(t):
    errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value[0],
        'error_msg': "非法字符"
    })
    t.lexer.skip(1)


# ---------------------------------------------------
# 构建词法分析器
# ---------------------------------------------------
lexer = lex.lex()

# ---------------------------------------------------
# 主程序：运行测试并输出 token 与错误信息
# ---------------------------------------------------
if __name__ == '__main__':
    code_sample = r'''/*这是实验一的测试用例，
//大家把测试界面截图放到实验报告测试文件中*/
@xy      //测试非法字符
#include     //测试预处理指令
abc  _ab    //测试标识符
12             //测试正常十进制整数
12a           //测试异常十进制数
1.2             //测试浮点数
1.2.3          //测试异常浮点数
1.2e2+3    //测试正常浮点数
05.234e3   //测试异常浮点数
0.12           //测试正常浮点数
00.12e+4  //测试浮点数
0x34          //测试正常16进制数
0x3g          //测试异常16进制数
0912         //测试异常八进制数
0712         //测试正常八进制数
0020         //测试异常八进制数
01110        //测试正常二进制数
0211         //测试异常二进制数
>==         //测试异常运算符
+     ++     +=     >=3  //测试双运算符
char a='x';   //测试字符字面量
b = 'acc';   //测试非法字符字面量（单引号内多字符）
string d="12      //测试异常字符串字面量
"acc";      //测试正常字符串字面量
bool d = true;
void main()
{
    int a=0,  b[3]={1,2,3};    //测试括号配对，词法阶段可以不报错
    for(int t=0;t<4;t++)    //测试括号配对，词法阶段可以不报错
/*这个程序快结束了       //测试注释未闭合
}'''
    lexer.input(code_sample)
    input_text = code_sample

    tokens_list = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        tokens_list.append(tok)

    print("Tokens:")
    for tok in tokens_list:
        col = find_column(input_text, tok.lexpos)
        info = token_info.get(tok.type, ('UNKNOWN', 0))
        print(f"{tok.lineno}:{col} '{tok.value}' -> {info[0]}({info[1]})")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"{err['line']}:{err['column']} '{err['lexeme']}' -> {err['error_msg']}")


