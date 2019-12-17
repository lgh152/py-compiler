import os
import re
import sys

from src.lexer import word_list
from src.LR import analysis
# from parser import Node,build_ast
from src.other.function import if_num

sys.path.append(os.pardir)

operator = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b
}

"""
四元式对象
成员：　op，arg1,arg2,result 分别对于操作数，两个变量，结果
特殊的自定义四元式语法：
    1.  (code_block, 0, 0, block1)   代码块开始标记
    2.  (j, 0, 0, , +2)              跳转语句，往后跳两行
    3.  (j<, ａ, b, block1)          条件跳转 if(a<b) then　jmp block1
    4.  (print, 0, 0, a)             打印变量ａ
"""


class Mnode:
    def __init__(self, op="undefined", a1=None, a2=None, re=None):
        self.op = op
        self.arg1 = a1
        self.arg2 = a2
        self.re = re
    
    """字符化输出"""
    
    def __str__(self):
        return "({0},{1},{2},{3})".format(self.op, self.arg1, self.arg2, self.re)
    
    def __repr__(self):
        return self.__str__()


"""
两个全局 mid_result 存放四元式对象
tmp记录零时变量id
"""
mid_result = []
while_flag = []
arr = {}
tmp = 0
type_flag = ""

"""
递归遍历语法树
遇到相应非终结符做相应处理，遇到终结符返回终结符，其他字符递归处理其子节点

"""


def view_astree(root, ft=None):
    global type_flag
    if root.type == "type":
        type_flag = root.text
    if root == None or root.text == "(" or root.text == ")":
        return
    elif len(root.child) == 0 and root.text != None:
        return root.text
    if root.type == "L":
        math_op(root)
    elif root.type == "Pan":
        judge(root)
    elif root.type == "OUT":
        out(root)
    else:
        re = ""
        for c in root.child:
            cre = view_astree(c)
            if cre != None and cre not in "[]}{)(\"'":
                re = cre
        return re


def math_op(root, ft=None):
    if root == None:
        return
    elif len(root.child) == 0 and root.text != None:
        return root.text
    global mid_result
    global tmp
    global arr
    global type_flag
    """
    变量声明语句，两种情况
    1. 直接赋值
    2. 不赋值
    """
    if root.type == "L":
        
        c1 = root.child[1]
        if len(c1.child) == 1:
            mid_result.append(Mnode("=", 0, 0, math_op(root.child[0].child[0])))
        elif c1.child[0].type == "=":
            mid_result.append(Mnode("=", math_op(c1), 0, math_op(root.child[0].child[0])))
        else:
            if len(c1.child[1].child) > 1:
                cc1 = c1.child[1]
                mid_result.append(
                    Mnode("=", math_op(cc1), 0, math_op(root.child[0].child[0]) + "[]" + math_op(c1.child[0])))
            if math_op(root.child[0].child[0]) not in arr:
                arr[math_op(root.child[0].child[0])] = [math_op(c1.child[0]), type_flag]
                type_flag = ""
    elif root.type == "ET" or root.type == "TT":
        if len(root.child) > 1:
            op = Mnode(math_op(root.child[0]))
            arg1 = math_op(root.child[1])
            if if_num(arg1) and if_num(ft):
                return str(operator[op](int(arg1), int(ft)))
            
            """
            临时变量Tn
            ft 为父节点传入的操作符左边部分临时id
            """
            t = "T" + str(tmp)
            tmp += 1
            mid_result.append(Mnode(op, arg1, ft, t))
            ct = math_op(root.child[2], t)
            if ct != None:
                return ct
            return t
    
    elif root.type == "E" or root.type == "T":
        """
        赋值语句处理
        如果存在右递归，进行四则运算的解析
        不存在右递归的话直接赋值
        """
        if len(root.child[1].child) > 1:
            op = math_op(root.child[1].child[0])
            arg1 = math_op(root.child[0])
            arg2 = math_op(root.child[1].child[1])
            """静态的计算提前算好"""
            if if_num(arg1) and if_num(arg2):
                return str(operator[op](int(arg1), int(arg2)))
            
            t = "T" + str(tmp)
            tmp += 1
            mid_result.append(Mnode(op, arg1, arg2, t))
            ct = math_op(root.child[1].child[2], t)
            if ct != None:
                return ct
            return t
        else:
            return math_op(root.child[0])
    elif root.type == "F" and len(root.child) == 2:
        c = root.child
        if c[1].child != [] and c[1].child[0].type == "Size":
            return c[0].child[0].text + "[]" + math_op(c[1])
        else:
            return c[0].child[0].text
    
    else:
        re = ""
        for c in root.child:
            cre = math_op(c)
            if cre != None and cre not in "[]}{)(\"'":
                re = cre
        return re


