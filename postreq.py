import httpx

payload = {
    "input": [
        {
            "role": "user",
            "parts": [{"content": "Does this insurance cover dental surgery?"}]
        }
    ],
    "config": {}
}

response = httpx.post("http://localhost:8001/run", json=payload)
print(response.json())
