"""KPI task: calcul DSO, DPO, liquidité, marges."""
from mistralai import Mistral

KPI_PROMPT = """Tu es un analyste financier spécialisé en indicateurs de performance.
Calcule et analyse les KPIs financiers suivants à partir des données fournies :

1. **DSO (Days Sales Outstanding)** : délai moyen de recouvrement clients
2. **DPO (Days Payable Outstanding)** : délai moyen de paiement fournisseurs
3. **Ratio de liquidité courante** : actifs courants / passifs courants
4. **Ratio de liquidité immédiate** : (trésorerie + équivalents) / passifs courants
5. **Marge brute** : (CA - coût des ventes) / CA × 100
6. **Marge nette** : résultat net / CA × 100
7. **ROE** : résultat net / capitaux propres × 100

Pour chaque KPI : valeur calculée, benchmark sectoriel, interprétation, alerte si hors norme.

Données :
{data}

Date : {date}
"""


def run_kpi(data: str, date: str, client: Mistral, model: str) -> str:
    prompt = KPI_PROMPT.format(data=data[:8000], date=date)
    response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
