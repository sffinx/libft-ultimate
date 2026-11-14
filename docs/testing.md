# Validation de Libft Ultimate 0.1.0

Vérification locale du 14 novembre 2026. Sujet cible : PDF 1.3.

## Résultats obtenus

- **6765 cas réussis sur 6765** avec une fixture indépendante adossée à la libc.
- Les 43 fonctions sont présentes dans le catalogue.
- Même catalogue : 6765 cas réussis avec le moteur compilé par Clang.
- 43 contrôles de signatures réussis avec GCC et avec Clang.
- **21 mutations détectées sur 21** : mauvais booléen, mauvaise longueur,
  lecture hors limite, boucle infinie, écriture en trop, mauvais pointeur
  retourné, mauvais sens de memmove, mauvais retour strlcpy, NUL de strchr,
  comparaison inversée, calloc zéro/initialisation, crash sur malloc raté,
  fuite de split, index de callback, mauvais fd, fuite de nœud, tête non
  remise à NULL, mauvais traitement de contenu NULL, nettoyage incomplet
  de lstmap et exit(0) prématuré.
- Variante valide acceptée : comparaisons retournant un autre nombre
  de même signe et strdup allouant plus d’octets que le minimum.
- **258 cas ciblés réussis sous Valgrind** sur la fixture valide.
- **8 tests de la CLI réussis**, dont une 22e mutation de lecture après
  la fin d’une allocation, détectée par Valgrind et rattachée au bon cas.
- Les tests vérifient la conservation des octets ET des dates de modification
  des fichiers du projet testé, y compris avec des espaces et accents dans le chemin.
- Identifiants uniques et corpus reproductible avec la même graine.
- Aucun caractère ANSI ni backspace dans la sortie vérifiée.

Le scan complet de la fixture confirme aussi les contrôles Makefile.
La fixture appelle volontairement la libc pour fournir une référence
indépendante : le contrôle des fonctions externes doit donc la rejeter
comme projet de rendu, malgré la réussite de ses tests fonctionnels.
Cette distinction a été vérifiée, elle ne constitue pas un faux positif.

## Commandes réellement exécutées

Depuis le dossier du testeur, avec Valgrind installé :

```sh
python3 .testeur/tests/selftest.py /tmp/verification.json
python3 .testeur/tests/test_cli.py
```

Le scan CLI complet et des scans `--only`, `--json`, `--no-norm`,
`--credits` et `--valgrind` ont été exécutés sur des fixtures temporaires.
La compilation Clang a été vérifiée séparément avec le même catalogue.

Les rapports locaux ne sont pas versionnés. Les commandes ci-dessus
permettent de refaire les vérifications ; les exécutions GitHub sont visibles
dans [Actions](https://github.com/sffinx/libft-ultimate/actions).

Les contrôles de publication se lancent avec :

```sh
python3 .testeur/tests/test_publication.py
```

Ils vérifient notamment l’exemple documenté, les liens locaux et l’absence
de fichiers du workspace personnel dans les fichiers suivis par Git.

## Portée de cette validation

Aucune Libft étudiante n’a été validée ou modifiée pendant la construction
du testeur. Aucun résultat officiel, score ou nouvelle tentative n’est déduit.

Ces contrôles réduisent les faux positifs et valident les mécanismes testés.
Ils ne démontrent ni l’absence de tout défaut du testeur, ni une reprise
exhaustive de chaque assertion historique, ni une équivalence Moulinette.
