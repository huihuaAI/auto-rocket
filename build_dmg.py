#!/usr/bin/env python3
"""
macOS DMG 打包脚本
使用 uv 管理依赖和打包环境
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description="", check=True):
    """执行命令并显示输出"""
    if description:
        print(f"\n{'='*60}")
        print(f"🔧 {description}")
        print(f"{'='*60}")

    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True)

    if check and result.returncode != 0:
        print(f"❌ 命令执行失败: {cmd}")
        sys.exit(1)

    return result

def main():
    print("""
    ╔════════════════════════════════════════════════════╗
    ║       RocketGo - macOS DMG 打包脚本                ║
    ║       使用 uv + PyInstaller                        ║
    ╚════════════════════════════════════════════════════╝
    """)

    # 1. 检查是否在macOS上
    if sys.platform != 'darwin':
        print("⚠️  警告: 此脚本设计用于macOS系统")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

    # 2. 创建图标
    if not os.path.exists('icon.icns'):
        print("\n📦 步骤 1: 生成应用图标")
        if not os.path.exists('icon.png'):
            print("  未找到icon.png，将创建默认图标")
            run_command('uv run python create_icon.py', '创建默认图标')
        else:
            print("  使用现有的icon.png")
            run_command('uv run python create_icon.py --use-existing', '从PNG生成ICNS')
    else:
        print("\n✅ 图标文件已存在: icon.icns")

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

    # 5. 复制必要的配置文件到.app包
    print("\n📦 步骤 4: 复制配置文件")
    app_path = os.path.join('dist', 'RocketGo.app')
    resources_dir = os.path.join(app_path, 'Contents', 'Resources')
    os.makedirs(resources_dir, exist_ok=True)

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
            shutil.copy2(file, resources_dir)
            print(f"  ✅ 已复制: {file}")

    # 6. 创建DMG
    print("\n📦 步骤 5: 创建 DMG 安装包")

    dmg_name = "RocketGo-macOS.dmg"
    temp_dmg = "temp.dmg"

    # 移除旧的DMG文件
    for dmg in [dmg_name, temp_dmg]:
        if os.path.exists(dmg):
            os.remove(dmg)
            print(f"  清理旧文件: {dmg}")

    # 创建临时DMG目录
    dmg_dir = "dmg_temp"
    if os.path.exists(dmg_dir):
        shutil.rmtree(dmg_dir)
    os.makedirs(dmg_dir)

    # 复制.app到临时目录
    shutil.copytree(app_path, os.path.join(dmg_dir, 'RocketGo.app'))

    # 创建应用程序快捷方式
    run_command(
        f'ln -s /Applications "{dmg_dir}/Applications"',
        '创建应用程序文件夹快捷方式',
        check=False
    )

    # 使用hdiutil创建DMG
    print("\n  使用 hdiutil 创建 DMG...")

    # 创建临时DMG
    run_command(
        f'hdiutil create -volname "RocketGo" -srcfolder "{dmg_dir}" -ov -format UDRW "{temp_dmg}"',
        '创建可读写DMG'
    )

    # 转换为压缩的只读DMG
    run_command(
        f'hdiutil convert "{temp_dmg}" -format UDZO -o "{dmg_name}"',
        '转换为压缩DMG'
    )

    # 清理临时文件
    print("\n  清理临时文件...")
    if os.path.exists(temp_dmg):
        os.remove(temp_dmg)
    if os.path.exists(dmg_dir):
        shutil.rmtree(dmg_dir)

    # 7. 完成
    print("\n" + "="*60)
    print("✅ 打包完成!")
    print("="*60)
    print(f"\n📂 .app 文件: {os.path.abspath(app_path)}")
    print(f"💿 DMG 文件: {os.path.abspath(dmg_name)}")
    print(f"\n📦 文件大小:")

    # 显示文件大小
    if os.path.exists(dmg_name):
        dmg_size = os.path.getsize(dmg_name) / (1024 * 1024)
        print(f"  DMG: {dmg_size:.2f} MB")

    print("\n💡 使用说明:")
    print("  1. 打开 DMG 文件")
    print("  2. 将 RocketGo.app 拖到 Applications 文件夹")
    print("  3. 首次运行可能需要在「系统偏好设置 > 安全性与隐私」中允许")
    print("\n🎯 数据文件位置:")
    print("  应用数据目录: ~/Library/Application Support/RocketGo/")
    print("  - config.toml (配置文件)")
    print("  - auto_reply.log (日志文件)")
    print("  - conversations.db (数据库)")
    print("  也可以在应用内通过GUI界面配置")

if __name__ == '__main__':
    main()