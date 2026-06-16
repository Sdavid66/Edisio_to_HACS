# Publier ce dépôt sur GitHub pour HACS

HACS installe une intégration depuis un dépôt **GitHub public**. Ce dépôt est
publié sur [`Sdavid66/edisio_HA_v2`](https://github.com/Sdavid66/edisio_HA_v2).

## 1. Pousser les fichiers
Depuis le dossier du projet :
```bash
git init
git add .
git commit -m "Edisio integration 1.0.0"
git branch -M main
git remote add origin https://github.com/Sdavid66/edisio_HA_v2.git
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
`https://github.com/Sdavid66/edisio_HA_v2`, catégorie **Integration** → **Ajouter**,
puis ouvrez la fiche *Edisio* et **Téléchargez**. Redémarrez Home Assistant.

## Vérification automatique
Le workflow `.github/workflows/validate.yml` lance **hassfest** et **HACS Action**
à chaque push : une coche verte confirme que la structure est conforme.
