#识别图片
img_files=["C:/Users/thv/Desktop/1.jpg"]
import paddleocr
ocr=paddleocr.PaddleOCR(use_angle_cls=True,lang="ch")
result = ocr.ocr(img_files)
print(result[0]['input_path'])

for item in result:
    print(item['input_path'])
    print(item['rec_texts'])
