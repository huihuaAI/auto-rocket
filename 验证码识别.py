import ddddocr
import requests
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

if __name__ == '__main__':

    login_url = "https://pn3cs.rocketgo.vip/prod-api1/captchaImage"


    response = requests.get(login_url)
    code = response.json()["code"]
    if code != 200:
        print("获取验证码失败")
        print(response.json())
        exit()
    uuid = response.json()["uuid"]
    img = response.json()["img"]
    # 保存验证码base64图片
    base64_to_image(img, "验证码.png")
    ocr = ddddocr.DdddOcr()
    # 读取验证码图片
    image = open("验证码.png", "rb").read()
    result = ocr.classification(image)
    print(result)
