from pycparser import CParser, c_ast
from graphviz import Digraph

code = open('../C_file/a.c').read()
ast  = CParser().parse(code)

dot = Digraph(node_attr={'shape':'box'})
node_count = 0

def add_node(node):
    global node_count
    uid = f'n{node_count}'; node_count += 1
    dot.node(uid, type(node).__name__)
    for child_name, child in node.children():
        cid = add_node(child)
        dot.edge(uid, cid, label=child_name)
    return uid

add_node(ast)
dot.render('ast_pycparser', format='png', cleanup=True)
