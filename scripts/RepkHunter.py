import os
import subprocess
import shutil
import numpy as np

from preproccess import preproccess_apk
from utils import list_files
from node_feature import *
from edge_relation import gen_edge_relation,get_class_info
import sys
 
# 提高最大递归深度
# sys.setrecursionlimit(10000)
node_properti_dict = dict()
traverse_map = dict()
relation_map = dict()
hava_parent = dict()
have_rela = dict()
node_list = []
max_depth = 0
traverse_cnt = 0
root_cnt = 0
node_dict = dict()
node_set = set()

final_opseq = bytearray()  
final_opseq_str = ''


# def get_all_classes(smali_dir = './out'):
#     smali_filepaths=list_files(smali_dir)
#     all_class = []
#     # 获得所有smali文件的类名 
#     for path in smali_filepaths:
#         ft = open(path, 'r')
#         # 读取首行的class名
#         first_line = ft.readline()
#         ft.close() 
#         t = first_line.strip().split(' ')[-1]
#         all_class.append(t)
#     return all_class
def judge_ref(method_str, class_name, method_ref_dict):

    method_lines=method_str.split('\n')
    # 获得参数
    desp=method_lines[0]
    # print(desp)
    method_desp = desp.split(' ')[-1]
    method_name, args = method_desp.split('(')

    args, ret_v = args.split(')')[0], args.split(')')[1]
    args = parse_method_parameters(args)
    # 匹配avpass的反射模式
    if not len(re.findall(r'Ljava/lang/Class;->getMethod', method_str)) == 1:
        return False
    if len(method_name) < 16:
        print('len not ref method_name:', method_name)
        return False

    
    # 第一个参数是类名；后面的参数是反射方法参数；返回值是反射方法返回值
    print('find ref: {}'.format(method_desp))
    if len(args) > 0:
        _ref_cls = args[0]
    else:
        # _ref_cls = ''
        _tcls = re.findall(r'const-class .*?, L(.*?);', method_str)
        _ref_cls = 'L' + _tcls[0] + ';'
        print('modify ref_cls: {}'.format(_ref_cls))
    if len(args) > 1:
        _ref_args = args[1:]
    else:
        _ref_args = []
    _ref_ret = ret_v
    # 寻找字符串
    strs = re.findall(r'\"(.*?)\"', method_str)
    _ref_mthd = strs[0]
    method_ref_dict[(class_name,method_name,tuple(args),ret_v)] = (_ref_cls, _ref_mthd, tuple(_ref_args), _ref_ret)
    # print('ref_mthd: {} -> {}'.format((class_name,method_name,tuple(args),ret_v),(_ref_cls, _ref_mthd, tuple(_ref_args), _ref_ret)))
    return (_ref_cls, _ref_mthd, _ref_args, _ref_ret)
    
def get_all_classes(smali_dir = './out'):
    smali_filepaths=list_files(smali_dir)
    all_class = []
    # valid_mth_set代表被调用过的函数，即有效函数。防御死代码移除，因为死代码不会被调用。
    valid_mth_set = set()
    # 获得所有smali文件的类名 
    for path in smali_filepaths:
        f = open(path, 'r')
        first_line = f.readline()
        class_name = first_line.strip().split(' ')[-1]
        all_class.append(class_name)
        data = f.read()
        f.close()
        # 找到所有方法
        methods = re.findall(r'^\.method .+?\.end method$', data, re.MULTILINE | re.DOTALL)
        # 加入方法被调用flag
        for method in methods:
            calls = re.findall('invoke-.*? {.*?}, (\[*L.*?)\n', method)
            valid_mth_set.update(calls)
            # print('calls:',calls)
            # method_lines = method.split('\n')
            # # 获得参数
            # desp=method_lines[0]
            # # #print(desp)
            # #print('desp:',desp)
            # method_desp = desp.split(' ')[-1]

            # this_method_id = class_name + '->'+ method_desp
            # # print('this_method_id:',this_method_id)
            # valid_mth_set.add(this_method_id)
            # print('valid_method_id: {}, called by ',this_method_id )
    for item in valid_mth_set:
        # print('valid_method_id:',item)
        pass
    return all_class, valid_mth_set
        

