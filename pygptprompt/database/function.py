"""
pygptprompt/database/function.py
"""
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from llama_cpp import Embedding

from pygptprompt.api.factory import (
    ChatModel,  # ChatModel = Union[OpenAIAPI, LlamaCppAPI]
)


class ChatModelEmbeddingFunction(EmbeddingFunction):
    def __init__(self, chat_model: ChatModel):
        """
        Initialize the ChatModelEmbeddingFunction.

        Args:
            chat_model (ChatModel): The chat model instance, which can be either OpenAI or LlamaCpp API.
        """
        self._model = chat_model

    def __call__(self, texts: Documents) -> Embeddings:
        """
        Generate embeddings using the chat model.

        Args:
            texts (Documents): The input texts for which embeddings need to be generated.

        Returns:
            Embeddings: The list of embeddings generated by the chat model.

        """
        # Replace newlines, which can negatively affect performance.
        texts = [t.replace("\n", " ") for t in texts]

        # Get embeddings from the chat model API
        embeddings: Embedding = self._model.get_embeddings(input=texts)["data"]

        # Sort resulting embeddings by index
        # Note: This sorting step may not be necessary depending on the API response.
        # The `Embeddings` type should be a list of `EmbeddingData` objects.
        sorted_embeddings: Embedding = sorted(embeddings, key=lambda e: e["index"])  # type: ignore

        # Return just the embeddings
        return [result["embedding"] for result in sorted_embeddings]
