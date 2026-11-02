import requests
import time
from app.settings import settings

def embed_text(text):

    url  = f'{settings.ollama_base_url}/api/embed'
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



def get_answer(prompt):
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
            "model": "llama3.2:3b",
            "system": prompt.system_prompt,
            "prompt": prompt.user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_ctx": 8192,
                "num_predict": 768
            }
        }

    try:
        start = time.perf_counter()
        response = requests.post(url, json=payload, timeout=180)
    
        response.raise_for_status()
        data = response.json()
        print("Total time:", round(time.perf_counter() - start, 2), "seconds")
        print("Load time:", round(data.get("load_duration", 0) / 1e9, 2), "seconds")
        print("Prompt processing:", round(data.get("prompt_eval_duration", 0) / 1e9, 2), "seconds")
        print("Generation:", round(data.get("eval_duration", 0) / 1e9, 2), "seconds")
        print("Generated tokens:", data.get("eval_count"))
        return data["response"]
    except requests.exceptions.Timeout:
        raise TimeoutError("Request time out")
    except requests.exceptions.HTTPError as err:
        raise RuntimeError(f"Ollama embedding request failed: {err}") from err
    except requests.exceptions.RequestException as err:
        raise ValueError(err)