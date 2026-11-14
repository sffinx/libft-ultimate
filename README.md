# Libft Ultimate

Testeur en ligne de commande pour **Libft, sujet PDF version 1.3**.
Il vérifie les 43 fonctions, listes comprises, dans une copie temporaire
du projet.

La version 0.1.0 est ouverte aux premiers essais. Les retours sur les
faux positifs, les messages peu clairs et les différences entre Linux
sont les bienvenus.

## Lancer un test

Il faut Linux 64 bits, Python 3.10 ou plus, `cc`, `make`, `ar` et `nm`.
Le moteur utilise un éditeur de liens compatible avec `--wrap`.
Valgrind et Norminette sont facultatifs. macOS n’est pas pris en charge.

Cloner le testeur à côté de sa Libft :

```sh
git clone https://github.com/sffinx/libft-ultimate.git
cd libft-ultimate
./libft-test ../libft
```

`../libft` est le dossier contenant le `Makefile` et `libft.h`.
Le Makefile doit pouvoir produire `libft.a`. Remplacer ce chemin si le
projet se trouve ailleurs :

```sh
./libft-test "$HOME/42/Libft"
```

Le scan n’installe rien et n’utilise pas le réseau. Il n’écrit pas dans
le dossier étudiant et ne change pas son Git.

## Pendant le travail

```sh
# Une fonction
./libft-test ../libft --only split

# Plusieurs fonctions
./libft-test ../libft --only calloc,split,lstmap

# Vérification mémoire avec Valgrind
./libft-test ../libft --only split --valgrind

# Rapport à joindre à un retour
./libft-test ../libft --only split --json /tmp/libft-split.json
```

Avec `--only`, le résultat concerne les fonctions choisies. Les contrôles
du Makefile, de la Norminette et du projet entier sont réservés au scan
sans cette option.

## Lire une erreur

Un défaut introduit dans la bibliothèque de contrôle donne cette sortie :

```text
  ft_strlen — 'Hello !'
    longueur en octets ; attendu=7 ; obtenu=8
```

La suite du message donne l’identifiant du cas et ses références GitHub,
avec le fichier et la ligne consultés. Un cas créé pour ce testeur porte
la mention `test ajouté`. Les erreurs de mémoire sont rattachées au cas
concerné, y compris avec Valgrind.

[Exemples de sorties et lecture des résultats](docs/examples.md).

## Ce qui est vérifié

Le catalogue contient **6 765 cas distincts** avec la graine par défaut.
Il couvre les retours, les limites de buffers, les données binaires,
les chevauchements de `memmove`, les callbacks, les listes et le nettoyage
après un échec d’allocation.

Le sujet 1.3 impose notamment les retours `0` ou `1` des fonctions de
classification, `unsigned int` pour `ft_lstsize`, et un pointeur libérable
pour `calloc` de taille zéro hors échec d’allocation. Les listes font partie
des fonctions obligatoires.

Le moteur accepte plusieurs résultats quand le contrat le permet : il
compare le signe de `memcmp` et `strncmp`, et n’impose pas une allocation
de taille exacte. Les appels dont le comportement est indéfini ne servent
pas à déclarer une erreur.

## Ce que le résultat ne dit pas

**La Moulinette peut utiliser d’autres tests et ne pas reprendre ceux-ci.**
Le rappel apparaît à chaque scan. Tout réussir ici ne garantit aucune note.

Un `TIMEOUT` peut venir de la machine ou du programme. Un contrôle marqué
« à vérifier » n’a pas été validé automatiquement. Le contenu du README,
les fichiers inutiles et tous les appels transitifs autorisés par fonction
nécessitent encore une relecture.

La copie temporaire évite de modifier le travail pendant un scan ordinaire.
Elle n’isole pas un Makefile malveillant : tester uniquement des projets
auxquels on fait confiance.

[Couverture, choix de tests et limites](docs/coverage.md) ·
[Validation du moteur](docs/testing.md) · [Toutes les options](docs/usage.md)

## Signaler un problème

Ouvrir une [issue](https://github.com/sffinx/libft-ultimate/issues/new/choose)
avec la version du testeur, la distribution Linux, la commande lancée et
le message complet. Pour un faux positif, ajouter un petit cas reproductible
et la règle du sujet ou du manuel qui justifie le résultat attendu.

[Contribuer](CONTRIBUTING.md) · [Changements](CHANGELOG.md)

## Crédits

Ce projet s’appuie sur l’étude de **14 testeurs et distributions**.
Les entrées compatibles sont regroupées, puis vérifiées par un moteur
commun écrit pour le sujet 1.3. Ce n’est pas une reprise certifiée de chaque
assertion historique de ces projets.

[Tripouille/libftTester](https://github.com/Tripouille/libftTester) apparaît
en premier dans les références. Cet ordre ne signifie pas que ses tests
et ceux de la Moulinette sont identiques.

[Tous les auteurs, dépôts et révisions consultés](CREDITS.md).

Le code original de Libft Ultimate est sous [licence MIT](LICENSE).
Les notices des projets sources sont conservées avec leurs crédits.
