import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env
load_dotenv()

# 获取 API Key
api_key = os.getenv('DEEPSEEK_API_KEY')

if not api_key:
    print("❌ 错误：未找到 DEEPSEEK_API_KEY，请检查 .env 文件")
    exit(1)

print(f"✅ API Key 已加载: {api_key[:10]}...")

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

try:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "说一句话证明你连接成功了"}
        ],
        max_tokens=50
    )
    print(f"✅ 调用成功！回复: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ 调用失败: {e}")