def gen_class_relations(all_class, smali_dir = './out'):
    smali_filepaths=list_files(smali_dir)
    # 建立类关系
    # cls_rela_list = [] 
    cls_rela_dict = dict()
    cls_called_cnt_dict = dict()
    for path in smali_filepaths:
        t_cls_name, t_cls_rela, t_cls_called_cnt_dict = gen_edge_relation(path, all_class)
        cls_rela_dict[t_cls_name] = t_cls_rela
        cls_called_cnt_dict[t_cls_name] = t_cls_called_cnt_dict
        # cls_rela_list.append([t_cls_name,t_cls_rela])
        # node_rela_dict[class_name] = relation_list
    return cls_rela_dict, cls_called_cnt_dict

def gen_call_chains(all_classes, valid_mth_set):
    chains_dict = dict()
    for _cls in all_classes:
        smali_filepath = './out/' + _cls[1:-1] + '.smali'
        class_name, super_name, implements, fields = get_class_info(smali_filepath)
        if os.path.exists(smali_filepath) == False:
            print('smali_filepath method processing failed:',smali_filepath)
            return 
        with open(smali_filepath, 'r') as f:
            data=f.read()
        methods = re.findall(r'^\.method .+?\.end method$', data, re.MULTILINE | re.DOTALL)
        # 对每个方法生成调用链特征
        call_chains = get_call_chains(methods, _cls,all_classes,fields, valid_mth_set)
        chains_dict[_cls] = call_chains
    return chains_dict

def filter_class_relation(cls_rela_list):
    if len(cls_rela_list) > 10:
        cls_rela_list = cls_rela_list[:int(len(cls_rela_list)*0.8)]

def sort_feature(cls_rela_dict, chains_dict, cls_called_cnt_dict):
    # print('cls_rela_dict:',cls_rela_dict)
    cls_list = list(cls_rela_dict.keys())
    # 排序函数；输入是类关系字典；输入是各个类关系长度组成的元组；
    def get_cls_info(x):
        rela_num = len(cls_rela_dict[x][0] + cls_rela_dict[x][1] + cls_rela_dict[x][2] + cls_rela_dict[x][3] + cls_rela_dict[x][4])
        inher_num = len(cls_rela_dict[x][0])
        impl_num = len(cls_rela_dict[x][1])
        fldca_num = len(cls_rela_dict[x][2])
        mulcls_num = len(cls_rela_dict[x][3])
        mulcal_num = len(cls_rela_dict[x][4])
        union_num = len(cls_rela_dict[x][5])
        chains_num = len(chains_dict[x])
        node_num = 0
        for chain in chains_dict[x]:
            node_num += len(chain)
        return (rela_num,inher_num,impl_num,fldca_num,mulcls_num,mulcal_num,union_num,chains_num,node_num)
    # 对类进行排序
    cls_list.sort(key=get_cls_info, reverse=True)
    # 对字典中，每个类的关联类进行关系强度排序。
    # cls_rela_set_dict = dict()
    for _cls in cls_list:
        # cls_rela_set_dict[_cls] = set()
        def get_cls_rela_intensity(x):
            return cls_called_cnt_dict[_cls].get(x, 0)
        for rela_list in cls_rela_dict[_cls]:
            # 对关联类进行关系强度排序。
            rela_list.sort(key=get_cls_rela_intensity, reverse=True)
            # 添加到集合中
            # cls_rela_set_dict[_cls].add(set(rela_list))
            # 若关联类大于10个，则保留超出10个的前80%。
            # filter_class_relation(rela_list)
    # 打印类关系
    for _cls in cls_list:
        # print('cls1:{}, info:{}'.format(_cls, ','.join(str(item) for item in get_cls_info(_cls))))
        pass

    return cls_list

