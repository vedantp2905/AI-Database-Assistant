from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
import os

class LLMFactory:
    @staticmethod
    def create_llm(provider="sambanova"):
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.2
            )
        elif provider == "sambanova":
            return ChatOpenAI(
                api_key=os.getenv("SAMBANOVA_API_KEY"),
                base_url="https://api.sambanova.ai/v1",
                model="Meta-Llama-3.3-70B-Instruct",
                temperature=0.1,
                top_p=0.1,
                request_timeout=30,
                max_retries=2,
                streaming=True
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}") 