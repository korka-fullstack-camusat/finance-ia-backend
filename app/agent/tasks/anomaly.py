"""Anomaly task: détection fraudes et doublons."""
from groq import Groq

ANOMALY_PROMPT = """Tu es un expert en détection de fraudes et d'anomalies financières.
Analyse les données financières pour identifier toute irrégularité :

1. **Transactions dupliquées** : même montant, même date, même tiers
2. **Montants ronds suspects** : transactions atypiquement rondes
3. **Horaires inhabituels** : transactions hors heures ouvrables
4. **Séquences inhabituelles** : patterns d'évitement de seuils
5. **Bénéficiaires non reconnus** : nouveaux tiers avec montants élevés
6. **Variations statistiques** : écarts > 3 sigma par rapport à la moyenne
7. **Transactions fractionnées** : splitting pour contourner des limites
8. **Doublons factures** : même fournisseur, même montant, dates proches

Pour chaque anomalie : niveau de risque (CRITIQUE/ÉLEVÉ/MOYEN/FAIBLE), description, montant concerné, recommandation.

Données :
{data}

Date d'analyse : {date}
"""


def run_anomaly(data: str, date: str, client: Groq, model: str) -> str:
    prompt = ANOMALY_PROMPT.format(data=data[:8000], date=date)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
