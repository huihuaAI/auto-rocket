#!/usr/bin/env python3
"""
Windows EXE 打包脚本
使用 uv 管理依赖和打包环境
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description=""):
    """执行命令并显示输出"""
    if description:
        print(f"\n{'='*60}")
        print(f"🔧 {description}")
        print(f"{'='*60}")

    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"❌ 命令执行失败: {cmd}")
        sys.exit(1)

    return result

def main():
    print("""
    ╔════════════════════════════════════════════════════╗
    ║       RocketGo - Windows EXE 打包脚本              ║
    ║       使用 uv + PyInstaller                        ║
    ╚════════════════════════════════════════════════════╝
    """)

    # 1. 检查是否在Windows上
    if sys.platform != 'win32':
        print("⚠️  警告: 此脚本设计用于Windows系统")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

    # 2. 创建图标
    if not os.path.exists('icon.ico'):
        print("\n📦 步骤 1: 生成应用图标")
        if not os.path.exists('icon.png'):
            print("  未找到icon.png，将创建默认图标")
            run_command('uv run python create_icon.py', '创建默认图标')
        else:
            print("  使用现有的icon.png")
            run_command('uv run python create_icon.py --use-existing', '从PNG生成ICO')
    else:
        print("\n✅ 图标文件已存在: icon.ico")

    # 3. 安装打包依赖
    print("\n📦 步骤 2: 安装打包依赖")
    run_command('uv pip install pyinstaller', '安装 PyInstaller')

    # 4. 使用PyInstaller打包
    print("\n📦 步骤 3: 使用 PyInstaller 打包")

    # 清理之前的构建
    if os.path.exists('dist'):
        print("  清理旧的构建文件...")
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    # 构建命令
    pyinstaller_cmd = 'uv run pyinstaller RocketGo.spec --clean --noconfirm'

    run_command(pyinstaller_cmd, '执行 PyInstaller 打包')

    # 5. 复制必要的配置文件
    print("\n📦 步骤 4: 复制配置文件")
    dist_dir = os.path.join('dist', 'RocketGo')

    # 确保config.toml文件存在
    if not os.path.exists('config.toml'):
        if os.path.exists('config.toml.example'):
            print("  📋 config.toml 不存在，从 config.toml.example 复制...")
            shutil.copy2('config.toml.example', 'config.toml')
            print("  ✅ 已创建: config.toml")
        else:
            print("  ⚠️  警告: config.toml 和 config.toml.example 都不存在")

    files_to_copy = ['config.toml', 'README.md']
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, dist_dir)
            print(f"  ✅ 已复制: {file}")

    # 6. 完成
    print("\n" + "="*60)
    print("✅ 打包完成!")
    print("="*60)
    print(f"\n📂 输出目录: {os.path.abspath(dist_dir)}")
    print(f"🚀 可执行文件: {os.path.join(dist_dir, 'RocketGo.exe')}")
    print("\n💡 提示:")
    print("  1. 确保系统已安装必要的运行时库")
    print("  2. 可以使用 NSIS 或 Inno Setup 创建安装程序")
    print("\n🎯 数据文件位置:")
    print("  应用数据目录: %APPDATA%\\RocketGo\\")
    print("  - config.toml (配置文件)")
    print("  - auto_reply.log (日志文件)")
    print("  - conversations.db (数据库)")
    print("\n📦 创建发布包:")
    print(f"  可以压缩 dist\\RocketGo 文件夹为 RocketGo-Windows.zip 进行分发")

if __name__ == '__main__':
    main()