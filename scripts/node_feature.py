import re
from utils import parse_method_parameters

def remove_annotation(method):
    annotations = re.findall(r'\.annotation.+?\.end annotation', method, re.DOTALL)
    for annotation in annotations:
        method = method.replace(annotation, '')
    return method

def exclude_method(method_desp):
    # print('2method_desp:', method_desp)
    pamas = method_desp.split('(')[1].split(')')[0]
    ret_v = method_desp.split(')')[1]
    # if method_desp.strip().startswith('.method public static constructor <clinit>()V'):
    if "clinit" in method_desp.strip():
        return True
    return False

def recursive_call(method_id, inter_calls_dict, inner_calls_dict, all_calls_dict, checked_method, call_chain, depth,class_name,all_classes):
    if method_id in checked_method:
        return 1
    else:
        checked_method.add(method_id)
    # 终节点：不再调用任何方法的方法
    if len(all_calls_dict[method_id]) == 0: 
        print('{}called(inner,end):{}'.format(' '*(depth),method_id))
        call_chain.append(method_id)
        return 1
    else:
        print('{}called(inner):{}'.format(' '*(depth),method_id))
        pass
    # 递归调用类内方法
    for call in inner_calls_dict[method_id]:
        # 已经调用过
        if call in call_chain:
            continue
        recursive_call(call, inter_calls_dict,inner_calls_dict, all_calls_dict, checked_method, call_chain, depth+1,class_name,all_classes)
    # 直接把（联合依赖）类外调用加入调用链
    for call in inter_calls_dict[method_id]:
        # 已经调用过
        if call in call_chain:
            continue
        print('{}called(inter,end):{}'.format(' '*(depth+1),call))
        call_chain.append(call)
    return 0

def update_uncalled_chains(checked_method, call_entrances):
    pop_entrance = []
    # 弹出0调用的函数
    # for entrance in call_entrances:
    #     key = entrance[0]
    #     values = entrance[1] # set
    #     t_values = values.copy()
    #     # print('key:', key)
    #     for v in t_values:
    #         # print('value:', v)
    #         if v in checked_method:
    #             values.discard(v)
    #             # print('pop:', v)
    # for entrance in call_entrances:
    #     # 弹出无调用的函数
    #     if len(entrance[1]) == 0:
    #         # print('pop entrance: ', entrance[0])
    #         pop_entrance.append(entrance)
    # 弹出最大调用的函数
    if len(call_entrances)>=1:
        # print('pop entrance: ', call_entrances[0])
        pop_entrance.append(call_entrances[0])

    for x in pop_entrance:
        call_entrances.remove(x)
    # call_entrances = new_entrance
    call_entrances.sort(key=lambda x: len(x[1]), reverse=True)
    # print('checked_method:', checked_method)
    # print('call_entrances:', call_entrances)
    for entrance in call_entrances:
        # print('entrance:{},len:{}'.format(entrance[0],len(entrance[1])))
        pass
    # print('------------------------')

def count_leading_brackets(s):
    count = 0
    for char in s:
        if char == '[':
            count += 1
        else:
            break
    return count

def extend_type(_type):
    return _type
    if _type == 'Z': return 'Boolean'
    if _type == 'B': return 'Byte'
    if _type == 'C': return 'Char'
    if _type == 'S': return 'Short'
    if _type == 'I': return 'Int'
    if _type == 'F': return 'Float'
    if _type == 'J': return 'Long'
    if _type == 'D': return 'Double'
    if _type == 'V': return 'Void'
    if _type == 'Class': return 'Class'
    print('Unknown type:', _type)
    return 'Void'

