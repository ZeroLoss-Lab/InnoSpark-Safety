
import os

# 获取当前 Python 脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 切换到该目录
os.chdir(script_dir)
import subprocess

# 执行当前目录下的 shell 脚本（如 `script.sh`）
subprocess.run(["bash", "sft.sh"], check=True)