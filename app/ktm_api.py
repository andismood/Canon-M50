import httpx
from contextlib import ExitStack

class KtmApi:
    def __init__(self, timeout=15.0):
        self.timeout = timeout

    BASE_URL = "http://10.1.1.224:8045/api/ktm"


    async def get_by_nim(self, nim: str):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/mahasiswa",
                params={"nim": nim}
            )

            response.raise_for_status()
            

            if response.status_code == 404:
                return None
            elif response.status_code == 200:
                data = response.json()
            else:
                return None

            return data[0]

    async def save_mahasiswa(self, data: dict, file_paths: list):
        with ExitStack() as stack:
            files = [
                ("file", (path, stack.enter_context(open(path, "rb")), "image/jpeg"))
                for path in file_paths
            ]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/send-foto-ktm",
                    data = data,
                    files = files
                )

                response.raise_for_status()
                return response.json()