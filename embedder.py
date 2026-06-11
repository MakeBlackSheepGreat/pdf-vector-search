"""嵌入模型封装"""

from llama_index.embeddings.openai import OpenAIEmbedding


class SiliconFlowEmbedding(OpenAIEmbedding):
    """硅基流动嵌入模型（兼容 OpenAI 接口）"""

    def __init__(self, api_key: str, model_name: str = "Qwen/Qwen3-VL-Embedding-8B",
                 api_base: str = "https://api.siliconflow.cn/v1"):
        super().__init__(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
        )
