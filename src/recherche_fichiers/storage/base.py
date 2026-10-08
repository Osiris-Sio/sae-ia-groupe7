import chromadb


class VectorStore:
    """
    Gère le stockage et la recherche des vecteurs avec ChromaDB.
    """

    def __init__(
        self,
        persist_path: str = "data/chroma",
        collection_name: str = "documents",
    ):
        # Initialise la base ChromaDB.
        self.client = chromadb.PersistentClient(path=persist_path)

        # Récupère ou crée la collection.
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """
        Ajoute les chunks et leurs embeddings dans ChromaDB.
        """

        # Arrête la fonction si aucun chunk n'est fourni.
        if not ids:
            return

        # Vérifie que les listes ont la même longueur.
        if not (
            len(ids)
            == len(documents)
            == len(embeddings)
        ):
            raise ValueError(
                "ids, documents et embeddings doivent avoir "
                "la même longueur."
            )

        # Vérifie qu'il y a une métadonnée par chunk.
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                "metadatas doit avoir la même longueur que ids."
            )

        # Ajoute les données dans ChromaDB.
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float] | None = None,
        k: int = 5,
        embedding: list[float] | None = None,
    ) -> dict:
        """
        Recherche les k chunks les plus proches.
        """
        target_embedding = query_embedding if query_embedding is not None else embedding
        if target_embedding is None:
            raise ValueError("Un vecteur d'embedding doit être fourni.")

        if k <= 0:
            raise ValueError("k doit être supérieur à 0.")

        # Recherche les chunks les plus similaires.
        return self.collection.query(
            query_embeddings=[target_embedding],
            n_results=k,
        )