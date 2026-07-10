from httpx import AsyncClient

class OllamaEmbedder:
    def __init__(
        self,
        client: AsyncClient,
        model: str,
    ):
        self._client = client
        self._model = model

    async def embed(
        self,
        text: str,
    ) -> list[float]:
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        response = await self._client.post(
            "/api/embed",
            json={
                "model": self._model,
                "input": texts,
            },
        )

        response.raise_for_status()

        return response.json()["embeddings"]