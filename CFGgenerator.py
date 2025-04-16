from pycparser import c_parser, c_ast
import argparse

class CFGNode:
    def __init__(self, id, label=None):
        self.id = id
        self.label = label
        self.edges = []
        self.parent = []
    
    def add_edge(self, node):
        if node is not None and node not in self.edges:
            self.edges.append(node)
    
    def __repr__(self):
        return f"Node {self.id}: {self.label} -> {[n.id for n in self.edges]}"

class CFGBuilder(c_ast.NodeVisitor):
    def __init__(self):
        self.cfg = []
        self.current_node = None
        self.node_counter = 0
        self.entry_node = None
        self.exit_node = None
        self.break_nodes = []
        self.continue_nodes = []
    
    def new_node(self, label=None):
        node = CFGNode(self.node_counter, label)
        self.node_counter += 1
        self.cfg.append(node)
        return node
    
    def build(self, ast):
        for node in ast.ext:
            if isinstance(node, c_ast.FuncDef):
                self.visit(node)
        return self.cfg
    
    def visit_FuncDef(self, node):
        entry_node = self.new_node(f"Entry: {node.decl.name}")
        self.entry_node = entry_node
        self.current_node = entry_node
        
        self.visit(node.body)
        
        if not self.exit_node:
            exit_node = self.new_node(f"Exit: {node.decl.name}")
            if self.current_node:
                self.current_node.add_edge(exit_node)
                exit_node.parent.append(self.current_node)
            self.current_node = exit_node
            self.exit_node = exit_node
    
    def visit_Compound(self, node):
        if node.block_items:
            for item in node.block_items:
                self.visit(item)
    
    def visit_Decl(self, node):
        if node.init:       # no need to create node if variable is not initialized
            label = f"Decl: {node.name} = {self.get_expr_str(node.init)}"
            new_node = self.new_node(label)
            if self.current_node:
                new_node.parent.append(self.current_node)
                self.current_node.add_edge(new_node)
            self.current_node = new_node
    
    def visit_If(self, node):
        cond_node = self.new_node(f"If: {self.get_expr_str(node.cond)}")
        if self.current_node:
            self.current_node.add_edge(cond_node)
            cond_node.parent.append(self.current_node)
        
        after_if_node = self.new_node("After If")
        
        self.current_node = cond_node
        then_entry = self.new_node("Then")
        if cond_node:
            cond_node.add_edge(then_entry)
            then_entry.parent.append(cond_node)
        self.current_node = then_entry
        self.visit(node.iftrue)
        if self.current_node:
            self.current_node.add_edge(after_if_node)
            after_if_node.parent.append(self.current_node)
        
        if node.iffalse:
            self.current_node = cond_node
            else_entry = self.new_node("Else")
            if cond_node:
                cond_node.add_edge(else_entry)
                else_entry.parent.append(cond_node)
            self.current_node = else_entry
            self.visit(node.iffalse)
            if self.current_node:
                self.current_node.add_edge(after_if_node)
                after_if_node.parent.append(self.current_node)
                
        elif cond_node:         # when the condition is fase and where is not else branch
            cond_node.add_edge(after_if_node)
            after_if_node.parent.append(cond_node)
        
        self.current_node = after_if_node
    
    def visit_For(self, node):
        if node.init:
            self.visit(node.init)
        
        loop_cond = self.new_node(f"For: {self.get_expr_str(node.cond)}" if node.cond else "For: (always)")
        if self.current_node:
            self.current_node.add_edge(loop_cond)
            loop_cond.parent.append(self.current_node)
        
        after_loop = self.new_node("After For")
        
        self.break_nodes.append(after_loop)
        self.continue_nodes.append(loop_cond)
        
        self.current_node = loop_cond
        body_entry = self.new_node("For Body")
        if loop_cond:
            loop_cond.add_edge(body_entry)
            body_entry.parent.append(loop_cond)
        self.current_node = body_entry
        self.visit(node.stmt)
        
        if node.next:
            increment_node = self.new_node(f"Increment: {self.get_expr_str(node.next)}")
            if self.current_node:  # Connect from body end to increment
                self.current_node.add_edge(increment_node)
                increment_node.parent.append(self.current_node)
            self.current_node = increment_node
        
        if self.current_node and loop_cond:  
            self.current_node.add_edge(loop_cond)
            loop_cond.parent.append(self.current_node)
        
        self.break_nodes.pop()
        self.continue_nodes.pop()
        
        if loop_cond:       # if the loop condition is false
            loop_cond.add_edge(after_loop)
            after_loop.parent.append(loop_cond)
        
        self.current_node = after_loop
    
    def visit_While(self, node):
        loop_cond = self.new_node(f"While: {self.get_expr_str(node.cond)}")
        if self.current_node:
            self.current_node.add_edge(loop_cond)
            loop_cond.parent.append(self.current_node)
        
        after_loop = self.new_node("After While")
        
        self.break_nodes.append(after_loop)
        self.continue_nodes.append(loop_cond)
        
        self.current_node = loop_cond
        body_entry = self.new_node("While Body")
        if loop_cond:
            loop_cond.add_edge(body_entry)
            body_entry.parent.append(loop_cond)
        self.current_node = body_entry
        self.visit(node.stmt)
        
        if self.current_node and loop_cond:
            self.current_node.add_edge(loop_cond)
            loop_cond.parent.append(self.current_node)
        
        self.break_nodes.pop()
        self.continue_nodes.pop()
        
        if loop_cond:
            loop_cond.add_edge(after_loop)
            after_loop.parent.append(loop_cond)
        
        self.current_node = after_loop
    
    def visit_DoWhile(self, node):
        body_entry = self.new_node("Do-While Body")
        if self.current_node:
            self.current_node.add_edge(body_entry)
            body_entry.parent.append(self.current_node)
        
        after_loop = self.new_node("After Do-While")
        
        self.break_nodes.append(after_loop)
        self.continue_nodes.append(body_entry)
        
        self.current_node = body_entry
        self.visit(node.stmt)
        
        if self.current_node:
            loop_cond = self.new_node(f"Do-While: {self.get_expr_str(node.cond)}")
            self.current_node.add_edge(loop_cond)
            loop_cond.parent.append(self.current_node)
            
            if loop_cond:
                loop_cond.add_edge(body_entry)
                body_entry.parent.append(loop_cond)
                loop_cond.add_edge(after_loop)
                after_loop.parent.append(loop_cond)
            
        self.break_nodes.pop()
        self.continue_nodes.pop()
        
        self.current_node = after_loop
    
    def visit_Switch(self, node):
        switch_node = self.new_node(f"Switch: {self.get_expr_str(node.cond)}")
        if self.current_node:
            self.current_node.add_edge(switch_node)
            switch_node.parent.append(self.current_node)
        
        after_switch = self.new_node("After Switch")
        
        self.break_nodes.append(after_switch)
        
        self.current_node = switch_node
        self.visit(node.stmt)
        
        if self.current_node and self.current_node != after_switch:
            self.current_node.add_edge(after_switch)
            after_switch.parent.append(self.current_node)
        
        self.break_nodes.pop()
        
        self.current_node = after_switch
    
    def visit_Case(self, node):
        case_node = self.new_node(f"Case: {self.get_expr_str(node.expr)}")
        if self.current_node:
            self.current_node.add_edge(case_node)
            case_node.parent.append(self.current_node)
        self.current_node = case_node
        
        for stmt in node.stmts:
            self.visit(stmt)
    
    def visit_Default(self, node):
        default_node = self.new_node("Default:")
        if self.current_node:
            self.current_node.add_edge(default_node)
            default_node.parent.append(self.current_node)
        self.current_node = default_node
        
        for stmt in node.stmts:
            self.visit(stmt)
    
    def visit_Break(self, node):
        if self.break_nodes:
            break_target = self.break_nodes[-1]
            if self.current_node:
                self.current_node.add_edge(break_target)
                self.break_nodes[-1].parent.append(self.current_node)
            self.current_node = None
    
    def visit_Continue(self, node):
        if self.continue_nodes:
            continue_target = self.continue_nodes[-1]
            if self.current_node:
                self.current_node.add_edge(continue_target)
                self.break_nodes[-1].parent.append(self.current_node)
            self.current_node = None
    
    def visit_Return(self, node):
        label = f"Return {self.get_expr_str(node.expr)}" if node.expr else "Return"
        return_node = self.new_node(label)
        if self.current_node:
            self.current_node.add_edge(return_node)
            return_node.parent.append(self.current_node)
        self.exit_node = return_node
        self.current_node = None
    
    def visit_Assignment(self, node):
        label = f"{self.get_expr_str(node.lvalue)} = {self.get_expr_str(node.rvalue)}"
        new_node = self.new_node(label)
        if self.current_node:
            self.current_node.add_edge(new_node)
            new_node.parent.append(self.current_node)
        self.current_node = new_node
    
    def get_expr_str(self, expr):
        if isinstance(expr, c_ast.Constant):
            return expr.value
        elif isinstance(expr, c_ast.ID):
            return expr.name
        elif isinstance(expr, c_ast.BinaryOp):
            return f"{self.get_expr_str(expr.left)} {expr.op} {self.get_expr_str(expr.right)}"
        elif isinstance(expr, c_ast.UnaryOp):
            return f"{expr.op}{self.get_expr_str(expr.expr)}"
        elif isinstance(expr, c_ast.FuncCall):
            args = ", ".join(self.get_expr_str(arg) for arg in expr.args.exprs) if expr.args else ""
            return f"{self.get_expr_str(expr.name)}({args})"
        elif isinstance(expr, c_ast.ArrayRef):
            return f"{self.get_expr_str(expr.name)}[{self.get_expr_str(expr.subscript)}]"
        return str(expr)
    
    def print_cfg(self, file):
        with open(file, 'w') as f:
            for node in self.cfg:
                f.write(f"{node}\n")
            
    def isSquashInsn(self, node):
        if not isinstance(node, CFGNode) or not node.label:
            return False

        label = node.label.lower()

        return (
            label.startswith("if:") or
            label.startswith("while:") or
            label.startswith("do-while:") or
            label.startswith("for:") or
            ("load" in label)
        )


    def genSS(self, node, cfg_nodes):
        
        SS = set()
        for i, cfg_node in enumerate(cfg_nodes):
            if i>0 and self.isSquashInsn(cfg_nodes[i-1]):
                continue
            if cfg_node.id >= node.id:
                break
            if self.isSquashInsn(cfg_node):
                if(cfg_nodes[i+1].edges[0].id <= node.id):
                    SS.add(cfg_node)

        return [n.label for n in SS]


def main():
    
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--file", help="Path to the C file to parse")
    argparser.add_argument("--show-cfg", action="store_true", help="Show CFG")
    argparser.add_argument("--show-ast", action="store_true", help="Show AST")
    args = argparser.parse_args()
    
    if args.file:
        with open(args.file, 'r') as f:
            code = f.read()
    else:
        assert False, "No C file provided. Use --file to specify a C file."

    ast_file = args.file + ".ast"
    cfg_file = args.file + ".cfg"
    ss_file = args.file + ".ss"

    parser = c_parser.CParser()
    ast = parser.parse(code)

    cfg_builder = CFGBuilder()
    cfg = cfg_builder.build(ast)
    
    if args.show_ast:
        with open(ast_file, 'w') as f:
            ast.show(buf=f)
    
    if args.show_cfg:
        cfg_builder.print_cfg(cfg_file)
    
    cfg = cfg_builder.build(ast)
    
    with open(ss_file, 'w') as f:
        for i, node in enumerate(cfg):
            if i > len(cfg)/2:
                break
            ss = cfg_builder.genSS(node, cfg)
            f.write(f"Safe Set for {node.label}: {ss}\n")

    
if __name__ == "__main__":
    main()