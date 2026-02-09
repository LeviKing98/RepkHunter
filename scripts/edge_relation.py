import os
import re
from utils import parse_method_parameters
def get_class_info(filepath):
    """
    获取类名，父类名，接口名，字段名
    """
    class_name=''
    super_name=''
    implements=[]
    fields = {}

    with open(filepath, 'r') as f:
        lines = [line.replace('\n','') for line in f if line.strip() != '' and not line.startswith('#') and not line.strip().startswith('.line') and not line.startswith('.source')] 
        class_name = lines[0].split(' ')[-1]
        super_name = lines[1].split(' ')[-1]
        # 用于表示当前正在处理的内容，需要记录很多状态
        for line in lines:
            # 每行开头的空格都去掉，方面后续处理
            line=line.strip()
            # 检查接口 .implements LMovable;
            if(line.startswith('.implements')):
                implements.append(line.split(' ')[-1])
                continue
            # 获取字段
            if(line.startswith('.field')):
                line=line.split(' = ')[0]
                # print(line)
                field = line.split(' ')[-1]
                # print(field)
                tname, ttype= field.split(':')
                fields[tname] = ttype
                continue
    return class_name, super_name, implements, fields

inheritance_cnt = 0
implementations_cnt = 0
dependencies_cnt = 0
associations_cnt = 0
aggregations_cnt = 0
compositions_cnt = 0

def list_files(directory):
    """
    递归获得一个文件夹下所有文件的路径
    """
    filepaths = []
    for root, dirs, files in os.walk(directory):
        for name in files:
            # print(os.path.join(root, name))
            filepaths.append(os.path.join(root, name))
    return filepaths

def is_class(class_name,exclude_class,all_class):
    return class_name in all_class and not class_name in exclude_class


def is_field_call_dep(method_desp, fields):
    obj = method_desp.split('->')[0]
    if obj in fields.values():
        return True
    
def is_mulclass_dep(method_desp, class_name,super_name, all_class):
    obj = method_desp.split('->')[0]
    method = method_desp.split('->')[1].split('(')[0]
    args = method_desp.split('->')[1].split('(')[1].split(')')[0]
    ret_v = method_desp.split('->')[1].split('(')[1].split(')')[1]
    if is_class(obj, [class_name,super_name], all_class): 
        # print(f'stac add obj{obj} to dependencies')
        # 是否构成多类调用
        if is_class(ret_v, [obj],all_class):
            return True
        targs = parse_method_parameters(args)
        for x in targs:
            if is_class(x, [obj],all_class):
                return True

def is_mulcall_dep(method_desp, class_name,super_name, all_class,class_calls_dict):
    # 分离主类、方法、参数、返回值
    obj = method_desp.split('->')[0]
    method = method_desp.split('->')[1].split('(')[0]
    args = method_desp.split('->')[1].split('(')[1].split(')')[0]
    ret_v = method_desp.split('->')[1].split('(')[1].split(')')[1]
    # 调用类外方法
    if is_class(obj, [class_name,super_name], all_class): 
        # 是否构成多次调用
        if obj in class_calls_dict:
            if len(class_calls_dict[obj]) > 1:
                return True
            

