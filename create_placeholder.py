import os
import base64

# Создаем папки
os.makedirs("static/images", exist_ok=True)

# Base64 для черного пикселя 1x1 (JPEG)
placeholder_base64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="

# Декодируем и записываем файл
image_data = base64.b64decode(placeholder_base64)
with open("static/images/placeholder.jpg", "wb") as f:
    f.write(image_data)

print("✅ Файл placeholder.jpg создан в static/images/")

# Также создаем другие изображения-заглушки
for i in range(1, 7):
    with open(f"static/images/product{i}.jpg", "wb") as f:
        f.write(image_data)
    print(f"✅ Создан product{i}.jpg")

for i in range(1, 4):
    with open(f"static/images/carousel{i}.jpg", "wb") as f:
        f.write(image_data)
    print(f"✅ Создан carousel{i}.jpg")

print("🎉 Все placeholder изображения созданы!")