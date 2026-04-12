"""Forecast task: prévisions trésorerie 6 mois."""

FORECAST_PROMPT = """Tu es un expert en prévision financière et gestion de trésorerie.
Établis des prévisions de trésorerie sur les 6 prochains mois à partir des données historiques.

Structure du rapport :
1. **Analyse des flux historiques** : tendances entrées/sorties
2. **Prévisions mois par mois** (M+1 à M+6) :
   - Encaissements prévisionnels
   - Décaissements prévisionnels
   - Solde de trésorerie prévisionnel
3. **Scénarios** : optimiste / central / pessimiste
4. **Points de vigilance** : mois de tension, besoins de financement
5. **Recommandations** : actions à mener pour optimiser la trésorerie

Format : tableaux chiffrés + graphique ASCII de l'évolution + recommandations actionnables.

Données historiques :
{data}

Date d'analyse : {date}
"""


async def run_forecast(data: str, date: str, anthropic_client) -> str:
    prompt = FORECAST_PROMPT.format(data=data[:8000], date=date)
    message = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
