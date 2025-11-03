import base64
from PIL import Image
from io import BytesIO


def base64_to_image(base64_str, output_path):
    """
    将Base64编码字符串转换为图片并保存

    参数:
        base64_str: Base64编码字符串
        output_path: 图片保存路径，如"output.png"
    """
    try:
        # 解码Base64数据
        image_data = base64.b64decode(base64_str)

        # 将字节数据转换为图片
        image = Image.open(BytesIO(image_data))

        # 保存图片
        image.save(output_path)
        print(f"图片已成功保存至: {output_path}")
        return True
    except Exception as e:
        print(f"转换失败: {str(e)}")
        return False
