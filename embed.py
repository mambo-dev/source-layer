import requests

def embed_text(text):

    url  = 'http://localhost:11434/api/embed'
    payload ={
        "model":"nomic-embed-text",
        "input":text
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
    
        response.raise_for_status()
        response = response.json()
        return response['embeddings']
    except requests.exceptions.Timeout:
        raise TimeoutError("Request time out")
    except requests.exceptions.HTTPError as err:
        raise RuntimeError(f"Ollama embedding request failed: {err}") from err
    except requests.exceptions.RequestException as err:
        raise ValueError(err)



