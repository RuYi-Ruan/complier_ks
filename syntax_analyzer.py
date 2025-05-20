# 定义 Token 类，用于封装一个词法单元的信息
import json
import logging
import os
import sys
from typing import Optional, List, Dict, Tuple, Union


class Token:
    def __init__(self, line, col, token_type, value):
        # 行号和列号转换为整数
        self.line = int(line)
        self.col = int(col)
        self.type = token_type  # 词法类型，如 KEYWORD、IDENTIFIER、OPERATOR 等
        self.value = value  # 实际的字符串值，如 "int", "main", "+", "0" 等

    def __repr__(self):
        # 自定义打印格式，便于调试和输出
        return f"Token({self.line}:{self.col}, {self.type}, {self.value})"


# 定义 TokenStream 类，用于管理 token 列表的读取操作
class TokenStream:
    def __init__(self, filename):
        # 初始化时从文件加载所有 token
        self.tokens = self._load_tokens(filename)
        self.current = 0  # 当前读取的位置索引

    # 内部函数：从文件中读取所有 token 并存储到列表中
    def _load_tokens(self, filename):
        tokens = []
        with open(filename, 'r', encoding='gbk') as file:
            for line in file:
                if not line.strip():  # 跳过空行
                    continue
                # 将每一行按制表符拆分为三个部分：位置、类型和值
                pos, token_type, value = line.strip().split('\t')
                # 位置形如 "3:5"，拆分为行号和列号
                line_no, col_no = pos.split(':')
                # 构造 Token 对象并添加到列表中
                tokens.append(Token(line_no, col_no, token_type, value))
        return tokens

    # 获取当前 token 并将指针移动到下一个（类似迭代器的 next）
    def next(self):
        if self.current < len(self.tokens):
            tok = self.tokens[self.current]
            self.current += 1
            return tok
        return None  # 没有更多 token 时返回 None

    # 查看当前 token 但不前进（用于语法分析中的 lookahead）
    def peek(self, offset=0):
        """
        返回当前指针向前偏移 offset 的 token，但不移动指针。
        offset=0 时等同于原 peek()：看下一个要 next() 的 token。
        offset=1 则是再往后一个，以此类推。
        """
        idx = self.current + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    # 重置读取指针到开头（用于测试或语法分析回溯）
    def reset(self):
        self.current = 0


# 判断关键字类型
KEYWORD_TYPES = {"int", "float", "bool", "char", "double", "void", "const"}


def is_type(tok_type, tok_val):
    return tok_type == "KEYWORD" and tok_val in KEYWORD_TYPES


# 符号表条目
class Symbol:
    def __init__(self, kind: str, name: str, typ: str,
                 params=None, scope_level: int = 0, line: int = 0,
                 is_defined: bool = False):
        self.kind = kind  # 'function' 或 'variable' 或 'parameter'
        self.name = name
        self.type = typ
        self.params = params
        self.scope_level = scope_level
        self.first_line = line
        self.count = 1
        self.is_defined = is_defined # 函数是否有函数体(定义)

    def increment(self):
        self.count += 1


