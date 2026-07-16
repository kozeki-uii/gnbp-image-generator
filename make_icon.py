import os
from PIL import Image

# 配置区
INPUT_IMG = 'logo.png'
OUTPUT_ICO = 'app_icon.ico'


def create_icon():
    if not os.path.exists(INPUT_IMG):
        print(f"❌ 错误: 找不到源图片 '{INPUT_IMG}'")
        return

    try:
        # 1. 打开图片
        img = Image.open(INPUT_IMG)

        # 确保图片是 RGBA 模式 (处理透明背景)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 2. 定义尺寸
        # 包含了 256 (大图标), 48 (大任务栏), 32 (标准任务栏), 16 (标题栏/小任务栏)
        # 注意：顺序很重要，通常把大的放在前面，或者按 Pillow 要求列表
        size_list = [256, 128, 64, 48, 32, 16]

        # 3. 【核心修改】手动使用 LANCZOS 算法进行高质量重采样
        resampled_images = []
        for s in size_list:
            # 使用 LANCZOS 滤镜进行缩放，抗锯齿效果最好
            new_img = img.resize((s, s), Image.Resampling.LANCZOS)
            resampled_images.append(new_img)

        # 4. 保存为 ICO
        # append_images 参数允许我们将处理好的多个图片打包进同一个 ICO 文件
        # save 的第一个对象作为主图，其余的放在 append_images 里
        resampled_images[0].save(
            OUTPUT_ICO,
            format='ICO',
            append_images=resampled_images[1:]
        )

        print(f"✅ 高清图标生成成功: {OUTPUT_ICO}")
        print(f"   (包含尺寸: {size_list}，已应用 LANCZOS 抗锯齿)")

    except Exception as e:
        print(f"❌ 生成过程中出错: {e}")


if __name__ == '__main__':
    create_icon()