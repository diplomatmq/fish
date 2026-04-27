import libcst as cst
import libcst.matchers as m

class DbCallTransformer(cst.CSTTransformer):
    def __init__(self):
        super().__init__()
        self.in_async_func = False
        self.async_func_depth = 0
        self.modified_count = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.asynchronous is not None:
            self.async_func_depth += 1
            self.in_async_func = True
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        if original_node.asynchronous is not None:
            self.async_func_depth -= 1
            if self.async_func_depth == 0:
                self.in_async_func = False
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.CSTNode:
        # checking if it's db.<method>(...)
        # and NOT already wrapped in _run_sync
        
        if not self.in_async_func:
            return updated_node
            
        def is_db_attr(node):
            return (
                isinstance(node, cst.Attribute) and 
                isinstance(node.value, cst.Name) and 
                node.value.value == 'db'
            )

        # Check if current call is db.something()
        if is_db_attr(updated_node.func):
            self.modified_count += 1
            
            # Reconstruct as await _run_sync(db.method, args...)
            
            # create Arg for db.method
            db_method_arg = cst.Arg(value=updated_node.func)
            
            # combined args
            new_args = [db_method_arg] + list(updated_node.args)
            
            # new call _run_sync(...)
            new_call = cst.Call(
                func=cst.Name("_run_sync"),
                args=new_args
            )
            
            # return Await(Call)
            return cst.Await(expression=new_call)
            
        return updated_node
        
with open('bot.py', 'r', encoding='utf-8') as f:
    source_code = f.read()
    
tree = cst.parse_module(source_code)
transformer = DbCallTransformer()
modified_tree = tree.visit(transformer)

print(f"Modifications made: {transformer.modified_count}")

with open('bot.py.new', 'w', encoding='utf-8') as f:
    f.write(modified_tree.code)
    
print("Saved to bot.py.new")