# def gen_signature2(cls_list, cls_rela_dict, chains_dict):
#     signature_set = set()
#     # 对每一类进行遍历
#     ele_num = 0
#     node1_index = 0
#     node2_index = 0
#     rela_index = 0
#     for _cls in cls_list:
#         para_num = 0
#         ret_num = 0
#         chain_num = 0
#         # 节点1，选取最长的，即第一个调用链
#         for chain in chains_dict[_cls][:1]:
#             for node in chain:
#                 para_num += len(node.split('_')[1])
#                 ret_num += len(node.split('_')[2])
#         chain_num = len(chains_dict[_cls])
#         node1_index = (para_num % 2) * 2 ** 7 + (ret_num % 2) * 2 ** 6 + (chain_num % 2) * 2 ** 5
#         # 遍历所有的节点2
#         rela_str = ['inher','imple','fldca','mulcls','mulcal','union']
#         rela_list = cls_rela_dict[_cls]
#         # 遍历每种关系
#         for i in range(len(rela_list)-1):
#             rela_index = i - 1 if i > 0 else i
#             rela_index = rela_index * 2 ** 3
#             for rela_cls in rela_list[i]:
#                 para_num = 0
#                 ret_num = 0
#                 chain_num = 0
#                 # 节点2
#                 for chain in chains_dict[rela_cls][:1]:
#                     for node in chain:
#                         para_num += len(node.split('_')[1])
#                         ret_num += len(node.split('_')[2])
#                 chain_num = len(chains_dict[_cls])
#                 node2_index = (para_num % 2) * 2 ** 2 + (ret_num % 2) * 2 ** 1 + chain_num % 2

#                 final_index = node1_index + rela_index + node2_index
#                 signature_set.add(final_index)
#                 ele_num += 1
    
#     print('ele_added_num2 = ',ele_num)
#     print('ele_set_num2 = ',len(signature_set))
#     return signature_set

def get_cls_info(x, cls_rela_dict, chains_dict):
    rela_num = len(cls_rela_dict[x][0] + cls_rela_dict[x][1] + cls_rela_dict[x][2] + cls_rela_dict[x][3] + cls_rela_dict[x][4])
    inher_num = len(cls_rela_dict[x][0])
    impl_num = len(cls_rela_dict[x][1])
    fldca_num = len(cls_rela_dict[x][2])
    mulcls_num = len(cls_rela_dict[x][3])
    mulcal_num = len(cls_rela_dict[x][4])
    union_num = len(cls_rela_dict[x][5])
    chains_num = len(chains_dict[x])
    node_num = 0
    for chain in chains_dict[x]:
        node_num += len(chain)
    return (rela_num,inher_num,impl_num,fldca_num,mulcls_num,mulcal_num,union_num,chains_num,node_num)

def get_chains(chains, xlen):
    node_call_chain = ''
    if len(chains) == 0:
        node_call_chain = 'DataContainer'
    else:
        xlen = xlen if xlen < len(chains) else len(chains)
        for chain in chains[:xlen]:
            node_call_chain += '->'.join(chain) + '#'
    return node_call_chain

def gen_signature(cls_list, cls_rela_dict, chains_dict):
    signature = ''
    # 提取核心类
    cls_rela_set_dict = dict()
    for _cls in cls_list:
        cls_rela_set_dict[_cls] = set()
        for rela_list in cls_rela_dict[_cls]:
            # 添加到集合中
            cls_rela_set_dict[_cls].update(set(rela_list))
    core_cls_list = []
    core_cls_cluster_set = set()
    for _cls in cls_list:
        # 若核心类为空，则直接加入
        if len(core_cls_list) == 0:
            core_cls_list.append(_cls)
            core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
        else:
            # 若当前类不在已遍历类中，则加入
            # if _cls not in core_cls_cluster_set:
            #     core_cls_list.append(_cls)
            #     core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
            # 若当前类不的关联类与已遍历类的关联类重合度小于0.2，则加入
            if len(cls_rela_set_dict[_cls]) == 0: continue
            if len(cls_rela_set_dict[_cls] & core_cls_cluster_set) == 0:
                core_cls_list.append(_cls)
                core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
    for _cls in core_cls_list:
        # print('core_cls: {}, info:{}'.format(_cls, ','.join(str(item) for item in get_cls_info(_cls, cls_rela_dict, chains_dict))))
        pass
    
    # 第一个类，即关系数最多的类。关系最强的类往往保留，但是可能变化。
    cls_max = 10000
    cls_len = cls_max if len(core_cls_list) > cls_max else len(core_cls_list)
    for _cls in core_cls_list[:cls_len]:
        rela_list = cls_rela_dict[_cls]
        # 加入核心类自身信息
        call_chain = ''
        for chain in chains_dict[_cls]:
            call_chain += '->'.join(chain) + '#'
        signature += call_chain
        rela_str = ['Inheritance','Implementing','Field_Call_Dependency','Multiple_Class_Dependency','Multiple_Call_Dependency','Union_Dependency']
        # 加入关联类信息
        for i in range(len(rela_list)-1):
            # 每种关联中，所有的类。进行关系强度排序
            for rela_cls in rela_list[i]:
                # print('rela_cls:',rela_cls)
                call_chain = ''
                if len(chains_dict[rela_cls]) == 0:
                    call_chain = 'DataContainer'
                else:
                    # 所有调用链
                    chain_max = 10000
                    chain_len = chain_max if len(chains_dict[rela_cls]) > chain_max else len(chains_dict[rela_cls])
                    for chain in chains_dict[rela_cls][:chain_len]:
                        call_chain += '->'.join(chain) + '#'
                # print('call_chain:',call_chain)
                signature += '@' + rela_str[i] + '@' + call_chain
    print('---------------------')
    print(signature)
    return signature

