import ply.lex as lex
import re
from practice.tokenType import TokenType, SymbolEntry, TokenCategory

# ---------------------------------------------------
# 定义 token 类型及辅助信息
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
             'RIGHT_BRACKET',
         ] + [token_type.name for token_type in reserved.values()]

token_info = {
    'COMMENT': ('COMMENT', 900),
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
# 词法分析器规则
# ---------------------------------------------------

# 注释规则（最高优先级）
def t_COMMENT(t):
    r'(/\*([^*]|\*+[^*/])*\*+/)|(//[^\n]*)'
    t.lexer.lineno += t.value.count("\n")
    return None  # 忽略注释token


def t_unclosed_comment(t):
    r'/\*([^*]|\*+[^*/])*'
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "多行注释未闭合"
    })
    t.lexer.skip(len(t.value))
    return None


# 带前缀的整数（放在异常数字规则之前）
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


# 异常数字规则
def t_INVALID_NUMBER(t):
    r'[+-]?0[xX][0-9a-fA-F]*[g-zG-Z][0-9a-zA-Z]*|[+-]?0[xX]|[+-]?(\d+[a-zA-Z]+)|([+-]?0[0-7]*[89][0-9]*)|([+-]?0[2-9][0-9]*)|([+-]?[0-9]+\.[0-9]+\.[0-9]+)|([+-]?0[0-9]+\.[0-9]+)|([+-]?[0-9]+\.[0-9]+[eE][+-]?[0-9]+[+-][0-9]+)|([+-]?[0-9]+\.[0-9]+[eE][^0-9+-])|[+-]?0\d+\.\d+[eE][+-]?\d+|[+-]?0\d+\.\d+[eE]|[+-]?0\d+\.\d+[eE][+-]'
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value,
        'error_msg': "异常数字"
    })
    t.lexer.skip(len(t.value))
    return None


# 浮点数规则
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
            'error_msg': "异常数字"
        })
        return None


# 以0开头的数字
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
            t.lexer.errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': s,
                'error_msg': "异常数字"
            })
            return None
    # 如果以"00"开头，则报异常8进制数
    if num.startswith("00"):
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': s,
            'error_msg': "异常数字"
        })
        t.lexer.skip(len(s))
        return None
    # 如果所有字符均在 "01234567" 内，则合法八进制
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
                'error_msg': "异常数字"
            })
            return None
    # 否则，报异常八进制数
    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': s,
        'error_msg': "异常数字"
    })
    t.lexer.skip(len(s))
    return None


# 普通十进制整数
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


# 字符串字面量
def t_STR_LITERAL(t):
    r'"([^\\\n]|(\\.))*"'
    if t.value[-1] != '"':
        t.lexer.errors.append({
            'line': t.lineno,
            'column': find_column(t.lexer.lexdata, t.lexpos),
            'lexeme': t.value,
            'error_msg': "字符串字面量未闭合"
        })
        return None

    try:
        content = t.value[1:-1]
        decoded = bytes(content, "utf-8").decode("unicode_escape")
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


# 字符字面量
def t_CHAR_LITERAL(t):
    r'\'([^\\\n]|(\\.))*\''
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
        if len(decoded) != 1:
            t.lexer.errors.append({
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t.lexpos),
                'lexeme': t.value,
                'error_msg': "字符字面量只能包含一个字符"
            })
            return None
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


# 预处理指令
def t_PREPROCESSOR(t):
    r'\#[^\n]*'
    if '//' in t.value:
        t.value = t.value.split('//')[0].rstrip()
    return t


# 标识符
def t_IDENTIFIER(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')
    if isinstance(t.type, TokenType):
        t.type = t.type.name
    return t


# 运算符规则
def t_INVALID_OPERATOR(t):
    r'>=='
    t.lexer.errors.append({
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


# 换行与忽略
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


t_ignore = " \t\r"


def t_error(t):
    # 如果是在注释中的字符，跳过
    if t.lexer.lexdata.rfind('/*', 0, t.lexpos) > t.lexer.lexdata.rfind('*/', 0, t.lexpos) or \
            t.lexer.lexdata.rfind('//', 0, t.lexpos) > t.lexer.lexdata.rfind('\n', 0, t.lexpos):
        t.lexer.skip(1)
        return

    t.lexer.errors.append({
        'line': t.lineno,
        'column': find_column(t.lexer.lexdata, t.lexpos),
        'lexeme': t.value[0],
        'error_msg': "非法字符"
    })
    t.lexer.skip(1)


# 添加词法分析器类
class Lexer:
    def __init__(self):
        self.lexer = lex.lex()
        self.lexer.errors = []  # 将errors列表作为lexer对象的属性

    def tokenize(self, code):
        self.lexer.input(code)
        tokens = []
        self.lexer.errors = []  # 清空错误列表

        while True:
            try:
                tok = self.lexer.token()
                if not tok:
                    break

                # 创建SymbolEntry对象
                token_type = TokenType[tok.type] if tok.type in TokenType.__members__ else TokenType.ERROR
                entry = SymbolEntry(
                    lexeme=str(tok.value),
                    token_type=token_type,
                    value=tok.value,
                    line=tok.lineno,
                    column=find_column(code, tok.lexpos)
                )
                tokens.append(entry)
            except Exception as e:
                # 捕获词法分析过程中的错误
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

        # 处理错误
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

        return tokens, errors


# ---------------------------------------------------
# 主程序：运行测试并输出 token 与错误信息
# ---------------------------------------------------
if __name__ == '__main__':
    # 创建词法分析器实例
    lexer = Lexer()

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

    # 执行词法分析
    tokens, errors = lexer.tokenize(code_sample)

    # 输出结果
    print("Tokens:")
    for token in tokens:
        print(
            f"{token.line}:{token.column} '{token.lexeme}' -> {token.token_type.category.value}({token.token_type.code})")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"{error.line}:{error.column} '{error.lexeme}' -> {error.error_msg}")