"""
控制语句的程序块处理
可处理语句：
    １. if语句
    ２. while语句
    ３. if和while的相互嵌套语句
"""


def judge(root):
    if root == None:
        return
    elif len(root.child) == 0 and root.text != None:
        return root.text
    if root.type == "Ptype":
        if root.child[0].text == "if":
            while_flag.append([False])
        else:
            """
            对whilie语句进行代码块标记，方便跳转
            """
            cur = len(mid_result)
            while_flag.append([True, cur])
            mid_result.append(Mnode("code_block", 0, 0, "W" + str(cur)))
    if root.type == "Pbc":
        """
        判断语句括号中的的两种情况
        1. (E)
        2. (E1 cmp E2)
        """
        Pm = root.child[1].child
        if len(Pm) == 1:
            mid_result.append(Mnode("j=", 1, math_op(root.child[0]), "code" + str(len(mid_result) + 1)))
        else:
            mid_result.append(
                Mnode("j" + judge(Pm[0]), math_op(root.child[0]), math_op(Pm[1]), "code" + str(len(mid_result) + 1)))
        return
    if root.type == "Pro":
        """
        控制语句的代码块前后做标记
        判断标记
        跳转->结束标记
        {
            code
        }
        while跳转->判断标记
        结束标记
        """
        w = while_flag.pop()
        code_block = len(mid_result)
        code = "block" + str(code_block)
        mid_result.append(Mnode("j", 0, 0, code))
        mid_result.append(Mnode("code_block", 0, 0, "code" + str(code_block)))
        view_astree(root)
        if w[0] == True:
            mid_result.append(Mnode("j", 0, 0, "W" + str(w[1])))
        mid_result.append(Mnode("code_block", 0, 0, code))
        code_block += 1
        return
    else:
        re = ""
        for c in root.child:
            cre = judge(c)
            if cre != None and cre not in "[]}{)(\"'":
                re = cre
        return re


"""
输出处理
可处理语句：printf(a,b) 该语法：在括号内只能传入变量参数
"""


def out(root):
    if root == None:
        return
    elif root.type == "V":
        if len(root.child) <= 1:
            mid_result.append(Mnode("print", '-1', '-1', '-1'))
            return
        else:
            name = [math_op(root.child[1])]
            V = root.child[2]
            while len(V.child) > 1:
                name.append(math_op(V.child[1]))
                V = V.child[2]
            name.extend(['-1', '-1', '-1'])
            mid_result.append(Mnode("print", name[0], name[1], name[2]))
    else:
        for c in root.child:
            out(c)


def creat_mcode(filename):
    global tmp
    global mid_result
    global arr
    arr = {}
    tmp = 0
    mid_result = []
    w_list = word_list(filename)
    if w_list.flag:
        word_table = w_list.word_list
        string_list = w_list.string_list
        root = analysis(word_table)[1]
        view_astree(root)
        
        return {"name_list": w_list.name_list, "mid_code": mid_result, "tmp": tmp, "strings": string_list, "arrs": arr}
    else:
        return False

def get_generate():
    filename = 'code/upload.c'
    creat_mcode(filename)
    result = ''
    for r in mid_result:
        result += str(r)
    return result


if __name__ == "__main__":
    filename = '../code/upload.c'
    creat_mcode(filename)
    for r in mid_result:
        print(r)
