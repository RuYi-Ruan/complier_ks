# -*- coding: utf-8 -*-
from collections import namedtuple

# 简单的 AST 节点
class Node:
    def __init__(self, nodetype, children=None, token=None):
        self.type     = nodetype
        self.children = children or []
        self.token    = token
    def __repr__(self, level=0):
        indent = "  " * level
        s = f"{indent}{self.type}"
        if self.token:
            s += f" [{self.token.value}]"
        s += "\n"
        for c in self.children:
            if isinstance(c, Node):
                s += c.__repr__(level+1)
            else:
                s += "  "*(level+1) + repr(c) + "\n"
        return s

# —— Token, TokenStream 同你代码保持一致 ——
class Token:
    def __init__(self, line, col, token_type, value):
        self.line = int(line); self.col = int(col)
        self.type = token_type; self.value = value
    def __repr__(self):
        return f"Token({self.line}:{self.col},{self.type},{self.value})"

class TokenStream:
    def __init__(self, filename):
        self.tokens = self._load_tokens(filename)
        self.current = 0
    def _load_tokens(self, filename):
        arr = []
        with open(filename, encoding='utf-8') as f:
            for ln in f:
                if not ln.strip(): continue
                pos, ttype, val = ln.strip().split('\t')
                l,c = pos.split(':')
                arr.append(Token(l,c,ttype,val))
        return arr
    def next(self):
        if self.current < len(self.tokens):
            t = self.tokens[self.current]
            self.current += 1
            return t
        return None
    def peek(self, k=0):
        idx = self.current + k
        return self.tokens[idx] if idx < len(self.tokens) else None
    def reset(self):
        self.current = 0