import hashlib

def get_signature2(cls_list, cls_rela_dict, chains_dict):
    # 提取核心类
    cls_rela_set_dict = dict()
    for _cls in cls_list:
        cls_rela_set_dict[_cls] = set()
        for rela_list in cls_rela_dict[_cls]:
            # 添加到集合中
            cls_rela_set_dict[_cls].update(set(rela_list))
    for _cls in cls_list:
        print('cls1:{}, info:{}'.format(_cls, ','.join(str(item) for item in get_cls_info(_cls, cls_rela_dict, chains_dict))))
        pass
    core_cls_list = []
    core_cls_cluster_set = set()
    for _cls in cls_list:
        # 若核心类为空，则直接加入
        if len(core_cls_list) == 0:
            core_cls_list.append(_cls)
            core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
        else:
            # 若当前类不在已遍历类中，则加入
            # if _cls not in core_cls_cluster_set:
            #     core_cls_list.append(_cls)
            #     core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
            # 若当前类不的关联类与已遍历类的关联类重合度小于0.2，则加入
            if len(cls_rela_set_dict[_cls]) == 0: continue
            if len(cls_rela_set_dict[_cls] & core_cls_cluster_set) == 0:
                core_cls_list.append(_cls)
                core_cls_cluster_set.update(set(_cls) | cls_rela_set_dict[_cls])
    for _cls in core_cls_list:
        # print('core_cls: {}, info:{}'.format(_cls, ','.join(str(item) for item in get_cls_info(_cls, cls_rela_dict, chains_dict))))
        pass
    sigs = set()
    # 第一个类，即关系数最多的类。关系最强的类往往保留，但是可能变化。
    # 采样的类数，即生成的sig数
    cls_max = 1000
    cls_len = cls_max if len(core_cls_list) > cls_max else len(core_cls_list)
    for _cls in core_cls_list[:cls_len]:
        # 每一个类生成一个sig
        sig = ''
        rela_list = cls_rela_dict[_cls]

        # 加入核心类自身信息
        sig += get_chains(chains_dict[_cls],1)
        rela_str = ['Inheritance','Implementing','Field_Call_Dependency','Multiple_Class_Dependency','Multiple_Call_Dependency','Union_Dependency']
        # 加入所有的关联类信息
        for i in range(len(rela_list)-1):
            # 每种关联中，所有的类。进行关系强度排序
            for rela_cls in rela_list[i]:
                sig += '@' + rela_str[i] + '@' + get_chains(chains_dict[rela_cls],1)
        sigs.add(sig)
    # 对每一个签名进行哈希
    hash_set = set()
    for sig in sigs:
        hash_v = hashlib.sha256(sig.encode()).hexdigest()
        hash_set.add(hash_v)
    return hash_set, sigs

