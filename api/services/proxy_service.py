class ProxyService:
    def handle_chat_completions(self, payload: dict) -> dict:
        return {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "choices": [],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "request_echo": payload,
        }