def judge_ref(method_str, class_name, method_ref_dict):
    if not len(re.findall(r'Ljava/lang/Class;->getMethod', method_str)) == 1:
        return False
    # 截取'    invoke-virtual {v0, v1, v2}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;'之前的字符串
    method_lines=method_str.split('invoke-virtual {v0, v1, v2}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;')[0]
    method_lines=method_lines.split('\n')
    # 获得参数
    desp=method_lines[0]
    # print(desp)
    method_desp = desp.split(' ')[-1]
    method_name, args = method_desp.split('(')
    args, ret_v = args.split(')')[0], args.split(')')[1]
    args = parse_method_parameters(args)
    # 匹配avpass的反射模式
    if len(method_name) < 16:
        print('len not ref method_name:', method_name)
        return False
    # 第一个参数是类名；后面的参数是反射方法参数；返回值是反射方法返回值
    print('find ref: {}'.format(method_desp))
    # 寻找倒数第一个v0的类型
    _tcls = re.findall(r'const-class v., L(.*?);', method_str)
    if len(_tcls) == 0:
        return False
    _ref_cls = 'L' + _tcls[-1] + ';'

    _ref_mthd = re.findall(r'\"(.*?)\"', method_str)[-1]
    _ref_args = args
    if len(_ref_args) > 0:
        if _ref_args[0] == _ref_cls:
            if len(_ref_args) > 1:
                _ref_args = _ref_args[1:]
            else:
                _ref_args = []
    _ref_ret = ret_v

    method_ref_dict[(class_name,method_name,tuple(args),ret_v)] = (_ref_cls, _ref_mthd, tuple(_ref_args), _ref_ret)
    print('ref_mthd: {} -> {}'.format((class_name,method_name,tuple(args),ret_v),(_ref_cls, _ref_mthd, tuple(_ref_args), _ref_ret)))
    return (_ref_cls, _ref_mthd, _ref_args, _ref_ret)

def solve_ref(obj,method,args,ret_v,method_ref_dict):
    args = tuple(args)
    flag = False
    if (obj,method,args,ret_v) in method_ref_dict.keys():
        # print('undo ref: {} -> {}'.format((obj,method,args,ret_v),method_ref_dict[(obj,method,args,ret_v)]))
        flag = True
        obj,method,args,ret_v = method_ref_dict[(obj,method,args,ret_v)]
    args = list(args)
    call = obj + '->' + method + '(' + ''.join(args) + ')' + ret_v
    return flag, (obj,method,args,ret_v)

