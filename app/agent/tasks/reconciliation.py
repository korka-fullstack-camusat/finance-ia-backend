"""Reconciliation task: rapprochement bancaire."""
from groq import Groq

RECONCILIATION_PROMPT = """Tu es un expert en rapprochement bancaire.
Analyse les données fournies et effectue le rapprochement bancaire complet :

1. **Écritures concordantes** : transactions présentes des deux côtés
2. **Écarts détectés** : montants non réconciliés, dates décalées
3. **Transactions en attente** : chèques émis non encaissés, virements en cours
4. **Erreurs potentielles** : doublons, inversions de signe, mauvaises imputations
5. **Solde réconcilié final** et écart résiduel

Sois précis sur les montants et dates. Format markdown avec tableaux.

Données bancaires et comptables :
{data}

Date : {date}
"""


def run_reconciliation(data: str, date: str, client: Groq, model: str) -> str:
    prompt = RECONCILIATION_PROMPT.format(data=data[:8000], date=date)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
