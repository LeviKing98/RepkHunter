import os
import subprocess
import shutil

"""
涉及到的命令和脚本：
1. 从apk文件中提取出classes.dex文件
unzip apk_path -d ./unzip_apk/apk_name

2. 将classes.dex文件转换为smali文件
./baksmali disassemble ./unzip_apk/apk_name/classes.dex
默认情况下，smali文件会被放在当前目录下的out文件夹中，使用该命令前先清空out文件夹
"""

def unzip_apk(apk_path):
    """
    解压apk文件
    """
    apk_name=apk_path.split('/')[-1].split('.apk')[0]
    unzip_path='./unzip_apk/'+apk_name
    if os.path.exists(unzip_path):
        shutil.rmtree(unzip_path)
    cmd=f'unzip {apk_path} -d {unzip_path}'
    result=subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode!=0:
        print(f'解压apk失败，apk_path={apk_path}')
        print(result.stderr)
    else:
        print(f'解压apk成功，apk_path={apk_path}')
    
def disassemble_dex(dex_path):
    """
    反编译dex文件
    """
    cmd=f'./baksmali disassemble {dex_path}'
    result=subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode!=0:
        print(f'反编译dex文件失败，dex_path={dex_path}')
        print(result.stderr)
    else:
        print(f'反编译dex文件成功，dex_path={dex_path}')

def preproccess_apk(apk_path):
    """
    预处理apk文件
    """
    unzip_apk(apk_path)
    apk_name=apk_path.split('/')[-1].split('.apk')[0]
    unzip_path=f'./unzip_apk/{apk_name}'
    # 可能有多个dex文件
    if os.path.exists('./out'):
        shutil.rmtree('./out')
    file_list=os.listdir(unzip_path)
    for file in file_list:
        if file.startswith('classes') and file.endswith('.dex'):
            dex_path=os.path.join(unzip_path,file)
            disassemble_dex(dex_path)
    # 清理解压文件
    if os.path.exists(unzip_path):
        shutil.rmtree(unzip_path)
    
if __name__=='__main__':
    apk_path='./000D753E7C480FA12D69FD826890683B786E4C344C52A193F1AABE07542D4EFE.apk'
    preproccess_apk(apk_path)