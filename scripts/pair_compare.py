import os
import sys

apk_path1 = sys.argv[1]
apk_path2 = sys.argv[2]
apk_name1 = apk_path1.split('/')[-1]
apk_name2 = apk_path2.split('/')[-1]

os.system('python ./RepkHunter.py {} > log1'.format(apk_path1))
os.system('python ./RepkHunter.py {} > log2'.format(apk_path2))

os.system('ssdeep -b ./res/final_{}.txt > h1'.format(apk_name1))
os.system('ssdeep -b ./res/final_{}.txt > h2'.format(apk_name2))
os.system('ssdeep -a -k ./h1 ./h2')