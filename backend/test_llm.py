# test_llm.py
import json
import os
from services.llm_service import get_llm, extract_requirements

def test_ollama_connection():
    print("🔌 Test de connexion à Ollama...")
    llm = get_llm()
    response = llm.invoke("Dis 'Hello' en français")
    print(f"✅ Réponse : {response.content}")
    return True

def test_extraction():
    print("\n📄 Test d'extraction d'exigences...")
    
    # ✅ CDC réaliste de taille moyenne
    cdc_test = """
    SPÉCIFICATIONS TECHNIQUES - RÉSEAU D'ENTREPRISE
    
    1. GÉNÉRALITÉS
    1.1 Le système doit être composé de switchs de niveau 3 avec une capacité de commutation d'au moins 100 Gbps.
    1.2 Chaque switch doit disposer d'au moins 48 ports 10/100/1000 Mbps avec alimentation PoE+.
    1.3 Les équipements doivent supporter le protocole SNMP v3 pour la supervision et la gestion.
    1.4 La solution doit être compatible avec les VLAN IEEE 802.1Q et supporter au moins 4094 VLAN.
    
    2. ALIMENTATION ET REDONDANCE
    2.1 L'alimentation doit être redondante avec deux sources d'alimentation hot-swappable.
    2.2 Le switch doit supporter la norme IEEE 802.3at PoE+ avec une puissance totale d'au moins 740W.
    
    3. SÉCURITÉ
    3.1 Authentification 802.1X pour le contrôle d'accès au réseau.
    3.2 Support de ACL (Access Control Lists) pour la sécurité.
    3.3 Protection contre les attaques DHCP snooping et ARP spoofing.
    
    4. PERFORMANCES
    4.1 Le taux de forwarding doit être d'au moins 100 Mpps pour les paquets de 64 octets.
    4.2 La latence ne doit pas dépasser 5 microsecondes en mode store-and-forward.
    
    5. ENVIRONNEMENT
    5.1 Température de fonctionnement : 0°C à 45°C.
    5.2 Humidité relative : 10% à 90% (sans condensation).
    5.3 Niveau de bruit maximal : 45 dB(A) à 25°C.
    
    6. MANAGEMENT
    6.1 Support de l'interface web pour la configuration.
    6.2 Support SSH v2 pour l'administration sécurisée.
    6.3 Support de RADIUS et TACACS+ pour l'authentification administrateur.
    """
    
    try:
        result = extract_requirements(cdc_test)
        print("✅ Extraction réussie !")
        print("\n📊 RÉSULTATS :")
        print(f"  - Résumé : {result.get('summary', 'N/A')[:100]}...")
        print(f"  - Contraintes : {len(result.get('key_constraints', []))}")
        print(f"  - Exigences : {len(result.get('requirements', []))}")
        
        # Afficher les premières exigences
        if result.get('requirements'):
            print("\n📋 PREMIÈRES EXIGENCES :")
            for req in result['requirements'][:3]:
                print(f"  - [{req['id']}] {req['description'][:60]}...")
        
        return result
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return None

if __name__ == "__main__":
    try:
        test_ollama_connection()
        result = test_extraction()
        if result:
            print("\n🎉 Tous les tests sont passés !")
        else:
            print("\n⚠️ Certains tests ont échoué.")
    except Exception as e:
        print(f"\n❌ Erreur générale : {e}")