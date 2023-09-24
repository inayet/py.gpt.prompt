"""
pygptprompt/database/chroma.py
"""
from datetime import datetime
from typing import Dict, List, Optional, Union

from chromadb import PersistentClient, Settings
from chromadb.api.types import Include, OneOrMany, QueryResult, Where, WhereDocument

from pygptprompt.config.manager import ConfigurationManager
from pygptprompt.pattern.model import ChatModel, ChatModelDocument, ChatModelDocuments
from pygptprompt.storage.function import VectorStoreEmbeddingFunction


# NOTE:
# TELEMETRY IS SET TO OFF BY DEFAULT.
# YOU MUST OPT IN IF YOU WANT THIS TURNED ON.
#
# I plan on removing telemetry completely in the future.
# When I do, Chroma will be removed completely as a result.
#
# Set anonymized_telemetry in your clients settings to
# False to opt out of telemetry.
#
# SOURCE: https://docs.trychroma.com/telemetry
#
class ChromaVectorStore:
    def __init__(
        self,
        collection_name: str,
        database_path: str,
        config: ConfigurationManager,
        chat_model: ChatModel,
        anonymized_telemetry: bool = False,
    ):
        self.collection_name = collection_name
        self.database_path = database_path
        self.config = config
        self.chat_model = chat_model
        self.anonymized_telemetry = anonymized_telemetry
        self.embedding_function = None
        self.chroma_client = None
        self.collection = None

        self.logger = self.config.get_logger(
            "app.log.general", "ChromaVectorStore", "DEBUG"
        )

        self._initialize_components()
        self._get_or_create_collection()  # avoid cascades

    def _initialize_components(self):
        self.embedding_function = VectorStoreEmbeddingFunction(
            chat_model=self.chat_model, logger=self.logger
        )

        self.chroma_client = PersistentClient(
            path=self.database_path,
            settings=Settings(
                anonymized_telemetry=self.anonymized_telemetry,
            ),
        )

    def _get_or_create_collection(self):
        try:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
            )
            self.logger.debug(f"Created collection {self.collection_name}")
        except ValueError:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
            )
            self.logger.debug(f"Loaded collection {self.collection_name}")

    def get_chroma_heartbeat(self) -> int:
        """returns timestamp to check if service is alive"""
        return self.chroma_client.heartbeat()

    def get_collection_count(self) -> int:
        """returns total number of embeddings in a collection"""
        return self.collection.count()

    def add_message_to_collection(self, message: dict):
        """add new items to a collection"""
        timestamp = datetime.utcnow().isoformat()
        unique_id = f"{self.collection_name}_{timestamp}"

        self.collection.add(
            ids=[unique_id],
            documents=[message["content"]],
            metadatas=[{"role": message["role"]}],
        )

        self.logger.debug(
            f"Added message to collection {self.collection_name} with ID {unique_id}"
        )

    def upsert_to_collection(
        self,
        ids: Union[str, List[str]],
        metadatas: Union[Dict[str, str], List[Dict[str, str]]],
        documents: Union[ChatModelDocument, ChatModelDocuments],
    ):
        """new items will be added, existing items will be updated."""
        self.collection.upsert(
            ids=ids,
            metadatas=metadatas,
            documents=documents,
        )

        self.logger.debug(
            f"Upserted documents to collection {self.collection_name} with ID {ids}"
        )

    def query_from_collection(
        self,
        query_texts: Optional[OneOrMany[ChatModelDocument]] = None,
        n_results: int = 10,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
        include: Include = ["metadatas", "documents", "distances"],
    ) -> QueryResult:
        return self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
        )