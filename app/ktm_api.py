import httpx

class KtmApi:
    def __init__(self, timeout=15.0):
        self.timeout = timeout

    BASE_URL = "http://10.0.0.80:8045/api/ktm"


    async def get_by_nim(self, nim: str):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/mahasiswa",
                params={"nim": nim}
            )

            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            return data[0]

    async def save_mahasiswa(self, payload: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/mahasiswa/simpan",
                json=payload
            )

            response.raise_for_status()
            return response.json()