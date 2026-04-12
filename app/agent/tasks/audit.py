"""Audit task: rapport de conformité."""

AUDIT_PROMPT = """Tu es un auditeur financier certifié expert en conformité réglementaire.
Génère un rapport d'audit de conformité complet :

1. **Conformité comptable** : respect des normes IFRS/PCG, principes comptables
2. **Documentation** : exhaustivité des pièces justificatives
3. **Séparation des tâches** : contrôle interne, autorisations
4. **Conformité fiscale** : TVA, IS, déclarations obligatoires
5. **Conformité réglementaire** : RGPD si données personnelles, AML/CFT
6. **Points de non-conformité** : classés par criticité
7. **Plan d'action correctif** : priorités et échéances recommandées
8. **Synthèse de conformité** : score global et avis d'audit

Format : rapport formel avec sections numérotées, tableau récapitulatif, conclusion.

Données à auditer :
{data}

Date d'audit : {date}
"""


async def run_audit(data: str, date: str, anthropic_client) -> str:
    prompt = AUDIT_PROMPT.format(data=data[:8000], date=date)
    message = await anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
