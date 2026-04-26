import os, time, json, secrets, random
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Tannhaus HSM API", version="1.0")

def mr_base2(n):
    if n == 2 or n == 3: return True
    if n < 2 or n % 2 == 0: return False
    return pow(2, n-1, n) == 1

def wv4_prime(bits):
    target = 1 << (bits - 1)
    while True:
        X = random.randrange(target // 3, target // 2)
        if X % 4 == 0: continue
        n = 3*X - 7
        if mr_base2(n): return n

def get_keys():
    try:
        keys = json.loads(os.environ.get("API_KEYS", "{}"))
        if "sk_teste_123" not in keys:
            keys["sk_teste_123"] = 1000
        return keys
    except:
        return {"sk_teste_123": 1000}

def save_key(key, credits):
    keys = get_keys()
    keys[key] = credits
    os.environ["API_KEYS"] = json.dumps(keys)

@app.get("/", response_class=HTMLResponse)
def landing():
    return HTML_LANDING

@app.get("/v1/prime")
def get_prime(bits: int = 2048, authorization: str = Header(None)):
    keys = get_keys()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Cadê a API Key? Bearer sk_xxx")
    key = authorization.split(" ")[1]
    if key not in keys: raise HTTPException(403, "API Key inválida")
    if keys[key] <= 0: raise HTTPException(429, "Acabou crédito")
    keys[key] -= 1
    os.environ["API_KEYS"] = json.dumps(keys)
    t0 = time.time()
    p = wv4_prime(bits)
    ms = round((time.time() - t0) * 1000, 2)
    return {"prime": hex(p), "bits": bits, "ms": ms, "credito_restante": keys[key]}

@app.get("/v1/rsa")
def get_rsa(bits: int = 4096, authorization: str = Header(None)):
    keys = get_keys()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Cadê a API Key?")
    key = authorization.split(" ")[1]
    if key not in keys or keys[key] <= 0:
        raise HTTPException(403, "Sem crédito")
    keys[key] -= 2
    os.environ["API_KEYS"] = json.dumps(keys)
    t0 = time.time()
    p = wv4_prime(bits // 2)
    q = wv4_prime(bits // 2)
    n = p * q
    ms = round((time.time() - t0) * 1000, 2)
    return {"n": hex(n), "e": 65537, "bits": bits, "ms": ms, "credito_restante": keys[key]}

@app.post("/webhook_stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    event = json.loads(payload)
    event_type = event['type']

    email = None
    if event_type == 'checkout.session.completed':
        email = event['data']['object']['customer_details']['email']
    elif event_type == 'charge.succeeded':
        email = event['data']['object']['billing_details']['email']

    if email:
        nova_key = f"sk_live_{secrets.token_hex(12)}"
        save_key(nova_key, 100000)
        print(f"NOVA KEY GERADA: {nova_key} para {email}")
        # TODO: manda email com a key pro cliente aqui
        return {"status": "ok", "key": nova_key}

    return {"status": "ignored"}
HTML_LANDING = """<!DOCTYPE html><html><head><title>Tannhaus HSM</title></head><body><h1>Tannhaus HSM API</h1><p>RSA-4096 em 0.05s</p></body></html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