def get_node_sigs(cls_list, cls_rela_dict, chains_dict):
    final_set = set()
    ele_num = 0
    # 对每一类进行遍历
    for _cls in cls_list:
        # 源节点过滤明显的第三方库
        if _cls.startswith('Landroid/support/'):
            continue
        node1 = ''
        if len(chains_dict[_cls]) == 0:
            node1 = 'DataContainer'
        else:
            for chain in chains_dict[_cls][0]:
                node1 += '->'.join(chain) + '#'
        # 遍历所有的节点2
        rela_str = ['inher','imple','fldca','mulcls','mulcal','union']
        rela_list = cls_rela_dict[_cls]
        # 遍历每种关系
        for i in range(len(rela_list)-1):
            for rela_cls in rela_list[i]:
                # 节点2
                node2 = ''
                if len(chains_dict[rela_cls]) == 0:
                    # print('DataContainer:',rela_cls)
                    node2 = 'DataContainer'
                else:
                    for chain in chains_dict[rela_cls][0]:
                        node2 += '->'.join(chain) + '#'
                
                # _element = node1 + '@' +  rela_str[i] + '@' + node2 
                _element = '(' + _cls + ')' + node1 + '@' +  rela_str[i] + '@' + node2 + '(' + rela_cls + ')'
                ele_num += 1
                final_set.add(_element)

    hash_set = set()
    for sig in final_set:
        hash_v = hashlib.sha256(sig.encode()).hexdigest()
        hash_set.add(hash_v)
    return hash_set

def get_node_set(cls_list, cls_rela_dict, chains_dict):
    final_set = set()
    ele_num = 0
    # 对每一类进行遍历
    for _cls in cls_list:
        # 源节点过滤明显的第三方库
        if _cls.startswith('Landroid/support/'):
            continue
        node1 = ''
        if len(chains_dict[_cls]) == 0:
            node1 = 'DataContainer'
        else:
            for chain in chains_dict[_cls][0]:
                node1 += '->'.join(chain) + '#'
        # 遍历所有的节点2
        rela_str = ['inher','imple','fldca','mulcls','mulcal','union']
        rela_list = cls_rela_dict[_cls]
        # 遍历每种关系
        for i in range(len(rela_list)-1):
            for rela_cls in rela_list[i]:
                # 节点2
                node2 = ''
                if len(chains_dict[rela_cls]) == 0:
                    # print('DataContainer:',rela_cls)
                    node2 = 'DataContainer'
                else:
                    for chain in chains_dict[rela_cls][0]:
                        node2 += '->'.join(chain) + '#'
                
                _element = node1 + '@' +  rela_str[i] + '@' + node2 
                # _element = '(' + _cls + ')' + node1 + '@' +  rela_str[i] + '@' + node2 + '(' + rela_cls + ')'
                ele_num += 1
                final_set.add(_element)
    print('ele_added_num = ',ele_num)
    print('ele_set_num = ',len(final_set))
    return final_set

def summary_class_relations(cls_list, cls_rela_dict):
    inher_cnt = 0
    impl_cnt = 0
    dep_cnt = 0
    assoc_cnt = 0
    agg_cnt = 0
    comp_cnt = 0
    node_num = 0
    for _cls in cls_list:
        rela_list = cls_rela_dict[_cls]
        inher_cnt += len(rela_list[0])
        impl_cnt += len(rela_list[1])
        dep_cnt += len(rela_list[2])
        assoc_cnt += len(rela_list[3])
        agg_cnt += len(rela_list[4])
        comp_cnt += len(rela_list[5])
        node_num += 1
    print('cls_num:',node_num)
    print('inher_cnt:{},impl_cnt:{},fieldcall:{},mulclass:{},mulcall:{},union:{}'.format(inher_cnt,impl_cnt,dep_cnt,assoc_cnt,agg_cnt,comp_cnt))
    f = open('res_class_relations.txt','a')
    f.write('cls_num:{},inher_cnt:{},impl_cnt:{},fieldcall:{},mulclass:{},mulcall:{},union:{}\n'.format(node_num,inher_cnt,impl_cnt,dep_cnt,assoc_cnt,agg_cnt,comp_cnt))
    f.close()

def summary_call_chains(chains_dict):
    chain_num = 0
    call_num = 0
    for key, value in chains_dict.items():
        chain_num += len(value)
        for chain in value:
            call_num += len(chain)
    print('chain_num:',chain_num)
    print('call_num:',call_num)
    f = open('res_call_chains.txt','a')
    f.write('chain_num:{},call_num:{}\n'.format(chain_num,call_num))
    f.close()

import numpy
import seaborn as sns
import matplotlib.pyplot as plt


