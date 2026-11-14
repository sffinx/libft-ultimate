# Utilisation

La commande accepte le chemin d’une Libft. Sans chemin, elle utilise le
dossier courant.

```sh
./libft-test /chemin/vers/libft
```

Le testeur attend `Makefile` et `libft.h`, puis lance `make` dans une copie
temporaire pour obtenir `libft.a`. Un projet qui ne compile pas est signalé
avant les tests fonctionnels.

## Options

| Option | Usage |
|---|---|
| `--only split` | Tester une fonction et sa signature. |
| `--only calloc,split,lstmap` | Tester plusieurs fonctions. Le préfixe `ft_` est accepté. |
| `--valgrind` | Ajouter les contrôles de mémoire ; Valgrind doit être installé. |
| `--json /tmp/rapport.json` | Écrire un rapport structuré hors du dépôt étudiant. |
| `--seed 42` | Fixer la graine des données générées. Valeur par défaut : 42. |
| `--timeout 5` | Attendre au plus cinq secondes par cas. Valeur par défaut : 2. |
| `--no-norm` | Désactiver Norminette pour ce scan. |
| `--list` | Afficher les 43 fonctions sans scan. |
| `--credits` | Afficher les projets sources et leurs révisions. |
| `--version` | Afficher la version du testeur et du sujet ciblé. |
| `--help` | Afficher l’aide. |

Un chemin contenant des espaces doit être entre guillemets :

```sh
./libft-test "$HOME/42/ma libft" --only strlen
```

## Résultats

`OK` indique que les cas exécutés sont passés. `ÉCHEC` regroupe les résultats
incorrects, crashes et délais dépassés ; les détails permettent de les
distinguer. `ABSENT` indique qu’une fonction n’a pas été trouvée dans l’archive.

Un cas manquant ou non exécuté ne compte jamais comme réussi. Le mode
`--only` ne produit pas un bilan complet du projet.

Les retours `TIMEOUT` demandent une vérification du programme et de la charge
de la machine. Le délai peut être augmenté pour confirmer le résultat.

Codes de sortie :

| Code | Signification |
|---:|---|
| 0 | Les contrôles exécutés sont réussis. Les éléments à relire restent à vérifier. |
| 1 | Défaut détecté ou scan incomplet. |
| 2 | Problème d’outil ou d’environnement. |
| 130 | Scan interrompu. |

## Mise à jour

Le testeur ne se met pas à jour pendant un scan. Pour prendre une nouvelle
version, depuis un clone sans modifications locales :

```sh
git pull --ff-only
./libft-test --version
```

Pour comparer deux résultats, conserver la même révision du dépôt, la même
graine et les mêmes options. Un nombre de tests plus élevé ne garantit pas
qu’un testeur soit plus proche de la Moulinette.
