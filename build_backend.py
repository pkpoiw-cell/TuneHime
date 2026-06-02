"""
音姬 TuneHime - Python 后端打包脚本

使用 PyInstaller 将 Python 后端打包成独立的 .exe 文件
"""

import subprocess
import os
import shutil
import sys

# 项目路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_DIR, 'python-backend')
DIST_DIR = os.path.join(PROJECT_DIR, 'python-backend', 'dist')
BUILD_DIR = os.path.join(PROJECT_DIR, 'python-backend', 'build')

# 入口文件
ENTRY_FILE = os.path.join(BACKEND_DIR, 'server.py')

# 输出文件名
OUTPUT_NAME = 'server'

def clean():
    """清理旧的构建文件"""
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f'已清理: {dir_path}')

def build():
    """执行打包"""
    print('='*50)
    print('音姬 TuneHime - Python 后端打包')
    print('='*50)

    # 确保入口文件存在
    if not os.path.exists(ENTRY_FILE):
        print(f'错误: 入口文件不存在: {ENTRY_FILE}')
        return False

    # PyInstaller 参数
    args = [
        sys.executable, '-m', 'PyInstaller',
        ENTRY_FILE,
        '--name', OUTPUT_NAME,
        '--onefile',                    # 打包成单个文件
        '--console',                    # 控制台应用
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不询问确认
        # 添加依赖
        '--hidden-import', 'websockets',
        '--hidden-import', 'websockets.server',
        '--hidden-import', 'pedalboard',
        '--hidden-import', 'sounddevice',
        '--hidden-import', 'numpy',
        '--hidden-import', 'scipy',
        # 排除不需要的模块
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'PyQt5',
        '--exclude-module', 'PyQt6',
    ]

    print(f'\n入口文件: {ENTRY_FILE}')
    print(f'输出目录: {DIST_DIR}')
    print(f'\n开始打包...\n')

    try:
        result = subprocess.run(args, check=True, capture_output=False)

        # 检查输出
        output_path = os.path.join(DIST_DIR, f'{OUTPUT_NAME}.exe')
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f'\n打包成功!')
            print(f'输出文件: {output_path}')
            print(f'文件大小: {size_mb:.1f} MB')
            return True
        else:
            print(f'\n打包失败: 输出文件不存在')
            return False

    except subprocess.CalledProcessError as e:
        print(f'\n打包失败: {e}')
        return False
    except Exception as e:
        print(f'\n打包失败: {e}')
        return False

def copy_to_electron():
    """将打包后的文件复制到 Electron 目录"""
    src = os.path.join(DIST_DIR, f'{OUTPUT_NAME}.exe')
    dst_dir = os.path.join(PROJECT_DIR, 'electron-app', 'resources', 'server')
    dst = os.path.join(dst_dir, f'{OUTPUT_NAME}.exe')

    os.makedirs(dst_dir, exist_ok=True)

    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'已复制到: {dst}')
        return True
    return False

if __name__ == '__main__':
    clean()
    if build():
        copy_to_electron()