def process_call_chains(call_chain, class_name):
    simplified_chain = []
    for call in call_chain:
        obj = call.split('->')[0]
        if obj == class_name:
            # obj = 'InnerMethod'
            obj = 'N'
        else:
            # obj = 'InterMethod'
            obj = 'I'
        method_name, args = call.split('(')
        args, ret_v = args.split(')')[0], args.split(')')[1]
        args = parse_method_parameters(args)
        # if len(args) == 0:
        #     args = ['Void']
        # else:
        #     # args = ['Void'] if len(args) == 0 else args
        #     args = [extend_type(arg) for arg in args]
        args = ['V'] if len(args) == 0 else args
        new_args = []
        new_ret_v = ''
        # 化简参数。将参数中的类名替换为Class，将数组替换为Array。
        for arg in args:
            tstr = ''
            s_idx = count_leading_brackets(arg)
            tstr = arg[s_idx:]
            if tstr.startswith('L') and tstr.endswith(';'):
                tstr = 'X'
            else: 
                tstr = extend_type(tstr)
            tstr += '[]' * s_idx
            new_args.append(tstr)
        new_args.sort()
        # 化简返回值
        tstr = ''
        s_idx = count_leading_brackets(ret_v)
        tstr = ret_v[s_idx:]
        if tstr.startswith('L') and tstr.endswith(';'):
            tstr = 'X'
        else: 
            tstr = extend_type(tstr)
        tstr += '[]' * s_idx
        new_ret_v = tstr
        # print('call:', call)
        item = obj + '_' + ''.join(new_args) + '_' + new_ret_v
        # print('item:', item)
        simplified_chain.append(item)
        # print(item)
        # print('obj:', obj)
        # print('method:', method)
    simplified_chain.sort()
    return simplified_chain

def is_class(class_name,exclude_class,all_class):
    return class_name in all_class and not class_name in exclude_class

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
    # print('find ref: {}'.format(method_desp))
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

