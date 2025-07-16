import pandas as pd
import os

def convert_excel_to_query(file_path):
    try:
        # 读取 Excel 文件
        df = pd.read_excel(file_path, header=None)  # 假设没有表头

        # 提取第一列的数据
        items = df.iloc[:, 0].dropna().tolist()  # 去掉空值

        # 转换为所需的格式
        result = " OR ".join([f"handle:{item}" for item in items])

        return result
    except Exception as e:
        return f"发生错误：{e}"

# 示例：使用脚本
if __name__ == "__main__":
    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # 指定 Excel 文件名
    excel_file_name = "test.xlsx"  # 替换为你的文件名
    file_path = os.path.join(desktop_path, excel_file_name)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在，请检查路径和文件名是否正确！")
    else:
        # 转换并获取结果
        result = convert_excel_to_query(file_path)

        # 打印结果到控制台
        print("转换结果：")
        print(result)