def virtualize_cls_rela(cls_rela_dict, cls_called_cnt_dict,apk_path):
    cls_list = list(cls_rela_dict.keys())

    prefix_list = []
    prefix_cnt_dict = dict()
    for _cls in cls_list:
        prefix_cls = _cls[:_cls.rfind('/')]
        # 建立prefix列表
        if prefix_cls not in prefix_list:
            prefix_list.append(prefix_cls)
        old_dict = prefix_cnt_dict.get(prefix_cls, dict())
        # 建立prefix_cnt字典
        _cls_dict = cls_called_cnt_dict[_cls]
        add_dict = dict()
        for _key in _cls_dict.keys():
            _prefix = _key[:_key.rfind('/')]
            add_dict[_prefix] = add_dict.get(_prefix, 0) + _cls_dict[_key]
        mergerd_dict = {key: old_dict.get(key, 0) + add_dict.get(key, 0) for key in set(old_dict) | set(add_dict)}
        prefix_cnt_dict[prefix_cls] = mergerd_dict
    prefix_list.sort()

    # for prefix in prefix_cnt_dict.keys():
    #     print('prefix: ', prefix)
    # for _cls in cls_list:
    #     print('cls:{}, cls_called_cnt_dict:{}'.format(_cls, cls_called_cnt_dict[_cls]))
    matrix_data = np.zeros((len(prefix_list), len(prefix_list)))
    for _cls_row in prefix_list:
        for _cls_col in prefix_list:
            matrix_data[prefix_list.index(_cls_row)][prefix_list.index(_cls_col)] = prefix_cnt_dict[_cls_row].get(_cls_col, 0)
    sns.heatmap(matrix_data, cmap='coolwarm')
    apkname = apk_path.split('/')[-1]
    plt.savefig('./figure/cls_rela_{}.png'.format(apkname))
                

def generate_bin(apk_path):
    # apk_path = './apk_pairs/0/000595C346096B92B073F3A7C055FFE466EDCF3E51E017C280FEAB641E3D95D3.apk'
    global node_dict,node_set,traverse_map, relation_map, hava_parent, node_list, max_depth, traverse_cnt, root_cnt, final_opseq
    global final_opseq_str, all_class, node_properti_dict
    traverse_map = dict()
    relation_map = dict()
    hava_parent = dict()
    node_list = []
    max_depth = 0
    traverse_cnt = 0
    root_cnt = 0
    final_opseq = bytearray()  
    node_dict = dict()
    node_set = set()
    final_opseq_str = ''
    node_properti_dict = dict()

    # apk_name = apk_path.split('/')[-1]

    # shutil.rmtree(smali_dir)
    preproccess_apk(apk_path)
    # 垃圾类
    smali_dir='./out'
    smali_filepaths=list_files(smali_dir)
    for path in smali_filepaths:
        ft = open(path, 'r')
        content = ft.read()
        ft.close() 
        # 删除dasho新增加的RuntimeException类
        if re.findall(r'.super Ljava/lang/RuntimeException;', content):
            # print('delete RuntimeException, path:',path)
            os.remove(path)
        # # 删除support库
        # elif re.findall(r'Landroid/support/', content.split('\n')[0]):
        #     os.remove(path)
        # 删除dasho特有类
        # if len(re.findall(r'\.method.+?\.end method', content, re.DOTALL))==1:
        #     if re.findall('.method public static .*?\(Ljava/lang/String;I\)Ljava/lang/String;', content):
        #         class_name = content.split('\n')[0].split(' ')[-1]
        #         print('delete dasho specific class:',class_name)
        #         os.remove(path)
        #     if re.findall('.method public static .*?\(ILjava/lang/String;\)Ljava/lang/String;', content):
        #         class_name = content.split('\n')[0].split(' ')[-1]
        #         print('delete dasho specific class:',class_name)
        #         os.remove(path)
    # 获取所有类
    all_classes, valid_mth_set = get_all_classes(smali_dir)
    # 分析类之间的关系
    cls_rela_dict, cls_called_cnt_dict = gen_class_relations(all_classes, smali_dir)
    # 分析调用链
    chains_dict = gen_call_chains(all_classes, valid_mth_set)
    # 对特征进行排序
    cls_list = sort_feature(cls_rela_dict, chains_dict, cls_called_cnt_dict)
    # 获得最强关系类签名，用来第一阶段检测
    # hashes, sigs = get_signature2(cls_list, cls_rela_dict, chains_dict)
    # with open('./res/hash_set_{}.txt'.format(apk_name), 'w') as file:
    #     for hash_value in signature:
    #         file.write(f"{hash_value}\n")
    # signature = gen_signature(cls_list, cls_rela_dict, chains_dict)
    # signature = gen_signature2(cls_list, cls_rela_dict, chains_dict)
    # f = open('./res/signature_{}.txt'.format(apk_name),'w')
    # f.write(signature)
    # f.close()
    # 获得节点集合，用来第二阶段检测
    node_hash = get_node_sigs(cls_list, cls_rela_dict, chains_dict)
    node_set = get_node_set(cls_list, cls_rela_dict, chains_dict)
    # f = open('./res/node_set_{}.txt'.format(apk_name),'w')
    # for _ele in node_set:
    #     f.write(_ele)
    #     f.write('\n')
    # f.close()
    # 类关系强度可视化
    # virtualize_cls_rela(cls_rela_dict, cls_called_cnt_dict,apk_path)
    # 打印类关系和调用链
    summary_class_relations(cls_list, cls_rela_dict)
    summary_call_chains(chains_dict)
    # gen_node_final_feature(all_classes, class_rela_list,junk_class)
    # with open('{}.bin'.format(apk_path.split('/')[-1]), 'wb') as f:  
    #     f.write(final_opseq)  
    return node_set, node_hash

