from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        self._model = ChatOpenAI(api_key=api_key, model=model, temperature=0)

    def classify_domain(self, message: str, capabilities: dict[str, str]) -> str | None:
        options = "\n".join(f"{name}: {description}" for name, description in capabilities.items())
        reply = self._model.invoke(
            [
                SystemMessage(
                    content="Select exactly one matching domain from these compact descriptions, "
                    "or reply NONE when ambiguous. Reply only with the domain name or NONE.\n" + options
                ),
                HumanMessage(content=message),
            ]
        )
        answer = reply.content.strip().lower() if isinstance(reply.content, str) else ""
        return answer if answer in capabilities else None