# —— 递归下降解析器 ——
class SyntaxAnalyzer:
    def __init__(self, token_file):
        self.tok   = TokenStream(token_file)
        self.current_token = None
        self.errors = []
        self.last_token = None

    # —— 错误处理 ——
    def report_error(self, msg):
        self.errors.append(msg)

    def match(self, expected_type, expected_val=None):
        t = self.current_token
        if not t:
            self.report_error(f"Unexpected EOF, expected {expected_val or expected_type}")
            return None
        if t.type == expected_type and (expected_val is None or t.value == expected_val):
            self.last_token = t
            self.current_token = self.tok.next()
            return t
        else:
            got = f"{t.type}('{t.value}')"
            exp = expected_val or expected_type
            self.report_error(f"Expected {exp} but got {got} at {t.line}:{t.col}")
            # 同步：跳过一个 token，尝试继续
            self.current_token = self.tok.next()
            return None

    # 判断当前是否某个关键词
    def _check_kw(self, kw):
        return self.current_token and self.current_token.type=="KEYWORD" and self.current_token.value==kw

    # 判断是类型
    def _check_type(self):
        return self.current_token and self.current_token.type=="KEYWORD" and self.current_token.value in ("int","char","float","void")

    # —— 入口 ——
    def parse(self):
        self.current_token = self.tok.next()
        root = self.parse_程序()
        if self.current_token:
            self.report_error(f"Extra tokens after program: {self.current_token}")
        # 打印错误
        if self.errors:
            print("---- 语法错误列表 ----")
            for e in self.errors:
                print(" ", e)
        # 打印语法树
        print("---- 语法树 ----")
        print(root)
        return root

    # <程序> → main() <复合语句> <函数块>
    def parse_程序(self):
        node = Node("Program")
        node.children.append(self.match("KEYWORD","main"))
        self.match("DELIMITER","("); self.match("DELIMITER",")")
        node.children.append(self.parse_复合语句())
        node.children.append(self.parse_函数块())
        return node

    # <函数块> → <函数定义> <函数块> | ε
    def parse_函数块(self):
        node = Node("FunctionBlock")
        # 看下一个是不是函数定义的开头：Type id "("
        if self._check_type() and self.tok.peek(1) and self.tok.peek(1).type=="IDENTIFIER":
            node.children.append(self.parse_函数定义())
            node.children.append(self.parse_函数块())
        return node

    # <函数定义> → <函数类型> id "(" <函数定义形参列表>? ")" <复合语句>
    def parse_函数定义(self):
        node = Node("FunctionDef")
        node.children.append(self.parse_函数类型())
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        self.match("DELIMITER","(")
        # 形参列表
        if not self._check_kw(")"):
            node.children.append(self.parse_函数定义形参列表())
        self.match("DELIMITER",")")
        node.children.append(self.parse_复合语句())
        return node

    # <函数类型> → int|char|float|void
    def parse_函数类型(self):
        t = self.match("KEYWORD")  # 值由 match 检查
        return Node("FuncType", token=t)

    # <函数定义形参列表> → <变量类型> id <形参列表尾>
    def parse_函数定义形参列表(self):
        node = Node("ParamList")
        node.children.append(self.parse_变量类型())
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        node.children.append(self.parse_形参列表尾())
        return node

    # <形参列表尾> → "," <函数定义形参列表> | ε
    def parse_形参列表尾(self):
        node = Node("ParamListTail")
        if self.match("DELIMITER",","):
            node.children.append(self.parse_函数定义形参列表())
        return node

    # <变量类型> → int|char|float
    def parse_变量类型(self):
        t = self.match("KEYWORD")
        return Node("VarType", token=t)

    # <复合语句> → "{" <语句表>? "}"
    def parse_复合语句(self):
        node = Node("CompoundStmt")
        self.match("DELIMITER","{")
        # 可选语句表
        if not (self.current_token and self.current_token.type=="DELIMITER" and self.current_token.value=="}"):
            node.children.append(self.parse_语句表())
        self.match("DELIMITER","}")
        return node

    # <语句表> → <语句> <语句表>?
    def parse_语句表(self):
        node = Node("StmtList")
        node.children.append(self.parse_语句())
        # 递归
        if not (self.current_token and self.current_token.type=="DELIMITER" and self.current_token.value=="}"):
            node.children.append(self.parse_语句表())
        return node

    # <语句> → <声明语句> | <执行语句>
    def parse_语句(self):
        if self._check_type() or self._check_kw("const"):
            return self.parse_声明语句()
        elif self._check_kw("if") or self._check_kw("while") or self._check_kw("do") or self._check_kw("for")\
             or self._check_kw("return") or self._check_kw("break") or self._check_kw("continue")\
             or (self.current_token.type=="IDENTIFIER"):
            return self.parse_执行语句()
        else:
            self.report_error(f"Unknown stmt start: {self.current_token}")
            # 跳过一个 token 同步
            self.current_token = self.tok.next()
            return Node("ErrorStmt")

    # <声明语句> → <值声明> ";" | <函数声明> ";"
    def parse_声明语句(self):
        node = Node("DeclStmt")
        # 区分常量、变量、函数声明
        if self._check_kw("const") or self._check_type():
            # 先保存当前位置，看下后面是否是 IDENTIFIER "(" → 函数声明
            if self._check_type() and self.tok.peek(1) and self.tok.peek(1).type=="IDENTIFIER" and self.tok.peek(2).value=="(":
                node.children.append(self.parse_函数声明())
            else:
                node.children.append(self.parse_值声明())
        else:
            self.report_error("Bad decl")
        self.match("DELIMITER",";")
        return node

    # <值声明> → const <常量类型> <常量声明表> | <变量类型> <变量声明表>
    def parse_值声明(self):
        node = Node("ValueDecl")
        if self._check_kw("const"):
            node.children.append(Node("const", token=self.match("KEYWORD","const")))
            node.children.append(Node("ConstType", token=self.match("KEYWORD")))
            node.children.append(self.parse_常量声明表())
        else:
            node.children.append(self.parse_变量类型())
            node.children.append(self.parse_变量声明表())
        return node

    # <常量声明表> → id "=" <常量> <常量表尾>
    def parse_常量声明表(self):
        node = Node("ConstDeclList")
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        self.match("OPERATOR","=")
        node.children.append(self.parse_常量())
        node.children.append(self.parse_常量表尾())
        return node

    def parse_常量表尾(self):
        node = Node("ConstListTail")
        if self.match("DELIMITER",","):
            node.children.append(self.parse_常量声明表())
        return node

    def parse_常量(self):
        if self.current_token.type=="LITERAL" or self.current_token.type=="NUMBER":
            return Node("Literal", token=self.match(self.current_token.type))
        else:
            self.report_error(f"Bad constant at {self.current_token}")
            self.current_token = self.tok.next()
            return Node("ErrorLit")

    # <变量声明表> → <单变量声明> <变量表尾>
    def parse_变量声明表(self):
        node = Node("VarDeclList")
        node.children.append(self.parse_单变量声明())
        node.children.append(self.parse_变量表尾())
        return node

    def parse_变量表尾(self):
        node = Node("VarListTail")
        if self.match("DELIMITER",","):
            node.children.append(self.parse_变量声明表())
        return node

    def parse_单变量声明(self):
        node = Node("VarDecl")
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        if self.match("OPERATOR","="):
            node.children.append(self.parse_表达式())
        return node

    # <函数声明> → <函数类型> id "(" <函数声明形参列表>? ")"
    def parse_函数声明(self):
        node = Node("FuncDecl")
        node.children.append(self.parse_函数类型())
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        self.match("DELIMITER","(")
        if not self._check_kw(")"):
            node.children.append(self.parse_函数声明形参列表())
        self.match("DELIMITER",")")
        return node

    # <函数声明形参列表> 与 定义形参类似
    def parse_函数声明形参列表(self):
        node = Node("ParamList")
        node.children.append(self.parse_变量类型())
        node.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
        # 复用形参尾
        node.children.append(self.parse_声明形参尾())
        return node

    def parse_声明形参尾(self):
        node = Node("ParamListTail")
        if self.match("DELIMITER",","):
            node.children.append(self.parse_函数声明形参列表())
        return node

    # <执行语句>
    def parse_执行语句(self):
        if self._check_kw("if"):
            return self.parse_if语句()
        if self._check_kw("while"):
            return self.parse_while语句()
        if self._check_kw("do"):
            return self.parse_doWhile语句()
        if self._check_kw("for"):
            return self.parse_for语句()
        if self._check_kw("return"):
            return self.parse_return语句()
        if self._check_kw("break"):
            n = Node("Break", token=self.match("KEYWORD","break")); self.match("DELIMITER",";"); return n
        if self._check_kw("continue"):
            n = Node("Continue", token=self.match("KEYWORD","continue")); self.match("DELIMITER",";"); return n
        # 标识符开头：赋值或函数调用
        if self.current_token.type=="IDENTIFIER":
            # 先记住 id
            idtok = self.match("IDENTIFIER")
            # 函数调用?
            if self._check_kw(None) or self.current_token.value=="(":
                # 恢复 id 作为子节点
                node = Node("FuncCall")
                node.children.append(Node("Identifier", token=idtok))
                self.match("DELIMITER","(")
                if not self.current_token.value==")":
                    node.children.append(self.parse_实参列表())
                self.match("DELIMITER",")"); self.match("DELIMITER",";")
                return node
            else:
                # 赋值
                node = Node("Assign")
                node.children.append(Node("Identifier", token=idtok))
                self.match("OPERATOR","=")
                node.children.append(self.parse_表达式())
                self.match("DELIMITER",";")
                return node
        # 其它强行跳过
        self.report_error(f"Unknown exec stmt at {self.current_token}")
        self.current_token = self.tok.next()
        return Node("ErrorExec")

    # if, while, do-while, for, return
    def parse_if语句(self):
        n = Node("IfStmt")
        self.match("KEYWORD","if"); self.match("DELIMITER","(")
        n.children.append(self.parse_表达式())
        self.match("DELIMITER",")")
        n.children.append(self.parse_语句())
        if self._check_kw("else"):
            self.match("KEYWORD","else")
            n.children.append(self.parse_语句())
        return n

    def parse_while语句(self):
        n = Node("WhileStmt")
        self.match("KEYWORD","while"); self.match("DELIMITER","(")
        n.children.append(self.parse_表达式()); self.match("DELIMITER",")")
        n.children.append(self.parse_语句())
        return n

    def parse_doWhile语句(self):
        n = Node("DoWhileStmt")
        self.match("KEYWORD","do")
        n.children.append(self.parse_语句())
        self.match("KEYWORD","while"); self.match("DELIMITER","(")
        n.children.append(self.parse_表达式()); self.match("DELIMITER",")"); self.match("DELIMITER",";")
        return n

    def parse_for语句(self):
        n = Node("ForStmt")
        self.match("KEYWORD","for"); self.match("DELIMITER","(")
        # init
        if self._check_type() or self.current_token.type=="IDENTIFIER":
            # 变量声明 or 赋值
            if self._check_type():
                n.children.append(self.parse_变量类型())
                n.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
                if self.match("OPERATOR","="):
                    n.children.append(self.parse_表达式())
                self.match("DELIMITER",";")
            else:
                # 赋值
                n.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
                self.match("OPERATOR","=")
                n.children.append(self.parse_表达式()); self.match("DELIMITER",";")
        else:
            self.match("DELIMITER",";")
        # cond
        if not self.current_token.value==";":
            n.children.append(self.parse_表达式())
        self.match("DELIMITER",";")
        # update
        if not self.current_token.value==")":
            n.children.append(self.parse_表达式())
        self.match("DELIMITER",")")
        n.children.append(self.parse_语句())
        return n

    def parse_return语句(self):
        n = Node("ReturnStmt")
        self.match("KEYWORD","return")
        if not self.current_token.value==";":
            n.children.append(self.parse_表达式())
        self.match("DELIMITER",";")
        return n

    # <实参列表> → <表达式> { "," <表达式> }
    def parse_实参列表(self):
        n = Node("ArgList")
        n.children.append(self.parse_表达式())
        while self.match("DELIMITER",","):
            n.children.append(self.parse_表达式())
        return n

    # <表达式> → <赋值表达式>
    def parse_表达式(self):
        return self.parse_赋值表达式()

    # <赋值表达式> → id "=" <赋值表达式> | <逻辑或表达式>
    def parse_赋值表达式(self):
        # 先看第二个 token 是不是 "="
        if self.current_token.type=="IDENTIFIER" and self.tok.peek(1) and self.tok.peek(1).value=="=":
            n = Node("AssignExpr")
            n.children.append(Node("Identifier", token=self.match("IDENTIFIER")))
            self.match("OPERATOR","=")
            n.children.append(self.parse_赋值表达式())
            return n
        else:
            return self.parse_逻辑或()

    # 以下各层按照 { A (op A)* }
    def parse_逻辑或(self):
        n = self.parse_逻辑与()
        while self.match("OPERATOR","||"):
            parent = Node("LogicalOr", [n])
            parent.children.append(self.parse_逻辑与())
            n = parent
        return n

    def parse_逻辑与(self):
        n = self.parse_等值()
        while self.match("OPERATOR","&&"):
            parent = Node("LogicalAnd", [n])
            parent.children.append(self.parse_等值())
            n = parent
        return n

    def parse_等值(self):
        n = self.parse_关系()
        while self.current_token and self.current_token.type=="OPERATOR" and self.current_token.value in ("==","!="):
            op = self.current_token.value
            self.match("OPERATOR",op)
            parent = Node("Equality", [n])
            parent.children.append(self.parse_关系())
            n = parent
        return n

    def parse_关系(self):
        n = self.parse_算术()
        while self.current_token and self.current_token.type=="OPERATOR" and self.current_token.value in ("<",">","<=",">="):
            op = self.current_token.value
            self.match("OPERATOR",op)
            parent = Node("Relational", [n])
            parent.children.append(self.parse_算术())
            n = parent
        return n

    def parse_算术(self):
        n = self.parse_项()
        while self.current_token and self.current_token.type=="OPERATOR" and self.current_token.value in ("+","-"):
            op = self.current_token.value
            self.match("OPERATOR",op)
            parent = Node("Add", [n])
            parent.children.append(self.parse_项())
            n = parent
        return n

    def parse_项(self):
        n = self.parse_因子()
        while self.current_token and self.current_token.type=="OPERATOR" and self.current_token.value in ("*","/","%"):
            op = self.current_token.value
            self.match("OPERATOR",op)
            parent = Node("Mul", [n])
            parent.children.append(self.parse_因子())
            n = parent
        return n

    def parse_因子(self):
        if self.match("DELIMITER","("):
            expr = self.parse_表达式()
            self.match("DELIMITER",")")
            return expr
        if self.current_token.type=="IDENTIFIER":
            idt = self.match("IDENTIFIER")
            node = Node("Identifier", token=idt)
            # 后缀: 函数调用或数组
            while self.current_token and self.current_token.value in ("(", "["):
                if self.match("DELIMITER","("):
                    call = Node("FuncCall",[node])
                    if self.current_token.value != ")":
                        call.children.append(self.parse_实参列表())
                    self.match("DELIMITER",")")
                    node = call
                elif self.match("DELIMITER","["):
                    arr = Node("ArrayRef",[node, self.parse_表达式()])
                    self.match("DELIMITER","]")
                    node = arr
            return node
        if self.current_token.type in ("NUMBER","LITERAL"):
            tok = self.match(self.current_token.type)
            return Node("Literal", token=tok)
        # 都不对
        self.report_error(f"Bad factor at {self.current_token}")
        self.current_token = self.tok.next()
        return Node("ErrorFactor")

# ———— 主程序 ————
if __name__ == "__main__":
    parser = SyntaxAnalyzer("./token/tokens.txt")
    parser.parse()