def save_set(signature, path):

    # with open(path, 'w') as file:
    #     for hash_value in signature:
    #         file.write(f"{hash_value}\n")

    signature_list = list(signature)
    signature_list.sort()
    print('signature_list:',signature_list)
    with open(path, 'w') as file:
        for hash_value in signature_list:
            file.write(f"{hash_value}\n")

def read_set(path):
    hash_set = set()
    with open(path, 'r') as file:
        for line in file:
            hash_set.add(line.strip())
    return hash_set

if __name__=='__main__':
    # 只计算并保存一个apk的signature和node_set
    # path1 = sys.argv[1]
    # apk_name = path1.split('/')[-1]
    # hashes, sigs, node_set = generate_bin(path1)
    # save_set(sigs, './res/signature_{}.txt'.format(apk_name))
    # save_set(hashes, './res/hash_set_{}.txt'.format(apk_name))
    # save_set(node_set, './res/node_set_{}.txt'.format(apk_name))
    

    
    # 第二阶段：对第一阶段通过的应用，进行set的相似度计算，设置阈值2。我使用了两种相似度计算方式，你尝试一下，挑较好的一种，应该会是第一种。
    # 保存的文件，见generate_bin函数
    path1 = sys.argv[1]
    node_set_1, node_hash_1 = generate_bin(path1)
    path2 = sys.argv[2]
    node_set_2, node_hash_2 = generate_bin(path2)
    
    save_set(node_set_1, './res/node_set_{}.txt'.format(path1.split('/')[-1]))
    save_set(node_set_2, './res/node_set_{}.txt'.format(path2.split('/')[-1]))
    save_set(node_hash_1, './res/node_hash_{}.txt'.format(path1.split('/')[-1]))
    save_set(node_hash_2, './res/node_hash_{}.txt'.format(path2.split('/')[-1]))
    # print('union signature cnt:',len(hashes1 & hashes2))

    # 第一阶段：先对signature使用ssdeep生成hash，进行hash匹配，设置阈值1
    # hashes1 = read_set('./res/hash_set_{}.txt'.format(path1.split('/')[-1]))
    # hashes2 = read_set('./res/hash_set_{}.txt'.format(path2.split('/')[-1]))
    # print('hashes1:',hashes1)
    # print('hashes2:',hashes2)
    # print('union signature cnt:',len(hashes1 & hashes2))

    # 第二阶段：计算node_set的相似度
    node_set_1 = read_set('./res/node_set_{}.txt'.format(path1.split('/')[-1]))
    node_set_2 = read_set('./res/node_set_{}.txt'.format(path2.split('/')[-1]))
    union_set = node_set_1 & node_set_2
    similarity = max(len(union_set) / float(len(node_set_1)), len(union_set) / float(len(node_set_2)))
    print("apk1 has {} methods, apk2 has {} methods. Similarity score:{}".format(len(node_set_1),len(node_set_2),similarity))