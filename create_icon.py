#!/usr/bin/env python3
"""
生成应用图标
如果你有自己的图标，请替换 icon.png 为你的图标文件
"""
import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont

def create_default_icon():
    """创建一个简单的默认图标"""
    # 创建一个256x256的图标
    size = 256
    img = Image.new('RGB', (size, size), color='#4A90E2')
    draw = ImageDraw.Draw(img)

    # 绘制一个简单的"RG"字母（代表RocketGo）
    try:
        # macOS
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
    except:
        try:
            # Windows
            font = ImageFont.truetype("C:\\Windows\\Fonts\\Arial.ttf", 120)
        except:
            # 备用默认字体
            font = ImageFont.load_default()

    # 绘制白色文字
    text = "RG"
    # 计算文字位置使其居中
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2 - 10)

    draw.text(position, text, fill='white', font=font)

    # 保存PNG图标
    img.save('icon.png', 'PNG')
    print("✅ 已创建 icon.png")

    return img

def create_ico_from_png(png_path='icon.png'):
    """从PNG创建ICO文件（Windows）"""
    img = Image.open(png_path)
    # ICO支持多个尺寸
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save('icon.ico', format='ICO', sizes=icon_sizes)
    print("✅ 已创建 icon.ico (Windows)")

def create_icns_from_png(png_path='icon.png'):
    """从PNG创建ICNS文件（macOS）"""
    # 创建iconset目录
    iconset_path = 'icon.iconset'
    os.makedirs(iconset_path, exist_ok=True)

    img = Image.open(png_path)

    # macOS需要的所有尺寸
    sizes = [
        (16, 'icon_16x16.png'),
        (32, 'icon_16x16@2x.png'),
        (32, 'icon_32x32.png'),
        (64, 'icon_32x32@2x.png'),
        (128, 'icon_128x128.png'),
        (256, 'icon_128x128@2x.png'),
        (256, 'icon_256x256.png'),
        (512, 'icon_256x256@2x.png'),
        (512, 'icon_512x512.png'),
        (1024, 'icon_512x512@2x.png'),
    ]

    for size, filename in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(iconset_path, filename))

    # 使用iconutil转换为icns（仅macOS）
    try:
        subprocess.run(['iconutil', '-c', 'icns', iconset_path], check=True)
        print("✅ 已创建 icon.icns (macOS)")
    except FileNotFoundError:
        print("⚠️  iconutil未找到，跳过icns创建（仅macOS可用）")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  创建icns失败: {e}")

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════╗
    ║       RocketGo 图标生成工具            ║
    ╚════════════════════════════════════════╝
    """)

    use_existing = '--use-existing' in sys.argv

    if use_existing:
        # 使用现有的icon.png
        png_path = 'icon.png'
        if not os.path.exists(png_path):
            print("❌ 找不到 icon.png，请先准备图标文件")
            sys.exit(1)
        print("📝 使用现有的 icon.png")
    else:
        # 创建默认图标
        print("🎨 创建默认图标...")
        create_default_icon()

    # 生成ICO和ICNS
    print("\n📦 生成图标文件...")
    create_ico_from_png()
    create_icns_from_png()

    print("\n✅ 图标创建完成！")
    if not use_existing:
        print("💡 提示：如果需要自定义图标，请替换 icon.png 后运行:")
        print("   uv run python create_icon.py --use-existing")