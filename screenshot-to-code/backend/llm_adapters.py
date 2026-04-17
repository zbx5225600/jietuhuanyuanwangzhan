"""
多模型适配器
支持OpenAI、通义千问、文心一言、智谱GLM等多种AI模型
"""
import base64
from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """LLM适配器基类"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        """生成响应"""
        pass


class OpenAIAdapter(LLMAdapter):
    """OpenAI适配器 (GPT-4 Vision)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview", base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        import openai
        
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        client = openai.AsyncOpenAI(**client_kwargs)
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            else:
                raise Exception("No response from OpenAI")
        finally:
            await client.close()


class QwenAdapter(LLMAdapter):
    """通义千问适配器 (Qwen-VL)"""
    
    def __init__(self, api_key: str, model: str = "qwen-vl-max"):
        self.api_key = api_key
        self.model = model
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        import dashscope
        from dashscope import MultiModalConversation
        
        dashscope.api_key = self.api_key
        
        # 转换消息格式
        qwen_messages = self._convert_messages(messages)
        
        response = MultiModalConversation.call(
            model=self.model,
            messages=qwen_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"Qwen API error: {response.message}")
    
    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """转换消息格式为通义千问格式"""
        qwen_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                # 通义千问将system消息合并到第一个user消息
                continue
            
            if isinstance(msg["content"], str):
                qwen_messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}]
                })
            elif isinstance(msg["content"], list):
                content = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        content.append({"text": item["text"]})
                    elif item["type"] == "image_url":
                        # 提取base64图片
                        image_url = item["image_url"]["url"]
                        content.append({"image": image_url})
                
                qwen_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        return qwen_messages


class ErnieAdapter(LLMAdapter):
    """文心一言适配器 (ERNIE-Bot-4)"""
    
    def __init__(self, api_key: str, secret_key: str, model: str = "ernie-bot-4"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.model = model
        self.access_token = None
    
    async def _get_access_token(self) -> str:
        """获取access token"""
        if self.access_token:
            return self.access_token
        
        import aiohttp
        
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                result = await response.json()
                self.access_token = result["access_token"]
                return self.access_token
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        import aiohttp
        
        access_token = await self._get_access_token()
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{self.model}?access_token={access_token}"
        
        # 转换消息格式
        ernie_messages = self._convert_messages(messages)
        
        payload = {
            "messages": ernie_messages,
            "max_output_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if "result" in result:
                    return result["result"]
                else:
                    raise Exception(f"ERNIE API error: {result.get('error_msg', 'Unknown error')}")
    
    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """转换消息格式为文心一言格式"""
        ernie_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                continue
            
            if isinstance(msg["content"], str):
                ernie_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            elif isinstance(msg["content"], list):
                # 文心一言支持图片，但格式不同
                text_parts = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        text_parts.append(item["text"])
                    elif item["type"] == "image_url":
                        # 提取base64图片
                        image_url = item["image_url"]["url"]
                        if image_url.startswith("data:image"):
                            # 提取base64部分
                            base64_data = image_url.split(",")[1]
                            text_parts.append(f"[图片: {base64_data[:50]}...]")
                
                ernie_messages.append({
                    "role": msg["role"],
                    "content": "\n".join(text_parts)
                })
        
        return ernie_messages


class GLMAdapter(LLMAdapter):
    """智谱GLM适配器 (GLM-4V, GLM-4.1V-Thinking-Flash)"""
    
    def __init__(self, api_key: str, model: str = "glm-4v"):
        self.api_key = api_key
        self.model = model
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        from zhipuai import ZhipuAI
        
        client = ZhipuAI(api_key=self.api_key)
        
        # 转换消息格式
        glm_messages = self._convert_messages(messages)
        
        # GLM-4.1V-Thinking-Flash 支持更高的max_tokens
        if "thinking" in self.model.lower():
            max_tokens = min(max_tokens, 8192)  # Thinking模型支持更长输出
        
        response = client.chat.completions.create(
            model=self.model,
            messages=glm_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # 如果是Thinking模型，可能包含思维过程，提取最终答案
            if "thinking" in self.model.lower() and content:
                # Thinking模型的输出格式可能包含<think>标签
                # 但通常API已经处理好，直接返回最终答案
                return content
            
            return content
        else:
            raise Exception("No response from GLM")
    
    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """转换消息格式为智谱GLM格式"""
        glm_messages = []
        
        for msg in messages:
            if isinstance(msg["content"], str):
                glm_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            elif isinstance(msg["content"], list):
                content = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        content.append({
                            "type": "text",
                            "text": item["text"]
                        })
                    elif item["type"] == "image_url":
                        # GLM-4V支持图片URL
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": item["image_url"]["url"]}
                        })
                
                glm_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        return glm_messages


class DoubaoAdapter(LLMAdapter):
    """字节跳动豆包适配器 (Doubao Vision)"""
    
    def __init__(self, api_key: str, model: str = "doubao-vision-pro", base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        temperature: float = 0.2
    ) -> str:
        import openai
        
        client_kwargs = {"api_key": self.api_key, "base_url": self.base_url}
        client = openai.AsyncOpenAI(**client_kwargs)
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            else:
                raise Exception("No response from Doubao")
        finally:
            await client.close()


def create_adapter(
    provider: str,
    api_key: str,
    model: str,
    **kwargs
) -> LLMAdapter:
    """
    创建LLM适配器
    
    Args:
        provider: 提供商 (openai, qwen, ernie, glm, doubao)
        api_key: API密钥
        model: 模型名称
        **kwargs: 其他参数
    
    Returns:
        LLMAdapter实例
    """
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIAdapter(
            api_key=api_key,
            model=model,
            base_url=kwargs.get("base_url")
        )
    elif provider == "qwen":
        return QwenAdapter(api_key=api_key, model=model)
    elif provider == "ernie":
        return ErnieAdapter(
            api_key=api_key,
            secret_key=kwargs.get("secret_key", ""),
            model=model
        )
    elif provider == "glm":
        return GLMAdapter(api_key=api_key, model=model)
    elif provider == "doubao":
        return DoubaoAdapter(
            api_key=api_key,
            model=model,
            base_url=kwargs.get("base_url")
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
