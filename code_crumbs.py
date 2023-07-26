import ast
import astor
import os
import sys
import re
import argparse

def process_file(file_path, root_dir, args):
    with open(file_path, 'r') as file:
        source = file.read()

    root = ast.parse(source)
    info = []
    for node in ast.walk(root):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            prefix = f"{os.path.relpath(file_path, root_dir)}/{node.lineno}"
            flags = []
            if isinstance(node, ast.FunctionDef):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                    flags.append('L')  # single line function
                if any(isinstance(decorator, ast.Call) for decorator in node.decorator_list):
                    flags.append('D')  # function has decorators
                if any(isinstance(decorator, ast.Str) for decorator in node.decorator_list):
                    flags.append('C')  # function has comment on the same line
                argus = [arg.arg for arg in node.args.args]
            else:
                argus = []
            function_info = f"{prefix}/{node.name}({', '.join(argus)}) {''.join(flags)}"
            if isinstance(node, ast.ClassDef):
                info.append(f"{prefix}/{node.name}{''.join(flags)}")
                for sub_node in node.body:
                    if isinstance(sub_node, ast.FunctionDef):
                        sub_argus = [arg.arg for arg in sub_node.args.args]
                        function_info = f"{prefix}/{node.name}/{sub_node.name}({', '.join(sub_argus)}) {''.join(flags)}"
                        add_print_statement(sub_node, function_info, args)
                        info.append(function_info)
            else:
                add_print_statement(node, function_info, args)
                info.append(function_info)

    modified_source = astor.to_source(root)
    with open(file_path, 'w') as file:
        file.write(modified_source)

    return info

def add_print_statement(function_node, function_info, args):
    print_info = ast.Expr(
        value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[ast.Str(s=re.sub(r' \w+$', '', function_info))],
            keywords=[]
        )
    )
    print_info.lineno = function_node.body[0].lineno
    print_info.col_offset = function_node.body[0].col_offset
    function_node.body.insert(0, print_info)

    if args.args:
        # extract argument names
        arg_names = [arg.arg for arg in function_node.args.args]
        # generate print statements
        print_statements = []
        for arg_name in arg_names:
            # add print statement for argument name and value
            print_statement = ast.Expr(
                value=ast.Call(
                    func=ast.Name(id='print', ctx=ast.Load()),
                    args=[
                        ast.Str(s="\t" + arg_name + ":"),
                        ast.Name(id=arg_name, ctx=ast.Load())
                    ],
                    keywords=[]
                )
            )
            print_statement.lineno = function_node.body[0].lineno
            print_statement.col_offset = function_node.body[0].col_offset
            print_statements.append(print_statement)
        # insert print statements at the beginning of the function body
        for print_statement in reversed(print_statements):
            function_node.body.insert(0, print_statement)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--args', action='store_true', help='include function arguments in print statements')
    args = parser.parse_args()

    root_dir = os.getcwd()
    if not os.path.exists(os.path.join(root_dir, '.git')):
        print("This script should be run from the root directory of a Git repository.")
        sys.exit(1)

    output_file_path = os.path.join(root_dir, 'output.txt')
    info = []
    for foldername, subfolders, filenames in os.walk(root_dir):
        if foldername != root_dir:  # skip files in the root directory
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(foldername, filename)
                    info.extend(process_file(file_path, root_dir, args))

    with open(output_file_path, 'w') as file:
        file.write('\n'.join(info))

    print(f"Found {len(info)} methods and functions. Press Enter to continue.")
    input()

if __name__ == "__main__":
    main()
