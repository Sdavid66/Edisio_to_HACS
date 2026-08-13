# Publier ce dépôt sur GitHub pour HACS

HACS installe une intégration depuis un dépôt **GitHub public**. Ce dépôt est
publié sur [`Sdavid66/Edisio_to_HACS`](https://github.com/Sdavid66/Edisio_to_HACS).

## 1. Pousser les fichiers
Depuis le dossier du projet :
```bash
git init
git add .
git commit -m "Edisio integration 1.0.0"
git branch -M main
git remote add origin https://github.com/Sdavid66/Edisio_to_HACS.git
git push -u origin main
```

## 2. Créer une release (important pour HACS)
HACS privilégie les *releases*. Créez un tag correspondant à la version du manifest :
```bash
git tag v1.0.0
git push origin v1.0.0
```
Puis sur GitHub : **Releases → Draft a new release → tag v1.0.0 → Publish**.

> Astuce : à chaque nouvelle version, incrémentez `version` dans
> `custom_components/edisio/manifest.json` **et** créez le tag/release correspondant.

## 3. Ajouter le dépôt dans HACS
Dans Home Assistant : **HACS → ⋮ → Dépôts personnalisés** → collez
`https://github.com/Sdavid66/Edisio_to_HACS`, catégorie **Integration** → **Ajouter**,
puis ouvrez la fiche *Edisio* et **Téléchargez**. Redémarrez Home Assistant.

## Vérification automatique
Le workflow `.github/workflows/validate.yml` lance **hassfest** et **HACS Action**
à chaque push : une coche verte confirme que la structure est conforme.

## 4. Publier dans le magasin HACS **par défaut** (quand vous le voulez)

Aujourd'hui l'intégration s'installe en **dépôt personnalisé** (étape 3). Pour
qu'elle apparaisse dans la **recherche HACS de tous les utilisateurs**, il faut
la soumettre au magasin par défaut. **Rien ne se fait automatiquement** : c'est
une démarche volontaire, à lancer le jour où vous le décidez.

**Le dépôt est déjà prêt** (critères remplis) :
- ✅ dépôt public, non archivé, avec description et *topics* ;
- ✅ *issues* activées ;
- ✅ workflows `hassfest` + `HACS Action` au vert, sans `ignore` ;
- ✅ `README.md`, `LICENSE`, `hacs.json` conformes ;
- ✅ des *releases* GitHub existent (créées après le passage des workflows).

**Le jour où vous voulez publier**, une seule action à faire vous-même :
1. Forkez [`hacs/default`](https://github.com/hacs/default).
2. Dans le fichier **`integration`**, ajoutez la ligne `Sdavid66/Edisio_to_HACS`
   **en respectant l'ordre alphabétique**.
3. Ouvrez une **pull request** depuis votre fork (compte personnel, pas une
   organisation).
4. Attendez la revue (le délai se compte en semaines/mois).

> Astuce : lancez d'abord `python3 scripts/check_integration.py . --publish`
> (si le script est présent) pour re-vérifier les critères hors ligne.

Tant que cette PR n'est pas ouverte **et** fusionnée, l'intégration **n'est pas**
dans le magasin officiel — c'est exactement l'état voulu pour l'instant.