def get_call_chains(methods_blocks,class_name,all_classes,fields, valid_mth_set):
    chain_num = 0
    call_num = 0
    # 调用类方法字典
    valid_inter_calls_dict = {}
    all_inter_calls_dict = {}
    inner_calls_dict = {}
    inher_calls_dict = {}
    stardard_calls_dict = {}
    all_calls_dict = {}
    be_called_class_dict = {}
    # 被调用类方法字典
    called_class_dict = {}
    method_ref_dict = {}
    # 
    print('------------------------')
    print('class_name:', class_name)
    # 创建反射字典
    for method_blk in methods_blocks:
        judge_ref(method_blk, class_name, method_ref_dict)
    for method_blk in methods_blocks:
        # 去除注释
        method_blk = remove_annotation(method_blk)
        method_lines=method_blk.split('\n')
        # 获得描述符和id
        this_method_desp = method_lines[0]
        this_method_id = class_name + '->'+ this_method_desp.split(' ')[-1]
        # print('this_method_id:', this_method_id)
        valid_inter_calls_dict[this_method_id] = set()
        all_inter_calls_dict[this_method_id] = set()
        inner_calls_dict[this_method_id] = set()
        inher_calls_dict[this_method_id] = set()
        stardard_calls_dict[this_method_id] = set()
        all_calls_dict[this_method_id] = set()
        if this_method_id not in be_called_class_dict:
            be_called_class_dict[this_method_id] = set()
        # 获取方法调用
        calls = re.findall('invoke-.*? {.*?}, (\[*L.*?)\n', method_blk)
        # 构建类的调用字典，用来判断多次调用
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
                obj,method,args,ret_v = ref_ret
                if obj == '': obj = call.split('->')[0]
                call = obj + '->' + method + '(' + ''.join(args) + ')' + ret_v

            if obj not in called_class_dict:
                called_class_dict[obj] = set()
            if call not in called_class_dict[obj]:
                called_class_dict[obj].add(call)
            # 构建类内方法的被调用字典
            if obj == class_name:
                if call not in be_called_class_dict:
                    be_called_class_dict[call] = set()
                be_called_class_dict[call].add(this_method_id)
    # 检查调用关系
    for method_blk in methods_blocks:
        # 去除注释
        method_blk = remove_annotation(method_blk)
        # 获得描述符和id
        this_method_desp = method_blk.split('\n')[0]
        # 如果是确定模式（clinit）的垃圾方法,则跳过
        if exclude_method(this_method_desp): 
            continue
        this_method_id = class_name + '->'+ this_method_desp.split(' ')[-1]
        # print('method_id:', this_method_id)
        # 获得方法调用
        calls = re.findall('invoke-.*? {.*?}, (\[*L.*?)\n', method_blk)
        print(' method_id:', this_method_id)
        # 构建类的调用字典
        for call in calls:
            if call == 'Ljava/lang/Integer;->parseInt(Ljava/lang/String;)I':
                continue
            all_calls_dict[this_method_id].add(call)
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
                if obj == '': obj = call.split('->')[0]
                call = obj + '->' + method + '(' + ''.join(args) + ')' + ret_v
                print('    undo ref: {} # {}'.format(tcall,call))
            # 类外调用，判断是否是联合调用，是，加入清单
            if is_class(obj, [class_name], all_classes): 
                # 返回值是否构成多类调用
                if is_class(ret_v, [obj],all_classes):
                    valid_inter_calls_dict[this_method_id].add(call)
                    print('  mulcall: {}'.format(call))
                # 参数是否构成多类调用
                for x in args:
                    if is_class(x, [obj],all_classes):
                        valid_inter_calls_dict[this_method_id].add(call)
                        print('  mulcall: {}'.format(call))
                # 是否构成字段调用
                if obj in fields.values():
                    valid_inter_calls_dict[this_method_id].add(call)
                    print('  fieldcall: {}'.format(call))
                # 是否构成多次调用
                if obj in called_class_dict:
                    if len(called_class_dict[obj]) > 1:
                        valid_inter_calls_dict[this_method_id].add(call)
                        print('  mulclass: {}'.format(call))
                # baseline：考虑所有调用
                # print('direct_call_dep:',call)
                all_inter_calls_dict[this_method_id].add(call)
            # 类内调用，不判断联合调用
            elif is_class(obj, [], class_name):
                # 必须在类内存在（排除继承的方法）
                if call in inner_calls_dict.keys():
                    inner_calls_dict[this_method_id].add(call)
                    print('  innercall: {}'.format(call))
                # 继承方法
                else:
                    inher_calls_dict[this_method_id].add(call)
            # 标准类
            else:
                stardard_calls_dict[this_method_id].add(call)
    # 进行调用链的构建
    # 把所有的方法加入调用入口中,并进行调用数的排序
    call_entrances = []
    for key in all_calls_dict.keys():
        # entrance只考虑根节点。
        if len(be_called_class_dict[key]) != 0:
            continue
        # if key not in valid_mth_set:
        #     print('skip:', key)
        #     continue
        # valid_inter_calls指的是满足联合调用的方法。inner_calls指的是类内调用的方法
        values = valid_inter_calls_dict[key] | inner_calls_dict[key]
        # value_inter = valid_inter_calls_dict[key]
        # value_inner = inner_calls_dict[key]
        call_entrances.append([key,values])
        # print('key:', key)
        # print('values:', values)
    call_entrances.sort(key=lambda x: len(x[1]), reverse=True)
    # for chain in call_entrances:
    #     print('chain:', chain)
    # for key, value in valid_calls_dict.items():
    #     # print('key:', key)
    #     # print('value:', value)
    #     call_entrances.append([key, set(value)])

    # 调用链。单个节点的链跳过
    call_chains = []
    # update_uncalled_chains(checked_method, call_entrances)
    
    # 调用链没有全部遍历完
    for i in range(len(call_entrances)):
        # for chain in call_entrances:
        #     print('chain:', chain)
        if len(call_entrances) == 0:
            break
        entrance = call_entrances[0]
        call_chain = []
        call = entrance[0]
        calleds = entrance[1]
        call_chain.append(entrance[0])
        # print('call_chain:', call_chain)
        print('')
        print('call(entrance):', call)
        checked_method = set()
        checked_method.add(entrance[0])
        # 遍历调用.查看是否是类内方法,如果是,则进行递归调用
        for called in calleds:
            # print('called:', called)
            obj = called.split('->')[0]
            # 保证调用的方法没有被调用过
            if called in call_chain:
                continue
            # 如果是类内方法,则进行递归调用
            if obj == class_name:
                recursive_call(called, valid_inter_calls_dict,inner_calls_dict,all_calls_dict,checked_method, call_chain, 1,class_name,all_classes)
            else:
                call_chain.append(called)
                print(' called(inter,end):', called)
                checked_method.add(called)
        # 结束一次调用链
        print('call_chain:', call_chain)
        print('len:', len(call_chain))
        if len(call_chain) == 1:
            print('len==1, skip this enrty')
            pass
        else:
            call_num += len(call_chain)
            chain_num += 1
            simplified_call_chain = process_call_chains(call_chain, class_name)
            print('simplified_call_chain:', simplified_call_chain)
            call_chains.append(simplified_call_chain)
        update_uncalled_chains(checked_method, call_entrances)
    def contate_chain(chain):
        res = ''
        for x in chain:
            res += x + '->'
        return res
    call_chains.sort(key=lambda x: (len(x),contate_chain(x)), reverse=True)
    print('call_num:', call_num)
    print('chain_num:', chain_num)
    f = open('res_chain.csv', 'a')
    f.write('class_name:{},call_num:{},chain_num:{}\n'.format(class_name, call_num, chain_num))
    f.close()
    return call_chains