def gen_edge_relation(smali_filepath,all_class=[]):
    inheritance=set()
    implementations=set()
    # dependencies=set()
    # associations=set()
    # aggregations=set()
    # compositions=set()
    
    fieldcall_dep = set()
    mulclass_dep = set()
    mulcall_dep = set()
    union_call_dep = set()
    # desp_dep = set()
    direct_call_dep = set()
    
    # 调用次数
    class_called_cnt_dict = {}

    # method_calls_dict = {}

    # 获取类信息
    class_name, super_name, implements, fields = get_class_info(smali_filepath)

    if is_class(super_name, [class_name],all_class):
        inheritance.add(super_name)
    for implement in implements:
        if is_class(implement, [class_name,super_name],all_class):
            implementations.add(implement)

    with open(smali_filepath, 'r') as f:
        data=f.read()

    # 通过method找到类关系
    methods = re.findall(r'^\.method .+?\.end method$', data, re.MULTILINE | re.DOTALL)
    # method_num = len(methods)
    # print(smali_filepath)
    # print('raw methods num:', method_num)
    class_calls_dict = {}
    method_ref_dict = {}
    # method_calls_dict = {}

    # 创建反射字典
    for method_str in methods:
        judge_ref(method_str, class_name, method_ref_dict)

    # 构建类的调用字典，用来判断多次调用
    for method_str in methods:
        # 获取方法调用
        calls = re.findall('invoke-.*? {.*?}, (L.*?)\n', method_str)
        for call in calls:
            # 分离主类、方法、参数、返回值
            obj = call.split('->')[0]
            method = call.split('->')[1].split('(')[0]
            args = call.split('->')[1].split('(')[1].split(')')[0]
            args = parse_method_parameters(args)
            ret_v = call.split('->')[1].split('(')[1].split(')')[1]
            # 判断是否反射
            flag, ref_ret = solve_ref(obj,method,args,ret_v,method_ref_dict)
            if flag:
                tcall = call
                obj,method,args,ret_v = ref_ret
                # if obj == '': obj = call.split('->')[0]
                call = obj + '->' + method + '(' + ''.join(args) + ')' + ret_v
                # print('    undo ref: {} # {}'.format(tcall,call))

            if obj != class_name:
                class_called_cnt_dict[obj] = class_called_cnt_dict.get(obj, 0) + 1
            if obj not in class_calls_dict:
                class_calls_dict[obj] = set()
            if call not in class_calls_dict[obj]:
                # print('call_dict obj={} call={}'.format(obj,call))
                class_calls_dict[obj].add(call)

    # 构建类依赖关系
    for method_str in methods:
        method_lines=method_str.split('\n')
        # 获得参数
        desp=method_lines[0]
        # print(desp)
        method_desp = desp.split(' ')[-1]
        method_name, args = method_desp.split('(')

        this_method_id = class_name + '->'+ method_desp
        # method_calls_dict[this_method_id] = set()

        args, ret_v = args.split(')')[0], args.split(')')[1]
        args = parse_method_parameters(args)
        # 获取方法调用
        calls = re.findall('invoke-.*? {.*?}, (L.*?)\n', method_str)
        # 分析调用
        for call in calls:
            # 分离主类、方法、参数、返回值
            obj = call.split('->')[0]
            method = call.split('->')[1].split('(')[0]
            args = call.split('->')[1].split('(')[1].split(')')[0]
            args = parse_method_parameters(args)
            ret_v = call.split('->')[1].split('(')[1].split(')')[1]
            # 判断是否反射
            flag, ref_ret = solve_ref(obj,method,args,ret_v,method_ref_dict)
            if flag:
                tcall = call
                obj,method,args,ret_v = ref_ret
                # if obj == '': obj = call.split('->')[0]
                call = obj + '->' + method + '(' + ''.join(args) + ')' + ret_v
                # print('    undo ref: {} # {}'.format(tcall,call))
            # 调用类外方法，考虑联合调用
            if is_class(obj, [class_name], all_class): 
                # print(f'stac add obj{obj} to dependencies')
                # 是否构成多类调用
                if is_class(ret_v, [obj],all_class):
                    mulclass_dep.add(obj)
                    # method_calls_dict[this_method_id].add(call)
                # targs = parse_method_parameters(args)
                # for x in targs:
                for x in args:
                    if is_class(x, [obj],all_class):
                        mulclass_dep.add(obj)
                        # method_calls_dict[this_method_id].add(call)
                # 是否构成字段调用
                if obj in fields.values():
                    fieldcall_dep.add(obj)
                    # method_calls_dict[this_method_id].add(call)
                # 是否构成多次调用
                if obj in class_calls_dict:
                    # print('2call_dict obj={} call={}'.format(obj,call))
                    if len(class_calls_dict[obj]) > 1:
                        mulcall_dep.add(obj)
                        # method_calls_dict[this_method_id].add(call)
                # baseline：考虑所有调用
                # print('direct_call_dep:',call)
                direct_call_dep.add(obj)
            # 调用类内方法
            # method_calls_dict[this_method_id].add(call)

    union_call_dep = mulclass_dep | fieldcall_dep | mulcall_dep

    print('class_name:', class_name)
    print('inheritance:', inheritance)
    print('implementations:', implementations)
    print('fieldcall_dep:', fieldcall_dep)
    print('mulclass_dep:', mulclass_dep)
    print('mulcall_dep:', mulcall_dep)

    print('valid_call_dep:', union_call_dep)
    print('direct_call_dep:', direct_call_dep)
    print('------------------')
    # dep_final_set = direct_call_dep
    # dep_final_set = mulcall_dep
    # relation_list=[list(inheritance), list(implementations), list(dependencies), list(associations), list(aggregations), list(compositions)]
    relation_list= [list(inheritance), list(implementations), list(fieldcall_dep), list(mulclass_dep), list(mulcall_dep), list(union_call_dep)]
    # relation_list=[list(inheritance), list(fieldcall_dep), list(mulclass_dep), list(mulcall_dep), list(union_call_dep), list(direct_call_dep)]
    return class_name, relation_list, class_called_cnt_dict
    
if __name__=='__main__':
    smali_path='./out/com/joymeng/nineoldandroids/util/Property.smali'
    class_name, relation_list_str=gen_edge_relation(smali_path)
    print(class_name)
    print(relation_list_str)
