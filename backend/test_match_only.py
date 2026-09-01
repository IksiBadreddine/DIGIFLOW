# backend/test_match_only.py

import requests
import json

def test_matching():
    """Test du matching"""
    
    print("🧪 TEST DU MATCHING")
    print("="*50)
    
    # 1. Récupérer le catalogue
    print("\n📦 Récupération du catalogue...")
    response = requests.get('http://localhost:8000/api/products')
    
    if response.status_code != 200:
        print(f"❌ Erreur: {response.status_code}")
        return
    
    products = response.json().get('products', [])
    print(f"✅ {len(products)} produits dans le catalogue")
    
    # 2. Simuler des exigences
    print("\n📋 Simuler des exigences...")
    requirements = [
        {
            "id": "REQ-001",
            "description": "Switch manageable, minimum 24 ports, alimentation PoE+"
        },
        {
            "id": "REQ-002",
            "description": "Support des VLAN (802.1Q)"
        },
        {
            "id": "REQ-003",
            "description": "Supervision centralisée via protocole SNMP"
        },
        {
            "id": "REQ-004",
            "description": "4 caméras IP type dôme, résolution minimum 4 MP"
        },
        {
            "id": "REQ-005",
            "description": "Alimentation des caméras exclusivement en PoE (802.3af/at)"
        }
    ]
    
    print(f"✅ {len(requirements)} exigences simulées")
    
    # 3. Appeler l'API de matching
    print("\n🧠 Appel du matching...")
    
    payload = {
        "requirements": requirements,
        "products": products
    }
    
    response = requests.post(
        'http://localhost:8000/api/match',
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    # 4. Afficher les résultats
    if response.status_code == 200:
        results = response.json().get('results', [])
        
        print("\n" + "="*50)
        print("📊 RÉSULTATS DU MATCHING")
        print("="*50)
        
        for result in results:
            score = result.get('compliance_score', 0) * 100
            print(f"\n🔹 {result.get('product_name', 'N/A')}")
            print(f"   Fabricant: {result.get('manufacturer', 'N/A')}")
            print(f"   Score: {score:.1f}%")
            
            strengths = result.get('strengths', [])
            if strengths:
                print(f"   ✅ {', '.join(strengths[:2])}")
            
            gaps = result.get('gaps', [])
            if gaps:
                print(f"   ⚠️ {', '.join(gaps[:2])}")
        
        print("\n" + "="*50)
        print(f"✅ {len(results)} produits évalués")
        
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_matching()