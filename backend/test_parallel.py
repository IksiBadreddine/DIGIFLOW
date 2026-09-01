# backend/test_parallel.py

import asyncio
import time
from services.llm_service import get_llm

async def test_llm_parallel():
    """Teste si Ollama répond en parallèle"""
    
    llm = get_llm()
    
    async def call_llm(i):
        start = time.time()
        print(f"🔹 Requête {i} démarrée...")
        response = llm.invoke(f"Dis 'Bonjour' en français, réponse {i}")
        elapsed = time.time() - start
        print(f"✅ Requête {i} terminée en {elapsed:.1f}s")
        return response
    
    # Lancer 4 requêtes en parallèle
    start_total = time.time()
    tasks = [call_llm(i) for i in range(4)]
    results = await asyncio.gather(*tasks)
    total = time.time() - start_total
    
    print(f"\n📊 Temps total: {total:.1f}s")
    print(f"   Si c'est < 10s → parallélisme actif ✅")
    print(f"   Si c'est > 20s → pas de parallélisme ❌")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_llm_parallel())