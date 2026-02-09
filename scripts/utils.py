import os

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

def parse_method_parameters(param_string):
    """
    解析方法参数
    """
    
    index = 0 
    params = []    
        
    while index < len(param_string):
        if param_string[index] == 'T':
            # 处理泛型，这种泛型不重要，我关心的是自定义类作为泛型参数
            end_index = index
            while True:
                end_index += 1
                if param_string[end_index] == ';':
                    break
            params.append(param_string[index:end_index+1])
            index = end_index + 1
        elif param_string[index] in "ZBCSIFJD":    
            # 处理基本类型    
            params.append(param_string[index])    
            index += 1    
        elif param_string[index] == 'L':    
            # 处理对象类型（包括泛型信息）  
            end_index = index  
            depth = 0  # 用于跟踪泛型深度  
            while True:  
                end_index += 1  
                if param_string[end_index] == ';':  
                    # 泛型深度为0时，表示到达类型描述符末尾  
                    if depth == 0:  
                        break  
                elif param_string[end_index] == '<':  
                    depth += 1  # 进入泛型  
                elif param_string[end_index] == '>':  
                    depth -= 1  # 离开泛型  
            params.append(param_string[index:end_index+1])  
            index = end_index + 1    
        elif param_string[index] == '[':    
            # 处理数组类型    
            array_start_index = index    
            index += 1  
            # 多维数组    
            while param_string[index] == '[':    
                index += 1    
            if param_string[index] == 'T':
                # 处理泛型
                end_index = index
                while True:
                    end_index += 1
                    if param_string[end_index] == ';':
                        break
                index = end_index + 1
            elif param_string[index] in "ZBCSIFJD":    
                # 基本类型数组    
                index += 1    
            elif param_string[index] == 'L':    
                # 对象类型数组（包括泛型信息）  
                end_index = index  
                depth = 0  # 用于跟踪泛型深度  
                while True:  
                    end_index += 1  
                    if param_string[end_index] == ';':  
                        # 泛型深度为0时，表示到达类型描述符末尾  
                        if depth == 0:  
                            break  
                    elif param_string[end_index] == '<':  
                        depth += 1  # 进入泛型  
                    elif param_string[end_index] == '>':  
                        depth -= 1  # 离开泛型  
                index = end_index + 1  
            params.append(param_string[array_start_index:index])    
    return params  

if __name__=='__main__':
    dir='test_out'
    list_files(dir)