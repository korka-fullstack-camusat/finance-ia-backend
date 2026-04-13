"""Reporting task: génère bilan et P&L."""
from mistralai import Mistral

REPORTING_PROMPT = """Tu es un expert-comptable et analyste financier senior.
Analyse les données financières fournies et génère un rapport complet comprenant :

1. **Bilan comptable** (Actif / Passif)
2. **Compte de résultat (P&L)** : revenus, charges, résultat net
3. **Indicateurs clés** : marge brute, marge nette, EBITDA estimé
4. **Commentaires analytiques** : tendances, points d'attention, recommandations

Format de sortie : rapport structuré en markdown avec tableaux chiffrés.

Données financières :
{data}

Date d'analyse : {date}
"""


def run_reporting(data: str, date: str, client: Mistral, model: str) -> str:
    prompt = REPORTING_PROMPT.format(data=data[:8000], date=date)
    response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