# 符号表
class SymbolTable:
    def __init__(self):
        # 全局函数表
        self.functions: Dict[str, Symbol] = {}
        # 变量表
        self.vars: List[Dict[str, Symbol]] = []
        # 变量作用域栈，每层为 dict[name->Symbol]
        self.var_scopes: List[Dict[str, Symbol]] = []
        self.current_level = -1
        self.enter_scope()  # 创建全局变量作用域

    def enter_scope(self):
        self.var_scopes.append({})
        self.current_level += 1

    def exit_scope(self):
        if self.current_level >= 0:
            scope = self.var_scopes.pop()
            self.vars.append(scope)
            self.current_level -= 1

    def add_function(self, name: str, return_type: str,
                     param_types: List[str], line: int = 0,
                     is_definition: bool = False):
        existing = self.functions.get(name)

        # —— 不允许与变量同名 ——
        for scope in self.var_scopes:
            if name in scope:
                raise Exception(f"[Semantic Error] Function '{name}' conflicts with variable name at line {line}")

        if existing:
            # —— 重复声明检查 ——
            if existing.is_defined and is_definition:
                # 已经定义过，再定义就错
                raise Exception(f"[Semantic Error] Function '{name}' redefined at line {line}")
            if not existing.is_defined and not is_definition:
                # 已声明又声明，可以忽略或报重复声明
                self.functions[name].increment()
                raise Exception(f"[Semantic Error] Function  redeclared at line {line}")
            # 存在声明添加定义
            existing.is_defined = True
        else:
            sym = Symbol(kind='function', name=name, typ=return_type,
                         params=param_types, line=line,
                         is_defined=is_definition)
            self.functions[name] = sym

    def add_variable(self, name: str, var_type: str, kind: str = 'variable', line: int = 0):
        # —— 不允许与函数同名 ——
        if name in self.functions:
            raise Exception(f"[Semantic Error] Variable '{name}' conflicts with function name at line {line}")

        scope = self.var_scopes[self.current_level]
        if name in scope:
            scope[name].increment()
        else:
            sym = Symbol(kind=kind, name=name, typ=var_type, scope_level=self.current_level, line=line)
            scope[name] = sym

    def dump(self, path="./output/symbol_table.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            'functions': [vars(s) for s in self.functions.values()],
            'variables': [vars(sym) for scope in (self.vars + self.var_scopes) for sym in scope.values()]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def lookup_function(self, name: str) -> Optional[Symbol]:
        return self.functions.get(name)

    def lookup_variable(self, name: str) -> Optional[Symbol]:
        for lvl in range(self.current_level, -1, -1):
            if name in self.var_scopes[lvl]:
                return self.var_scopes[lvl][name]
        return None

    def lookup_var_in_current_scope(self, name: str) -> Optional[Symbol]:
        """只在当前作用域查找，检测重定义"""
        return self.var_scopes[self.current_level].get(name)


# 语法分析器
class SyntaxAnalyzer:
    def __init__(self, token_file="./token/tokens.txt",
                 output_file="./output/syntaxTree.txt",
                 error_file: str = "./output/syntax_errors.txt"):
        self.error_file = error_file
        # —— 1. 获取 logger 并清掉所有旧的 handler ——
        self.logger = logging.getLogger("SyntaxTree")
        self.logger.setLevel(logging.DEBUG)
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)

        # —— 2. 新增 控制台 handler ——
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(message)s")
        ch.setFormatter(fmt)
        self.logger.addHandler(ch)

        # —— 3. 新增 文件 handler，用 'w' 模式确保每次都 truncate ——
        fh = logging.FileHandler(output_file, mode="w", encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)

        self.tok = TokenStream(token_file)
        self.current_token = None
        self.indent = 0
        self.errors = []  # 用来收集错误
        self.last_token = None  # 记录上一个消费的 token,用于指定错误语句的行号

        # --- 符号表 ---
        self.symtab = SymbolTable()

    def peek_n(self, n=0):
        """
        返回从 current_token 开始，向前看第 n 个 token，但不移动指针。
        peek_n(0) == self.current_token
        peek_n(1) == 下一个要 next() 的 token
        依此类推
        """
        return self.tok.peek(n)

    # 语法树缩进
    def _log(self, msg):
        line = "--" * self.indent + msg
        self.logger.debug(line)

    # 进入某个文法时打印
    def _enter(self, name):
        self._log(f"分析{name}")
        self.indent += 1

    # 退出某个文法时打印
    def _exit(self, name):
        self.indent -= 1
        self._log(f"{name}分析结束")

    # 检测当前单词是否与文法的预期匹配
    def match(self, expected_type, expected_val=None):
        tok = self.current_token
        if tok is None:
            self.error("Unexpected end of input", use_token=self.last_token)

        # 如果看到一个意外的右括号，但当前文法不期待 ')'
        if tok.type == "OPERATOR" and tok.value == ")" and not (expected_type == "OPERATOR" and expected_val == ")"):
            # 直接报告“多余右括号”，然后跳过
            self.report_error(f"[Syntax Error] Unexpected ')' at line {tok.line}, col {tok.col}")
            self.current_token = self.tok.next()
            return

        # 如果有具体的 expected_val，就只允许它作为错误提示
        if tok.type == expected_type and (expected_val is None or tok.value == expected_val):
            self.last_token = tok
            self.current_token = self.tok.next()
        else:
            exp = expected_val if expected_val is not None else expected_type
            # 这里直接报错
            self.error(f"Expected '{exp}', but got {tok}", use_token=self.last_token or tok)

    def error(self, msg, use_token=None):
        # 如果传入了 use_token，就用它的行列；否则用当前 token
        tok = use_token or self.current_token or Token(0, 0, "EOF", "")
        full = f"[Syntax Error] {msg} at line {tok.line}, col {tok.col}"
        raise SyntaxError(full)

    def report_error(self, exception):
        # 记录错误字符串，不抛出
        self.errors.append(str(exception))

    def sync_to(self, sync_values):
        """
        跳过 token，直到碰到 sync_values 中的某个终结符。
        sync_values 是一组 (type, value) 对。
        即跳过当前出现语法错误的行
        """
        while self.current_token:
            if any(self.current_token.type == t and (v is None or self.current_token.value == v)
                   for t, v in sync_values):
                return
            self.current_token = self.tok.next()

    # 检查变量是否重定义
    def check_var_redefine(self, var_name: str, var_type: str, line):
        # —— 语义动作：同一作用域重定义检测 ——
        if self.symtab.lookup_var_in_current_scope(var_name):
            # 同一层已有同名变量，报错但继续解析
            self.report_error(f"[Semantic Error] Variable '{var_name}' redeclared in the same scope at line {line}")
            return True
        return False

    def type_compatible(self, declared: str, actual: str) -> bool:
        # 简单规则：同名、int->float 允许，其它都不行
        if declared == actual:
            return True
        if declared == "float" and actual == "int":
            return True
        return False

    """
    下面是语法分析模块，采用递归下降，parse为入口函数
    """

    def parse(self):
        # —— 在真正解析前，先把旧的错误文件清空 ——
        open(self.error_file, 'w', encoding='utf-8').close()
        # 开始分析
        self.current_token = self.tok.next()
        try:
            self.parse_P()
        except SyntaxError as e:
            self.report_error(e)

        if self.current_token is not None:
            self.report_error(f"Extra input after end of top-level block: {self.current_token}")

        # —— 在这里做 main 函数存在性检查 ——
        main_sym = self.symtab.lookup_function("main")

        if not main_sym or not main_sym.is_defined:
            # 如果既没声明也没定义，或者只声明没定义，都算缺 main
            self.report_error("[Semantic Error] Missing 'main' function")

        # 在写入 errors 文件之前，加上未使用变量的警告
        for scope in self.symtab.var_scopes + self.symtab.vars:
            for sym in scope.values():
                # 只检查普通变量（不包括参数、常量、函数名冲突等）
                if sym.kind == 'variable' and sym.count == 1:
                    self.report_error(
                        f"[Warning] Variable '{sym.name}' declared at line {sym.first_line} but never used"
                    )

        print("—— 解析结束 ——")
        # —— 在这里一次性把 errors 写到文件 ——
        with open(self.error_file, "w", encoding="utf-8") as f:
            for e in self.errors:
                f.write(e + "\n")
        self.symtab.dump()

    # P → TopList
    def parse_P(self):
        self._enter("程序")
        self.parse_TopList()
        self._exit("程序")

    # TopList → Top TopList | ε
    def parse_TopList(self):
        while (self.current_token is not None
               and (is_type(self.current_token.type, self.current_token.value)
                    or (self.current_token.type == "DELIMITER"
                        and self.current_token.value == "{")
                    or (self.current_token.type == "IDENTIFIER"
                        and self.current_token.value == "main"))):
            self.parse_Top()

    """
        Top → D     // 全局变量声明
          | FunDcl     // 函数声明
          | FunDef    // 函数定义
          | MainFunDef
          | { L }             // 匿名块
        MainFunDef → main ( ParamListOpt ) { L }
        FunDecl → type id ( ParamListOpt ) ;
        FunDef → type id ( ParamListOpt ) { L }
    """

    def parse_Top(self):
        if self.current_token:
            # 允许 `main()` 无类型
            if ((self.current_token.type == "IDENTIFIER" and self.current_token.value == "main")
                    or (is_type(self.current_token.type, self.current_token.value) and
                        self.peek_n().value == "main")):
                self._enter("main 函数")
                ret_type = self.current_token.value
                if self.current_token.type == "KEYWORD":
                    self.match("KEYWORD")
                line = self.current_token.line
                self.match("IDENTIFIER", "main")
                self.symtab.enter_scope()
                # main 一定是定义（有函数体），标记 is_definition=True
                self.symtab.add_function(name="main", param_types=[], return_type=ret_type,
                                        line = line, is_definition = True)
                self.match("OPERATOR", "(")
                self.parse_ParamListOpt()
                self.match("OPERATOR", ")")
                if self.current_token.value == "{":
                    self.match("DELIMITER", "{")
                    self.parse_L()
                    self.match("DELIMITER", "}")

                    self.symtab.exit_scope()
                    self._exit("main 函数")
                    return
                else:
                    self.error("Expected '{' after main function declaration")
                return

            elif is_type(self.current_token.type, self.current_token.value):
                # —— 可选 const 前缀 ——
                is_const = False
                if self.current_token.type == "KEYWORD" and self.current_token.value == "const":
                    is_const = True
                    self.match("KEYWORD", "const")

                # 需要区分是函数声明还是全局变量声明,向后提前查看两个单词
                # 全局变量声明 int a = 1; 函数 int a() {} | ;
                # 看下 3 个 token：type, id, 第三个 token
                t1 = self.current_token  # KEYWORD int
                t2 = self.peek_n()  # IDENTIFIER a
                t3 = self.tok.peek(1)  # 偏移 1 => 第三个 token

                if t2 and t2.type == "IDENTIFIER" and t3:
                    if t3.value == "(":  # int a ( …  → 函数声明/定义
                        self.parse_FunDef()
                    elif t3.value in ("=", ";", ","):  # int a = …; 或 int a; → 变量声明
                        self.parse_D(is_const = is_const)
                    else:
                        self.error(f"Unexpected token {t3} after type+id")
                else:
                    self.error("Expected identifier after type")

                return

            elif self.current_token.type == "DELIMITER" and self.current_token.value == "{":
                self._enter("块")
                self.symtab.enter_scope()
                self.match("DELIMITER", "{")
                self.parse_L()
                self.match("DELIMITER", "}")
                self.symtab.exit_scope()
                self._exit("块")
                return
        else:
            self.error("Expect FunDef or block")

    # FunDef → type id (ParamListOpt) {L}
    def parse_FunDef(self):
        if is_type(self.current_token.type, self.current_token.value):
            self._enter("函数定义")
            # 收集函数类型
            func_type = self.current_token.value
            self.match("KEYWORD")
            # 收集函数名称
            func_name = self.current_token.value
            self.match("IDENTIFIER")

            # 作用域层级 + 1
            self.symtab.enter_scope()

            self.match("OPERATOR", "(")
            # TODO: 后续应收集函数参数
            params = self.collect_params()
            # self.parse_ParamListOpt()

            self.match("OPERATOR", ")")

            if self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == ";":
                self._enter("函数声明")
                self.symtab.add_function(name=func_name, return_type=func_type, param_types=[],
                                         line=self.current_token.line, is_definition=False)
                # 更新函数签名
                self.symtab.functions[func_name].params = [f"{ptype} {pname} " for ptype, pname, _ in params]
                self.match("DELIMITER", ";")  # 函数声明
                self._exit("函数声明")
            elif self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == "{":
                # 如果是函数定义则需要将函数中的参数加入符号表
                for ptype, pname, pline in params:
                    if pname is not None:
                        self.symtab.add_variable(name=pname,
                                                 var_type=ptype,
                                                 kind='parameter',
                                                 line=pline)
                self.symtab.add_function(name=func_name, return_type=func_type, param_types=[],
                                         line=self.current_token.line, is_definition=True)
                # 更新函数签名
                self.symtab.functions[func_name].params = [f"{ptype} {pname} " for ptype, pname, _ in params]
                self.match("DELIMITER", "{")
                self.parse_L()
                self.match("DELIMITER", "}")
            else:
                self.error("Expected ';' or '{' after function signature", use_token=self.current_token)

            # 作用域层级 - 1
            self.symtab.exit_scope()
            self._exit("函数定义")
            return

    def collect_params(self):
        params = []
        if is_type(self.current_token.type, self.current_token.value):
            while True:
                ptype = self.current_token.value
                self.match('KEYWORD')
                pname = None
                pline = self.current_token.line
                if self.current_token.type == 'IDENTIFIER':
                    pname = self.current_token.value
                    self.match('IDENTIFIER')
                params.append((ptype, pname, pline))
                if self.current_token.value != ',': break
                self.match('DELIMITER', ',')
        return params

    #   ParamListOpt → ParamList | ε
    def parse_ParamListOpt(self):
        # 仅当下一个是 type 时才进入
        if is_type(self.current_token.type, self.current_token.value):
            self.parse_ParamList()
        # 否则 ε，什么都不做

    # ParamList → Param ( "," Param )*
    def parse_ParamList(self):
        self.parse_Param()
        while self.current_token and \
                self.current_token.type == "DELIMITER" and \
                self.current_token.value == ",":
            self.match("DELIMITER", ",")
            self.parse_Param()

    # Param → type [ id ]
    def parse_Param(self):
        self._enter("参数")
        self.match("KEYWORD")
        # 如果后面是标识符，再把它吃掉；否则跳过
        if self.current_token and self.current_token.type == "IDENTIFIER":
            self.match("IDENTIFIER")
        self._exit("参数")

    # L -> S L | ε
    def parse_L(self):
        """多条语句"""
        while self.current_token is not None and (
                # 赋值语句或后缀自增开头
                self.current_token.type == "IDENTIFIER"
                or (self.current_token.type == "OPERATOR"
                    and self.current_token.value in ("++", "--"))
                # 声明语句以类型关键字开头
                or is_type(self.current_token.type, self.current_token.value)
                # 块语句
                or (self.current_token.type == "DELIMITER" and self.current_token.value == "{")
                # if/while/for/do/break/continue/return 开头
                or (self.current_token.type == "KEYWORD" and self.current_token.value in
                    {"if", "while", "for", "do", "break", "continue", "return"})
        ):
            try:
                self.parse_S()
            except SyntaxError as e:
                self.report_error(e)
                self.sync_to({("DELIMITER", ";"), ("DELIMITER", "}")})
                if self.current_token and self.current_token.value == ';':
                    self.current_token = self.tok.next()

    """
    S   → F 
    | id CompAssign B ;
    | { L }
    | if ( B ) S S'
    | while ( B ) S
    | for ( ForInit ; B ; ForIter ) S
    | do S while ( B ) ;
    | continue ;
    | return ReturnExpr ;
    | break ;
    | D
    
    CompAssign -> = | += | -= | *= | /= | %=
    """

    def parse_S(self):
        if self.current_token.type == "DELIMITER" and self.current_token.value == ";":
            self._enter("空语句")
            self.match("DELIMITER", ";")
            self._exit("空语句")

        # 函数调用也当作表达式语句
        # 如果看到 IDENTIFIER 后面紧跟 '(', 就当作调用
        # 如果看到了 ++ 或 --，或是标识符后面直接跟 ++/--，
        # 就当成一条“表达式语句”：parse_F 再 match 分号
        # 函数调用或其他 F 导出的表达式语句
        elif (self.current_token.type == "IDENTIFIER"
              and self.peek_n().type == "OPERATOR"
              and self.peek_n().value == "(") \
                or (self.current_token.type == "OPERATOR"
                    and self.current_token.value in ("++", "--")) \
                or (self.current_token.type == "IDENTIFIER"
                    and self.peek_n().type == "OPERATOR"
                    and self.peek_n().value in ("++", "--")):
            self._enter("表达式语句")
            self.parse_F()
            self.match("DELIMITER", ";")
            self._exit("表达式语句")
            return

        # 赋值语句
        elif self.current_token.type == "IDENTIFIER":
            self._enter("赋值语句")
            lhs_name = self.current_token.value
            line = self.current_token.line
            self.match("IDENTIFIER")
            # 检查是否为常量，如果为常量则不能赋值
            sym = self.symtab.lookup_variable(lhs_name)
            if sym and sym.kind == "CONST":
                self.report_error(f"[Semantic Error] Cannot assign to constant '{lhs_name}' at line {line}")
            # 检查左值是否已声明
            if not self.symtab.lookup_variable(lhs_name):
                self.report_error(
                    f"[Semantic Error] Assignment to undeclared variable '{lhs_name}' at line {self.last_token.line}")
            if self.current_token.type == "OPERATOR" and self.current_token.value == "=":
                self.match("OPERATOR", "=")
                rhs_type = self.parse_B()
                self.match("DELIMITER", ";")
            else:
                self.error("Expected assignment operator …")
            self._exit("赋值语句")

        # 块语句
        elif self.current_token.type == "DELIMITER" and self.current_token.value == "{":
            # 1) 进入新块作用域
            self.symtab.enter_scope()
            self.match("DELIMITER", "{")
            self.parse_L()
            self.match("DELIMITER", "}")
            # 2) 退出新块作用域
            self.symtab.exit_scope()
            return

        # if 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "if":
            self._enter("if语句")
            self.match("KEYWORD", "if")
            self.match("OPERATOR", "(")
            self.parse_B()
            self.match("OPERATOR", ")")
            self.parse_S()
            self.parse_S_prime()
            self._exit("if语句")
            return

        # while 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "while":
            self._enter("while语句")
            self.match("KEYWORD", "while")
            self.match("OPERATOR", "(")
            self.parse_B()
            self.match("OPERATOR", ")")
            self.parse_S()
            self._exit("while语句")
            return

        # for 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "for":
            self._enter("for 语句")
            self.match("KEYWORD", "for")
            self.match("OPERATOR", "(")
            self.parse_ForInit()
            self.match("DELIMITER", ";")
            self.parse_B()
            self.match("DELIMITER", ";")
            self.parse_ForIter()
            self.match("OPERATOR", ")")
            self.parse_S()
            self._exit("for语句")
            return

        # do-while 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "do":
            self._enter("do-while语句")
            self.match("KEYWORD", "do")
            self.parse_S()
            self.match("KEYWORD", "while")
            self.match("OPERATOR", "(")
            self.parse_B()
            self.match("OPERATOR", ")")
            self.match("DELIMITER", ";")
            self._exit("do-while语句")
            return

        # break 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "break":
            self._enter("break语句")
            self.match("KEYWORD", "break")
            self.match("DELIMITER", ";")
            self._exit("break语句")
            return

        # continue语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "continue":
            self._enter("continue语句")
            self.match("KEYWORD", "continue")
            self.match("DELIMITER", ";")
            self._exit("continue语句")
            return

        # return 语句
        elif self.current_token.type == "KEYWORD" and self.current_token.value == "return":
            self._enter("return语句")
            self.match("KEYWORD", "return")
            self.parse_ReturnExpr()
            self.match("DELIMITER", ";")
            self._exit("return语句")
            return
        # 变量声明语句（type 开头）
        elif is_type(self.current_token.type, self.current_token.value):
            self.parse_D()
        else:
            self.error("Expected assignment, block, if, or declaration statement")

    # ForInit → id = B | D | ε 初始化条件
    def parse_ForInit(self):
        if self.current_token.type == "IDENTIFIER":
            self.match("IDENTIFIER")
            self.match("OPERATOR", "=")
            self.parse_B()
        elif is_type(self.current_token.type, self.current_token.value):
            # 只有声明初始化，这里只消费 type + id 列表，不要吃分号
            self.parse_type()
            self.parse_IDList()
        # ε 情况下什么都不做

    """
    ForIter → id CompAssign B       // e.g. i = expr
         | Prefix id            // e.g. ++i, --i
         | id Postfix           // e.g. i++, i--
         | ε
    """

    def parse_ForIter(self):
        """ForIter → id CompAssign B | Prefix id | id Postfix | ε"""
        # 1) 赋值迭代：id CompAssign B
        if (self.current_token
                and self.current_token.type == "IDENTIFIER"
                and self.peek_n()
                and self.peek_n().type == "OPERATOR"
                and self.peek_n().value in {"=", "+=", "-=", "*=", "/=", "%="}):
            self._enter("赋值迭代")
            self.match("IDENTIFIER")
            self.match("OPERATOR")  # =, +=, ...
            self.parse_B()
            self._exit("赋值迭代")
        # 2) 前缀 ++i / --i
        elif (self.current_token
              and self.current_token.type == "OPERATOR"
              and self.current_token.value in ("++", "--")):
            self._enter("前缀迭代")
            self.match("OPERATOR", self.current_token.value)
            self.match("IDENTIFIER")
            self._exit("前缀迭代")
        # 3) 后缀 i++ / i--
        elif (self.current_token
              and self.current_token.type == "IDENTIFIER"
              and self.peek_n()
              and self.peek_n().type == "OPERATOR"
              and self.peek_n().value in ("++", "--")):
            self._enter("后缀迭代")
            self.match("IDENTIFIER")
            self.match("OPERATOR", self.current_token.value)  # ++ or --
            self._exit("后缀迭代")
        # 4) ε：什么也不做
        else:
            return

    # ReturnExpr → B | ε              // 可选返回值
    def parse_ReturnExpr(self):
        if (self.current_token and
                (self.current_token.value == "!"
                 or self.current_token.value == "("
                 or self.current_token.type in ("IDENTIFIER", "LITERAL"))):
            self.parse_B()

    # D → ConstOpt type IDList ;
    # ConstOpt -> const | ε
    def parse_D(self,  is_const: bool = False):
        self._enter("声明语句")

        var_type = self.parse_type()  # ← 把类型记下来
        # 把 const 信息也传下去
        self.parse_IDList(var_type, is_const)
        self.match("DELIMITER", ";")
        self._exit("声明语句")

    # 处理类型
    def parse_type(self) -> str:
        if is_type(self.current_token.type, self.current_token.value):
            t = self.current_token.value
            self._enter("类型")
            self.match("KEYWORD")  # 吃掉 type
            self._exit("类型")
            return t
        else:
            self.error("Expected type keyword", use_token=self.current_token)

    # IDList → id IDInit IDList'
    def parse_IDList(self, var_type, is_const: bool = False):
        self._enter("标识符")
        # 第一个变量名称
        var_name = self.current_token.value
        line = self.current_token.line
        # 语义动作：检查同意作用域变量重定义
        if not self.check_var_redefine(var_name=var_name, var_type=var_type, line=line):
            # 类型有效性（一般不必，因为类型是从 KEYWORD 来的）
            self.symtab.add_variable(var_name, var_type,
                                     kind='CONST' if is_const else "variable",
                                     line=line)

        self.match("IDENTIFIER")
        # 传入 var_name 和 var_type
        self.parse_IDInit(var_name, var_type)
        self.parse_IDListTail(var_type)
        self._exit("标识符")

    # IDInit → = B | ε
    #   在这里做类型兼容检查
    def parse_IDInit(self, var_name: str, var_type: str):
        if self.current_token and self.current_token.value == "=":
            self._enter("初始化")
            self.match("OPERATOR", "=")
            rhs_type, _ = self.parse_B()  # ← 解包类型/值
            if not self.type_compatible(var_type, rhs_type):
                self.report_error(
                    f"[Semantic Error] Cannot initialize '{var_name}' of type '{var_type}' with '{rhs_type}' at line {self.current_token.line}"
                )
            self._exit("初始化")

    # IDList' → , id IDInit IDList' | ε
    def parse_IDListTail(self, var_type):
        while self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == ",":
            self._enter("继续声明")
            self.match("DELIMITER", ",")
            # 添加后续变量
            vname = self.current_token.value
            line = self.current_token.line
            # 进行重定义检查
            if not self.check_var_redefine(vname, var_type, line):
                self.symtab.add_variable(vname, var_type, kind='variable', line=line)
            self.match("IDENTIFIER")
            self.parse_IDInit()
            self._exit("继续声明")

    # S' → else S | ε
    def parse_S_prime(self):
        # 只有在下一个是 else 时才进入
        if (self.current_token
                and self.current_token.type == "KEYWORD"
                and self.current_token.value == "else"):
            self._enter("else分支")
            self.match("KEYWORD", "else")
            self.parse_S()
            self._exit("else分支")
        # 否则什么都不做（ε）

    # B → ( B ) B' | !B B' | R B'
    def parse_B(self) -> Tuple[str, Optional[Union[int, float]]]:
        """布尔表达式，返回 (类型, 常量值)；常量值对逻辑表达式总是 None。"""
        self._enter("布尔表达式")
        # 先处理布尔分组和一元 !
        if self.current_token.type == "OPERATOR" and self.current_token.value == "(":
            self.match("OPERATOR", "(")
            t, _ = self.parse_B()
            self.match("OPERATOR", ")")
            v = None
        elif self.current_token.type == "OPERATOR" and self.current_token.value == "!":
            self.match("OPERATOR", "!")
            t, _ = self.parse_B()
            if t != 'bool':
                self.report_error(
                    f"[Semantic] '!' operand must be bool, got {t} at line {self.last_token.line}"
                )
            t = 'bool'
            v = None
        else:
            t, _ = self.parse_R()
            v = None

        # 处理 && 和 ||
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("&&", "||")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            rhs_t, _ = self.parse_B()
            if t != 'bool' or rhs_t != 'bool':
                self.report_error(
                    f"[Semantic] logical '{op}' requires bool operands, got {t} and {rhs_t}"
                )
            t = 'bool'
            v = None

        self._exit("布尔表达式")
        return t, v

    # R → E R'
    # R' → relop E R' | ε
    def parse_R(self) -> Tuple[str, Optional[Union[int, float]]]:
        """关系表达式，返回 (类型, 常量值)；链式比较总是常量值 None。"""
        self._enter("关系表达式")
        # 先拿到左侧算术 expr
        lt, lv = self.parse_E()
        saw_relop = False

        # 处理一个或多个 relop E
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in (">", "<", ">=", "<=", "==", "!=")):
            saw_relop = True
            op = self.current_token.value
            self.match("OPERATOR", op)
            rt, _ = self.parse_E()
            if lt not in ("int", "float") or rt not in ("int", "float"):
                self.report_error(
                    f"[Semantic] relational '{op}' requires numeric operands, got {lt} and {rt}"
                )
            # 为了支持 a < b < c 链式比较，我们把 lt 更新为 rt
            lt, lv = rt, None

        self._exit("关系表达式")

        # 如果至少出现一次关系运算，结果是 bool，且不是编译期常量
        if saw_relop:
            return "bool", None
        # 否则就退回单纯的算术表达式
        return lt, lv

    # E → T E'
    # E' → + T E' | - T E' | ε
    def parse_E(self) -> Tuple[str, Optional[Union[int, float]]]:
        self._enter("算术表达式")
        lt, lv = self.parse_T()
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("+", "-")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            rt, rv = self.parse_T()
            # 类型提升
            tt = 'float' if 'float' in (lt, rt) else 'int'
            # 常量折叠
            if lv is not None and rv is not None:
                lv = lv + rv if op == "+" else lv - rv
            else:
                lv = None
            lt = tt
        self._exit("算术表达式")
        return lt, lv

    # T → F T'
    # T' → * F T' | / F' | ε
    # T → F T'
    # 改成返回 (类型, 常量值)
    def parse_T(self) -> Tuple[str, Optional[Union[int, float]]]:
        self._enter("项")
        # 先拿到 F 的 (类型, 常量值)
        lt, lv = self.parse_F()
        # 然后逐个处理 * / %
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("*", "/", "%")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            rt, rv = self.parse_F()
            # 除法／取余前做零检查
            if op in ("/", "%") and rv == 0:
                self.report_error(
                    f"[Semantic Error] Division or modulo by zero at line {self.last_token.line}"
                )
            # 类型提升
            tt = 'float' if 'float' in (lt, rt) else 'int'
            # 常量折叠
            if lv is not None and rv is not None:
                if op == "*":
                    lv = lv * rv
                elif op == "/":
                    lv = lv / rv
                else:
                    lv = lv % rv
            else:
                lv = None
            lt = tt
        self._exit("项")
        return lt, lv

    """
    F   → id ( ArgListOpt ) ;
    | ( R ) 
    | id Postfix 
    | Prefdaoix id 
    | literal
    Postfix → ++ | -- | ε
    Prefix  → ++ | -- | + | - 
    """

    def parse_F(self) -> Tuple[str, Optional[Union[int, float]]]:
        """因子，返回 (类型, 常量值或 None)。"""
        self._enter("因子")
        tok = self.current_token

        # 前缀 +、-
        if tok.type == "OPERATOR" and tok.value in ("+", "-"):
            op = tok.value
            self.match("OPERATOR", op)
            t, v = self.parse_F()
            # 常量折叠：如果 v 不为 None，就做 +/- 运算
            if v is not None:
                v = +v if op == "+" else -v
            self._exit("因子")
            return t, v

        # 函数调用，结果肯定不是编译期常量
        if tok.type == "IDENTIFIER" and self.peek_n().value == "(":
            name = tok.value
            self.match("IDENTIFIER")
            self.match("OPERATOR", "(")
            self.parse_ArgListOpt()
            self.match("OPERATOR", ")")
            sym = self.symtab.lookup_function(name)
            if not sym:
                self.report_error(f"[Semantic] call to undeclared function '{name}' at line {tok.line}")
                t = 'int'
            else:
                t = sym.type
            self._exit("因子")
            return t, None

        # 括号子表达式
        if tok.type == "OPERATOR" and tok.value == "(":
            self.match("OPERATOR", "(")
            t, v = self.parse_B()
            self.match("OPERATOR", ")")
            self._exit("因子")
            return t, v

        # 标识符，自增/自减后值就不再是常量了
        if tok.type == "IDENTIFIER":
            name = tok.value
            self.match("IDENTIFIER")
            sym = self.symtab.lookup_variable(name)
            if not sym:
                self.report_error(f"[Semantic Error] Use of undeclared variable '{name}' at line {tok.line}")
                t, v = 'int', None
            else:
                # 增加使用次数
                sym.increment()
                t, v = sym.type, getattr(sym, 'const_val', None)
            # 后缀 ++/--
            if self.current_token and self.current_token.type == "OPERATOR" and self.current_token.value in (
            "++", "--"):
                self.match("OPERATOR", self.current_token.value)
                # 变量经过自增以后，编译期就不再是常量
                v = None
            self._exit("因子")
            return t, v

        # 字面量
        if tok.type == "LITERAL":
            lit = tok.value
            self.match("LITERAL")
            # 类型与常量值
            if '.' in lit or 'e' in lit.lower():
                t, v = 'float', float(lit)
            elif lit in ('true', 'false'):
                t, v = 'bool', (lit == 'true')
            elif lit.startswith("'") and lit.endswith("'"):
                t, v = 'char', lit[1]  # or ord(...)
            else:
                t, v = 'int', int(lit)
            self._exit("因子")
            return t, v

        # 错误
        self.error("Expected factor")
        self._exit("因子")
        return 'int', None

    # ArgListOpt → ArgList | ε
    def parse_ArgListOpt(self):
        # 只有当看到可能的表达式起始符时，才 parse ArgList
        if (self.current_token and
                (self.current_token.value in ("!", "++", "--")
                 or self.current_token.value == "("
                 or self.current_token.type in ("IDENTIFIER", "LITERAL"))):
            self.parse_ArgList()
        # 否则 ε，什么都不做

    # ArgList → B ArgList’
    def parse_ArgList(self):
        # 先消费一个参数表达式
        self.parse_B()
        # 不额外判断，直接循环消费所有后续 “, expr”
        self.parse_ArgList_tail()

    # ArgList’ → , B ArgList’ | ε
    def parse_ArgList_tail(self):
        while (self.current_token.type == "DELIMITER" and
               self.current_token.value == ","):
            self.match("DELIMITER", ",")
            self.parse_B()
        # 为空不处理


# ----- 主程序入口 -----
if __name__ == "__main__":
    parser = SyntaxAnalyzer("./token/tokens.txt")
    parser.parse()
