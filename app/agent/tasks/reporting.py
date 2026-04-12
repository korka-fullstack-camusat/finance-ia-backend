"""Reporting task: génère bilan et P&L à partir des données financières."""
import json
from typing import Optional


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


async def run_reporting(data: str, date: str, anthropic_client) -> str:
    """Lance l'analyse de reporting avec Claude."""
    prompt = REPORTING_PROMPT.format(data=data[:8000], date=date)

    message = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
