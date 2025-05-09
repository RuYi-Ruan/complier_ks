# 定义 Token 类，用于封装一个词法单元的信息
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


# 判断是否符合type
def is_type(type, value):
    return type == "KEYWORD" and value in {"int", "float", "bool", "char", "double", "void"}


# 语法分析器
class SyntaxAnalyzer:
    def __init__(self, token_file="./token/tokens.txt"):
        self.tok = TokenStream(token_file)
        self.current_token = None
        self.indent = 0
        self.errors = []  # 用来收集错误
        self.last_token = None  # 记录上一个消费的 token,用于指定错误语句的行号

    def peek_n(self, n=0):
        """
        返回从 current_token 开始，向前看第 n 个 token，但不移动指针。
        peek_n(0) == self.current_token
        peek_n(1) == 下一个要 next() 的 token
        依此类推
        """
        return self.tok.peek(n)

    def _peek_third(self):
        """返回当前单词的后一个单词"""


    # 语法树缩进
    def _log(self, msg):
        print("--" * self.indent + msg)

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

    # 语法分析入口
    def parse(self):
        # 开始分析
        self.current_token = self.tok.next()
        try:
            self.parse_P()
        except SyntaxError as e:
            self.report_error(e)

        if self.current_token is not None:
            self.report_error(f"Extra input after end of top-level block: {self.current_token}")

        print("—— 解析结束 ——")
        if self.errors:
            print("发现以下语法错误：")
            for e in self.errors:
                print(" ", e)

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

                if self.current_token.type == "KEYWORD":
                    self.match("KEYWORD")
                self.match("IDENTIFIER", "main")
                self.match("OPERATOR", "(")
                self.parse_ParamListOpt()
                self.match("OPERATOR", ")")
                if self.current_token.value == "{":
                    self.match("DELIMITER", "{")
                    self.parse_L()
                    self.match("DELIMITER", "}")
                    self._exit("main 函数")
                    return
                else:
                    self.error("Expected '{' after main function declaration")
                return

            elif is_type(self.current_token.type, self.current_token.value):
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
                        self.parse_D()
                    else:
                        self.error(f"Unexpected token {t3} after type+id")
                else:
                    self.error("Expected identifier after type")

                return

            elif self.current_token.type == "DELIMITER" and self.current_token.value == "{":
                self._enter("块")
                self.match("DELIMITER", "{")
                self.parse_L()
                self.match("DELIMITER", "}")
                self._exit("块")
                return
        else:
            self.error("Expect FunDef or block")

    # FunDef → type id (ParamListOpt) {L}
    def parse_FunDef(self):
        if is_type(self.current_token.type, self.current_token.value):
            self._enter("函数定义")
            self.match("KEYWORD")
            self.match("IDENTIFIER")
            self.match("OPERATOR", "(")
            self.parse_ParamListOpt()
            self.match("OPERATOR", ")")

            if self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == ";":
                self._enter("函数声明")
                self.match("DELIMITER", ";")  # 函数声明
                self._exit("函数声明")
            elif self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == "{":
                self.match("DELIMITER", "{")
                self.parse_L()
                self.match("DELIMITER", "}")
            else:
                self.error("Expected ';' or '{' after function signature", use_token=self.current_token)
            self._exit("函数定义")
            return

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
        # 一定要有类型
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
            self.match("IDENTIFIER")
            if (self.current_token is not None and
                    self.current_token.type == "OPERATOR" and
                    self.current_token.value in {"=", "+=", "-=", "*=", "/=", "%="}):
                self.match("OPERATOR")
                self.parse_B()
                self.match("DELIMITER", ";")
                self._exit("赋值语句")
            else:
                self.error("Expected assignment operator (=, +=, -=, *=, /=, %=)")
            return

        # 块语句
        elif self.current_token.type == "DELIMITER" and self.current_token.value == "{":
            self.parse_P()
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
        elif (is_type(self.current_token.type, self.current_token.value)):
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

    # D → type IDList ;
    def parse_D(self):
        self._enter("声明语句")
        self.parse_type()
        self.parse_IDList()
        self.match("DELIMITER", ";")
        self._exit("声明语句")

    def parse_type(self):
        if is_type(self.current_token.type, self.current_token.value):
            self._enter("类型")
            self.match("KEYWORD")  # 匹配 type
            self._exit("类型")
        else:
            self.error("Expected type keyword (int, float, bool, char, double)")

    # IDList → id IDInit IDList'
    def parse_IDList(self):
        self._enter("标识符")
        self.match("IDENTIFIER")
        self.parse_IDInit()
        self.parse_IDListTail()
        self._exit("标识符")

    # IDInit → = B | ε
    def parse_IDInit(self):
        if self.current_token and self.current_token.type == "OPERATOR" and self.current_token.value == "=":
            self._enter("初始化")
            self.match("OPERATOR", "=")
            self.parse_B()
            self._exit("初始化")
        # ε 情况无需处理（可选）

    # IDList' → , id IDInit IDList' | ε
    def parse_IDListTail(self):
        while self.current_token and self.current_token.type == "DELIMITER" and self.current_token.value == ",":
            self._enter("继续声明")
            self.match("DELIMITER", ",")
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
    def parse_B(self):
        self._enter("布尔表达式")
        # 先处理布尔分组
        # 如果是 '(' 开头，就把整个 B 包在里面
        if (self.current_token.type == "OPERATOR"
                and self.current_token.value == "("):
            self.match("OPERATOR", "(")
            self.parse_B()
            self.match("OPERATOR", ")")
        # 一元运算符 ‘!’
        elif (self.current_token.type == "OPERATOR"
              and self.current_token.value == "!"):
            self.match("OPERATOR", "!")
            self.parse_B()
        # 否则走关系表达式
        else:
            self.parse_R()

        # 然后匹配零次或多次的 && 或 ||
        self.parse_B_prime()
        self._exit("布尔表达式")

    # B' → && B B' | || B B' | ε
    def parse_B_prime(self):
        self._enter("布尔表达式'")
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("&&", "||")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            # 这里必须用 parse_B()，而不是 parse_R()
            # 因为后面可能是 ! 前缀，或嵌套的逻辑连接
            self.parse_B()
        self._exit("布尔表达式'")

    # R → E R'
    def parse_R(self):
        self._enter("关系表达式")
        self.parse_E()
        self.parse_R_prime()
        self._exit("关系表达式")

    # R' → relop E R' | ε
    def parse_R_prime(self):
        self._enter("关系表达式'")
        # 只要下一个 token 是关系运算符就循环
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in (">", "<", ">=", "<=", "==", "!=")):
            rel = self.current_token.value
            self.match("OPERATOR", rel)
            self.parse_E()
        self._exit("关系表达式'")

    # E → T E'
    def parse_E(self):
        self._enter("算术表达式")
        self.parse_T()
        self.parse_E_prime()
        self._exit("算术表达式")

    # E' → + T E' | - T E' | ε
    def parse_E_prime(self):
        self._enter("算术表达式'")
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("+", "-")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            self.parse_T()
        self._exit("算术表达式'")

    # T → F T'
    def parse_T(self):
        self._enter("项")
        self.parse_F()
        self.parse_T_prime()
        self._exit("项")

    # T' → * F T' | / F' | ε
    def parse_T_prime(self):
        self._enter("项'")
        while (self.current_token
               and self.current_token.type == "OPERATOR"
               and self.current_token.value in ("*", "/", "%")):
            op = self.current_token.value
            self.match("OPERATOR", op)
            self.parse_F()
        self._exit("项'")

    """
    F   → id ( ArgListOpt ) ;
    | ( R ) 
    | id Postfix 
    | Prefix id 
    | literal
    Postfix → ++ | -- | ε
    Prefix  → ++ | -- | + | - 
    """

    def parse_F(self):
        self._enter("因子")
        # 一元 + / - —— #
        if (self.current_token.type == "OPERATOR"
                and self.current_token.value in ("+", "-")):
            # 将 -x 或 +x 当成 Prefix F
            op = self.current_token.value
            self.match("OPERATOR", op)
            self.parse_F()
            self._exit("因子")
            return

        # 函数调用
        if (self.current_token.type == "IDENTIFIER" and
                self.peek_n().type == "OPERATOR"
                and self.peek_n().value == "("):
            self._enter("函数调用")
            self.match("IDENTIFIER")
            self.match("OPERATOR", "(")
            self.parse_ArgListOpt()
            self.match("OPERATOR", ")")
            self._exit("函数调用")
            self._exit("因子")
            return

        # 括号子表达式
        elif self.current_token.type == "OPERATOR" and self.current_token.value == "(":
            self.match("OPERATOR", "(")
            self.parse_R()
            self.match("OPERATOR", ")")

        # 前缀自增/自减
        elif (self.current_token.type == "OPERATOR"
              and self.current_token.value in ("++", "--")):
            # Prefix id
            op = self.current_token.value
            self.match("OPERATOR", op)
            self.match("IDENTIFIER")

        # 标识符，可能带后缀自增/自减
        elif self.current_token.type == "IDENTIFIER":
            self.match("IDENTIFIER")
            # Postfix 可选
            if (self.current_token.type == "OPERATOR"
                    and self.current_token.value in ("++", "--")):
                op = self.current_token.value
                self.match("OPERATOR", op)
            # 字面量
        elif self.current_token.type == "LITERAL":
            self.match("LITERAL")
        else:
            self.error("Expected '(', identifier (with optional ++/--), or literal")

        self._exit("因子")

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
